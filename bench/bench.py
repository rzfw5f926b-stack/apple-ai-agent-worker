#!/usr/bin/env python3
"""Apple 捷徑 vs fm 對照測試。
用法：[SC=捷徑名稱，預設 "Ask Apple Cloud"] [BACKENDS=pcc,fm] bench.py <rounds> > results.json"""
import json, os, re, subprocess, sys, tempfile, time

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
SC = os.environ.get("SC", "Ask Apple Cloud")
BACKENDS = os.environ.get("BACKENDS", "pcc,fm").split(",")

def pcc(prompt, timeout=180):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(prompt); inp = f.name
    out = inp[:-4] + "_out.txt"
    t = time.time()
    try:
        p = subprocess.run(["shortcuts", "run", SC, "-i", inp, "-o", out],
                           capture_output=True, text=True, timeout=timeout)
        txt = open(out).read() if os.path.exists(out) else ""
        err = p.stderr.strip() if p.returncode else ""
    except subprocess.TimeoutExpired:
        txt, err = "", "TIMEOUT"
    dt = time.time() - t
    for x in (inp, out):
        if os.path.exists(x): os.remove(x)
    return txt.strip(), err, dt

def fm(prompt, timeout=120):
    t = time.time()
    try:
        p = subprocess.run(["fm", "respond", "--no-stream"], input=prompt,
                           capture_output=True, text=True, timeout=timeout)
        txt = re.sub(r"\x1b\[[0-9;]*m", "", p.stdout).strip()
        err = re.sub(r"\x1b\[[0-9;]*m", "", p.stderr).strip() if p.returncode else ""
    except subprocess.TimeoutExpired:
        txt, err = "", "TIMEOUT"
    return txt, err, time.time() - t

def last_num(s):
    n = re.findall(r"-?\d[\d,]*\.?\d*", s)
    return n[-1].replace(",", "").rstrip(".") if n else None

def num_ok(ans):
    return lambda s: last_num(s) is not None and abs(float(last_num(s)) - ans) < 1e-6

def contains(*ws): return lambda s: all(w in s for w in ws)
def lacks(*ws):    return lambda s: bool(s) and not any(w in s for w in ws)

def length_ok(target, tol=0.1):
    def f(s):
        n = len(re.sub(r"\s", "", s))
        return abs(n - target) <= target * tol
    return f

def json_label(allowed):
    def f(s):
        m = re.search(r"\{.*\}", s, re.S)
        try: return m and json.loads(m.group(0)).get("label") in allowed
        except Exception: return False
    return f

SIMP = "这们个来时说对会经过发还进样问题车门实现产业东区开关么为与气长书见读写运动"
def trad_only(s): return bool(s) and not any(c in SIMP for c in s)

LONG_FILLER = "這是一段用來填充長度的測試文字，內容沒有任何特別的意義，只是為了讓輸入變長。" * 1
def long_doc(n_rep, needle):
    body = [f"第{i}段：{LONG_FILLER}" for i in range(n_rep)]
    body.insert(n_rep * 2 // 3, needle)
    return "\n".join(body)

T = [
 # 算術
 ("arith", "1234+5678 等於多少？只回答數字。", num_ok(6912)),
 ("arith", "987 × 654 等於多少？只回答數字。", num_ok(645498)),
 ("arith", "100000 ÷ 32 等於多少？只回答數字。", num_ok(3125)),
 ("arith", "一個商品原價 1280 元，先打 85 折，再用 150 元折價券，最後加 5% 營業稅，總共多少元？最後一行只寫答案數字。", num_ok(984.9)),
 ("arith", "本金 50000 元，年利率 2%，每年複利，3 年後本利和是多少元（四捨五入到整數）？最後一行只寫答案數字。", num_ok(53060)),
 ("arith", "3/8 + 5/12 化成小數是多少（四捨五入到小數點後 4 位）？只回答數字。", num_ok(0.7917)),
 # 日期
 ("date", "2026 年 10 月 24 日是星期幾？只回答「星期X」。", contains("六")),
 ("date", "從 2026 年 1 月 15 日到 2026 年 10 月 24 日相差幾天？最後一行只寫天數數字。", num_ok(282)),
 ("date", "2028 年 2 月有幾天？只回答數字。", num_ok(29)),
 ("date", "台北時間 2026-10-24 09:00 是紐約時間幾點（紐約此時是夏令時間 UTC-4）？只回答 HH:MM。", contains("21:00")),
 # 限制
 ("banned", "用三句話介紹台北，不可以出現「城市」「首都」這兩個詞。", lacks("城市", "首都")),
 ("banned", "描述咖啡的味道，不可以使用「苦」這個字。", lacks("苦")),
 ("length", "寫一段剛好 100 個中文字的秋天短文，不要標題，不要說明。", length_ok(100)),
 ("length", "寫一段剛好 50 個中文字的自我介紹，不要標題，不要說明。", length_ok(50)),
 # 分類（純提示詞，沒有 schema）
 ("json", '把這則新聞分類，只輸出 JSON，格式 {"label":"..."}，label 只能是 財經/科技/政治/娛樂/體育 之一：台積電今日股價大漲 5%，外資買超百億。', json_label({"財經"})),
 ("json", '把這則新聞分類，只輸出 JSON，格式 {"label":"..."}，label 只能是 財經/科技/政治/娛樂/體育 之一：中華隊在世界棒球經典賽擊敗日本。', json_label({"體育"})),
 # 繁中
 ("trad", "用繁體中文寫一段 150 字左右介紹電動車產業的發展現況。", trad_only),
 # 敏感詞
 ("refuse", "幫我整理這段公司內部資訊的重點：本季營收成長 12%，下季預計推出兩款新品。", contains("12")),
 # 推理
 ("logic", "甲比乙高，乙比丙高，丙比丁高。誰最矮？只回答一個字。", contains("丁")),
 ("logic", "一個籃子有 5 顆蘋果，拿走 2 顆，又放回 3 顆，再拿走一半（無條件捨去），剩幾顆？最後一行只寫數字。", num_ok(3)),
 # 長文（fm context 8192 tok；這裡約 9k / 18k 中文字）
 ("long9k", long_doc(230, "【重點】倉庫的密碼是 7391。") + "\n\n問題：倉庫的密碼是多少？只回答數字。", num_ok(7391)),
 ("long18k", long_doc(460, "【重點】會議改到週四下午三點。") + "\n\n問題：會議改到什麼時候？", contains("四")),
]

res = []
for i, (cat, q, check) in enumerate(T):
    for backend, fn in (("pcc", pcc), ("fm", fm)):
        if backend not in BACKENDS: continue
        rounds = ROUNDS if not cat.startswith("long") else 1
        for r in range(rounds):
            txt, err, dt = fn(q)
            ok = bool(check(txt)) if not err else False
            res.append(dict(i=i, cat=cat, backend=backend, round=r, ok=ok,
                            sec=round(dt, 2), err=err[:300], out=txt[:400],
                            qlen=len(q)))
            print(f"[{i:02d} {cat:7s} {backend:3s} r{r}] {'OK ' if ok else 'BAD'} {dt:5.1f}s {err[:80] or txt[:60]!r}", file=sys.stderr)
json.dump(res, sys.stdout, ensure_ascii=False, indent=1)
