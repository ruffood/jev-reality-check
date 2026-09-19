"""算术门槛梯度: 门槛离真实总价 3% / 10% / 30% / 50%, 每档 12 题, 对比"自己算"和"合计由代码给出"。"""
import random, sys
sys.path.insert(0, '.')
from run import call, load_key
from cases import noul
key = load_key(); rng = random.Random(7)
G = ["跑鞋", "T恤", "保温杯", "耳机", "背包", "袜子"]
def order():
    idx = rng.sample(range(len(G)), 3)
    lines = [(G[k], rng.randint(1, 4), rng.randint(19, 299)) for k in idx]
    return lines, sum(q*p for _, q, p in lines)
def ask(state, thr):
    d, _ = call(key, state, {"over": noul(f"这笔订单的商品总价是否超过 {thr} 元？")})
    return d["answers"]["over"]["noul"]
for label, m in [("±3%", .03), ("±10%", .10), ("±30%", .30), ("±50%", .50)]:
    ok = okc = 0; n = 12
    for i in range(n):
        lines, total = order(); over = i % 2 == 0
        thr = round(total * (1 - m)) if over else round(total * (1 + m))
        items = "\n".join(f"- {a} × {q}，单价 {p} 元" for a, q, p in lines)
        ok += (ask("订单明细：\n" + items, thr) >= .5) == over
        okc += (ask("订单明细：\n" + items + f"\n合计：{total} 元", thr) >= .5) == over
    print(f"{label:5}  自己算 {ok}/{n}   给了合计 {okc}/{n}")
