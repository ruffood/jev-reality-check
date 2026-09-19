"""按官方 jaggedness 页面描述的条件补测: 长列表计数、混合格式日期。"""
import json, random, sys
from datetime import date, timedelta
sys.path.insert(0, '.')
from run import call, load_key
from cases import noul, choice, GOODS_ZH
key = load_key(); rng = random.Random(42)
rows = []

# 长列表计数: 20 到 40 件, 选项给真值附近 ±4
for i in range(30):
    n = rng.randint(20, 40)
    items = [rng.choice(GOODS_ZH) for _ in range(n)]
    opts = {str(k): None for k in range(n - 4, n + 5)}
    d, _ = call(key, "顾客购物车里的商品（每行一件）：\n" + "\n".join(items),
                {"q": choice("购物车里一共有几件商品？", opts)})
    a = d["answers"]["q"]
    rows.append(dict(group="长列表计数", n=n, got=a["choice"], ok=a["choice"] == str(n), conf=a["confidence"]))

# 混合格式日期: 今天和签收日用不同写法, 含跨年
def fmt(dt, k):
    return [f"{dt.year}年{dt.month}月{dt.day}日", f"{dt.month}/{dt.day}/{dt.year}",
            f"{dt.day:02d}.{dt.month:02d}.{dt.year}", f"{dt.month}月{dt.day}号"][k]
for i in range(30):
    today = date(2026, 1, rng.randint(1, 8)) if i % 3 == 0 else date(2026, rng.randint(2, 12), rng.randint(1, 28))
    gap = rng.choice([5, 6, 7, 8, 9, 10])
    got_on = today - timedelta(days=gap)
    k1, k2 = rng.sample(range(4), 2)
    state = f"今天是 {fmt(today, k1)}。顾客的签收日期是 {fmt(got_on, k2)}。顾客说：我想退货。"
    d, _ = call(key, state, {"q": noul("距离签收是否已经超过 7 天？")})
    p = d["answers"]["q"]["noul"]
    rows.append(dict(group="混合格式日期", state=state, gap=gap, p=p, ok=(p >= .5) == (gap > 7), conf=max(p, 1 - p)))

json.dump(rows, open("hard.json", "w"), ensure_ascii=False, indent=1)
for g in ("长列表计数", "混合格式日期"):
    rs = [r for r in rows if r["group"] == g]; wrong = [r for r in rs if not r["ok"]]
    wc = f"{sum(r['conf'] for r in wrong)/len(wrong):.2f}" if wrong else "-"
    print(f"{g}: 对 {sum(r['ok'] for r in rs)}/{len(rs)}  错题平均把握 {wc}  错题中把握≥0.8 {sum(r['conf']>=.8 for r in wrong)}")
