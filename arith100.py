"""算术 100 题: 门槛离真实总价 1% 到 3%, 中英各 50, 对比"自己算"和"合计由代码给出"。结果写入 arith100.json。"""
import json, math, random, sys
sys.path.insert(0, '.')
from run import call, load_key
from cases import noul, GOODS_ZH, GOODS_EN
key = load_key(); rng = random.Random(100)
def wilson(k, n, z=1.96):
    p = k/n; d = 1 + z*z/n; c = p + z*z/(2*n); h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return (c-h)/d, (c+h)/d
rows = []
for i in range(100):
    lang = "zh" if i < 50 else "en"; over = i % 2 == 0
    idx = rng.sample(range(8), rng.randint(3, 4))
    lines = [(k, rng.randint(1, 4), rng.randint(19, 299)) for k in idx]
    total = sum(q*p for _, q, p in lines)
    m = rng.uniform(0.01, 0.03)
    thr = int(total*(1-m)) if over else int(total*(1+m)) + 1
    if lang == "zh":
        items = "订单明细：\n" + "\n".join(f"- {GOODS_ZH[k]} × {q}，单价 {p} 元" for k, q, p in lines)
        given = f"\n合计：{total} 元"; qtext = f"这笔订单的商品总价是否超过 {thr} 元？"
    else:
        items = "Order items:\n" + "\n".join(f"- {GOODS_EN[k]} x {q}, ${p} each" for k, q, p in lines)
        given = f"\nSubtotal: ${total}"; qtext = f"Is the order subtotal greater than ${thr}?"
    r = dict(i=i, lang=lang, over=over, total=total, thr=thr, margin=round(m, 4))
    for mode, st in (("self", items), ("given", items + given)):
        d, ms = call(key, st, {"q": noul(qtext)})
        p = d["answers"]["q"]["noul"]
        r[mode] = dict(p=p, ok=(p >= .5) == over, ms=round(ms))
    rows.append(r)
json.dump(rows, open("arith100.json", "w"), ensure_ascii=False, indent=1)
for mode in ("self", "given"):
    for lang in ("zh", "en", "all"):
        rs = [r for r in rows if lang == "all" or r["lang"] == lang]
        k = sum(r[mode]["ok"] for r in rs); n = len(rs); lo, hi = wilson(k, n)
        yes = sum(r[mode]["p"] >= .5 for r in rs)
        wrong = [max(r[mode]["p"], 1-r[mode]["p"]) for r in rs if not r[mode]["ok"]]
        wc = f"{sum(wrong)/len(wrong):.2f}" if wrong else "-"
        hi8 = sum(w >= .8 for w in wrong)
        print(f"{mode:5} {lang:3} 对 {k}/{n}  95%区间 {lo:.0%}-{hi:.0%}  答'超过' {yes}/{n}  错题平均把握 {wc}  错题中把握≥0.8 {hi8}")
