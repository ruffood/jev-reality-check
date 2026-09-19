"""跑 Jev 实测。

用法:
  python3 run.py --limit 3          # 每组只跑 3 条, 冒烟测试
  python3 run.py                    # 全量
  python3 run.py --parallel         # 测 1/5/20 个问题的延迟差异
key 从环境变量 TYPESAFE_API_KEY 或同目录 .env 读取。
"""
import argparse, json, os, statistics, sys, time, urllib.error, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from cases import CASES, ROUTE, noul, choice  # noqa: E402

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
PRICE_PER_M = 0.042  # 美元 / 百万输入 token, 输出免费
HIGH_CONF = 0.8


def load_key():
    if os.environ.get("TYPESAFE_API_KEY"):
        return os.environ["TYPESAFE_API_KEY"]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("TYPESAFE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"\'')
    sys.exit("找不到 TYPESAFE_API_KEY")


def call(key, state, questions, retries=5):
    body = json.dumps({"model": MODEL, "state": state, "questions": questions}).encode()
    for attempt in range(retries):
        req = urllib.request.Request(URL, body, {
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            return data, (time.perf_counter() - t0) * 1000
        except urllib.error.HTTPError as e:
            if e.code in (429, 529) and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:300]}")


def judge(ans, expected):
    """返回 (模型答案, 把握度, 是否正确 或 None)"""
    if ans["type"] == "noul":
        p = ans["noul"]
        got = p >= 0.5
        return got, max(p, 1 - p), None if expected is None else got == expected
    got = ans["choice"]
    return got, ans.get("confidence"), None if expected is None else got == expected


def run_cases(key, limit):
    seen = defaultdict(int)
    out = ROOT / "results.jsonl"
    rows = []
    with out.open("w") as f:
        for c in CASES:
            if limit and seen[(c["group"], c["lang"])] >= limit:
                continue
            seen[(c["group"], c["lang"])] += 1
            data, ms = call(key, c["state"], c["questions"])
            for qk, exp in c["expected"].items():
                ans = data["answers"][qk]
                got, conf, ok = judge(ans, exp)
                row = dict(id=c["id"], group=c["group"], lang=c["lang"], q=qk,
                           expected=exp, got=got, conf=conf, ok=ok, ms=round(ms),
                           tokens=data["usage"]["input_tokens"], raw=ans)
                rows.append(row)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                mark = {True: "✓", False: "✗", None: "·"}[ok]
                print(f"{mark} {c['id']:10} {c['lang']} got={got!s:6} exp={exp!s:6} "
                      f"conf={conf if conf is None else round(conf, 2)} {round(ms)}ms")
    summarize(rows)


def summarize(rows):
    print("\n组别        语言  准确率      高把握却答错  错题平均把握  p50ms  p95ms")
    groups = defaultdict(list)
    for r in rows:
        groups[(r["group"], r["lang"])].append(r)
    for (g, lang), rs in groups.items():
        graded = [r for r in rs if r["ok"] is not None]
        wrong = [r for r in graded if not r["ok"]]
        ms = sorted(r["ms"] for r in rs)
        p95 = ms[min(len(ms) - 1, int(len(ms) * 0.95))]
        acc = f"{sum(r['ok'] for r in graded)}/{len(graded)}" if graded else "-"
        hc = sum(1 for r in wrong if r["conf"] and r["conf"] >= HIGH_CONF)
        wc = round(statistics.mean(r["conf"] for r in wrong), 2) if wrong else "-"
        if not graded:  # 强制选择组: 报高把握选了个错选项的次数
            hc = sum(1 for r in rs if r["conf"] and r["conf"] >= HIGH_CONF)
            wc = round(statistics.mean(r["conf"] for r in rs), 2)
        print(f"{g:8} {lang:4}  {acc:10}  {hc:<12}  {wc!s:<12}  {ms[len(ms)//2]:<5}  {p95}")
    tok = sum({r['id']: r['tokens'] for r in rows}.values())
    print(f"\n总输入 token {tok}，费用约 ${tok * PRICE_PER_M / 1e6:.6f}")


def run_parallel(key, reps=5):
    state = "顾客消息：鞋子尺码发错了，而且信用卡上还多扣了一笔钱，你们打算怎么办？"
    extra = [noul(f"顾客是否提到了{w}？") for w in
             ["退款", "尺码", "扣款", "物流", "发票", "投诉", "愤怒", "紧急", "会员",
              "优惠券", "差评", "法律", "律师", "媒体", "换货", "地址", "电话", "时间", "价格"]]
    for n in (1, 5, 20):
        qs = {"team": choice("这条消息应该派给哪个团队？", ROUTE)}
        qs.update({f"q{i}": q for i, q in enumerate(extra[: n - 1])})
        times, toks = [], []
        for _ in range(reps):
            data, ms = call(key, state, qs)
            times.append(ms)
            toks.append(data["usage"]["input_tokens"])
        print(f"{n:2} 个问题: 延迟中位数 {statistics.median(times):.0f}ms "
              f"(全部 {[round(t) for t in times]})，输入 token {toks[0]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--parallel", action="store_true")
    a = ap.parse_args()
    k = load_key()
    run_parallel(k) if a.parallel else run_cases(k, a.limit)
