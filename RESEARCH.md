# Apple AI 能力研究專案

**建立日期：2026-06-07**  
**目標：** 測試 Apple 各 AI 路徑的能力邊界，評估能否作為 Claude 的低成本 sub-worker

---

## 模型版本一覽

Apple AI 有多個模型與執行路徑，本專案測試了以下幾種：

| ID | 模型 | 規格 | 執行路徑 | 測試日期 |
|----|------|------|---------|---------|
| **A** | AFM Core 3B | 3B Dense, 2-4bit 混合量化, on-device Neural Engine | `apple-fm-sdk` Python API | 2026-06-07 |
| **B** | AFM Core 3B（Ollama 包裝）| 同 A，換成 HTTP API | `POST localhost:11436`（`server.py`）| 2026-06-10 |
| **C** | AFM Cloud PCC | 雲端推理，tier 未知（PCC / Cloud Pro？）| `shortcuts run "Apple Intelligence"` | 2026-06-10 |
| **D** | AFM Core Advanced 20B MoE | active 1-4B, on-device, macOS 27 新增 | `apple-fm-sdk 0.2.0`（v0.2.0 + Xcode 27 後自動啟用）| 2026-06-11 |

> **A 與 B 的關係：** 使用相同底層模型，B 只是把 A 包成 Ollama 相容 HTTP API，方便 Python `requests` 呼叫。
>
> **C 的 tier：** Shortcuts「使用模型」Action 實際走哪一層 PCC（Apple server vs Google Cloud Pro）目前無法從外部確認，以延遲特性（1.5–3s）推測為 PCC 標準層。
>
> **D 的狀態：** macOS 27 升級後 `apple-fm-sdk` 預設是否已切換至 Core Advanced 尚未驗證，server.py 仍回報 `3B`，可能是 metadata 未更新或確實仍跑 3B。

---

## 安裝紀錄（適用 Model A / B / D）

### 需求
- macOS 27 (Golden Gate) — 內部版號 26.x
- Apple Silicon (M1+)
- Apple Intelligence 啟用
- Python 3.10+
- Xcode 26+（Command Line Tools）

### 安裝方式

```bash
pip3 install apple-fm-sdk --break-system-packages
```

> **舊版（macOS 26 Tahoe）**：需 clone repo 並修改 `build_backend.py` 繞過 Xcode check，macOS 27 後已不需要。

### 基本用法

```python
import apple_fm_sdk as fm
import asyncio

async def main():
    session = fm.LanguageModelSession()
    r = await session.respond("你的問題")
    print(r)

asyncio.run(main())
```

### 多輪對話（重用 session）

同一個 `LanguageModelSession` 物件連續呼叫 `respond()` 有完整多輪記憶。
**每次 `new LanguageModelSession()` 才會失去記憶**——這是之前錯誤評估「0/5」的原因。

```python
async def chat():
    s = fm.LanguageModelSession()
    await s.respond("我叫 Alice。")
    await s.respond("我喜歡藍色。")
    r = await s.respond("列出你知道關於我的事。")
    # ✅ 正確列出：Alice + 藍色
```

### Permissive Guardrail

```python
model = fm.SystemLanguageModel(
    guardrails=fm.SystemLanguageModelGuardrails.PERMISSIVE_CONTENT_TRANSFORMATIONS
)
session = fm.LanguageModelSession(model=model)
```

### Structured Output

```python
@fm.generable
class Result:
    label: str
    confidence: int

r = await session.respond("分類這段文字...", generating=Result)
print(r.label, r.confidence)
```

---

---

## 測試結果

---

### [Model A · AFM Core 3B · on-device · apple-fm-sdk] 2026-06-07

#### 模型基本資訊

| 項目 | 數值 |
|------|------|
| 參數量 | ~3B（混合 2-bit / 4-bit 量化） |
| 推理位置 | Apple Neural Engine（完全 on-device） |
| Context Window | ~4096 tokens（≈ 5501 中文字） |
| 回應速度（簡單） | 0.22s |
| 回應速度（複雜） | 2.09s |
| 整體評分 | 3.3 / 5 |

---

### 能力分類

#### ✅ 強項（可穩定依賴）

| 能力 | 分數 | 備註 |
|------|------|------|
| 中文品質 | 5/5 | 摘要、文體切換、繁體純度全滿分 |
| 回應速度 | — | 0.22~2s，零網路延遲 |
| Markdown / Table 格式輸出 | 5/5 | 穩定 |
| Structured Output（非財經） | 5/5 | dataclass、巢狀、list 欄位 |
| 基本推理 | 5/5 | 文字題、矛盾偵測、情感分類 |
| 英文摘要 | 5/5 | 流暢精準 |
| JSON 嚴格輸出 | 5/5 | 完全遵守格式 |

#### ⚠️ 中等（可用但需驗證）

| 能力 | 分數 | 備註 |
|------|------|------|
| 翻譯（英→繁中） | 4/5 | on-device 版無 bug；偶爾偏字面直譯 |
| 指令遵守（格式類） | 4/5 | table/bullet 好，語意類不穩 |

#### ❌ 弱項（不建議依賴）

| 能力 | 分數 | 問題 |
|------|------|------|
| 字數精確控制 | 1/5 | 要求50字 → 輸出125字 |
| 禁止詞遵守 | 1/5 | 明確說禁止還是違規 |
| 多輪對話記憶 | 5/5 | **同一 session 物件**完全有記憶；每次 new session 才失效 |
| 時區 / 複雜時間計算 | 1/5 | 台灣9點-13小時答「下午12點」（正確：前一天20:00）|
| 事實準確性 | — | 偶發錯誤（清邁誤列為台灣景點）|
| 超長輸入 | — | 超過 5501 字靜默截斷，不報錯 |

---

### Hard Limit

**財經 Structured Output 完全封鎖**
- 股票分析（recommendation、price_target）
- 財經新聞分類（結構化格式）
- 不論用 `generable`、`json_schema`、改欄位名、permissive guardrail，一律擋
- **純文字財經內容可通過**，workaround：純文字取得 → 自行 parse

---

### Context Window 測試（needle-in-haystack）

| 輸入長度 | 開頭 | 中間 | 結尾 |
|---------|------|------|------|
| 1000字 | ✅ | ✅ | ✅ |
| 3000字 | ✅ | ✅ | ✅ |
| 5000字 | ✅ | ✅ | ✅ |
| **5501字** | ✅ | ✅ | ✅ |
| **5502字** | ❌ | ❌ | ❌ |
| 8000字 | ❌ | ❌ | ❌ |

**精確邊界：5501 字（≈ 4096 tokens）**
超過邊界為靜默截斷，模型不報錯。

---

### Guardrail 行為

| 設定 | 一般內容 | 財經結構化 | 有害內容 |
|------|---------|-----------|---------|
| `DEFAULT` | 部分誤判 | ❌ | ✅ 擋 |
| `PERMISSIVE` | 誤判修正 | ❌ 仍擋 | ✅ 擋 |

- 身高排序等無害內容在 DEFAULT 下被誤判，切換 PERMISSIVE 可解
- 財經 structured output 是 hard block，無法繞過

---

### 呼叫架構

```
Python 程式碼
  ↓
apple_fm_sdk Python API
  ↓
ctypes bindings（自動生成）
  ↓
Swift C bridge（libFoundationModels.dylib）
  ↓
Apple FoundationModels framework（macOS 26 系統框架）
  ↓
Neural Engine（完全 on-device，無網路）
```

**vs Shortcuts 方式的差異：**
- Shortcuts：需要 app 前景 session、雲端模型（有 bug）、RTF 輸出需轉換
- SDK：直接 Python API、on-device、無 session 限制、無格式轉換

---

---

### [Model A · AFM Core 3B · on-device · apple-fm-sdk] 2026-06-07 補測：Generation Guides、CONTENT_TAGGING、Tool Calling

### Generation Guides（輸出約束）

SDK 提供 `GuideType`：`anyOf`、`range`、`minimum`、`maximum`、`minItems`、`maxItems`、`count`、`element`、`constant`、`regex`

| Guide | 結果 | 備註 |
|---|---|---|
| `anyOf` | ✅ 完美 | 強制 token 只能輸出指定值，不靠模型遵守指令 |
| `range` / `minimum` / `maximum` | ✅ 正常 | 數字邊界有效（confidence 0–100 測試通過）|
| `regex` | ❌ GenerationError status 255 | 不可用 |

**`anyOf` 是最實用的 guide**：解掉了先前「禁止詞遵守只有 50%」的問題。分類任務強烈建議用 `anyOf` 而非自由文字輸出。

```python
@fm.generable
class Category:
    label: str = fm.guide(anyOf=["財經", "科技", "政治", "娛樂"])
    confidence: int = fm.guide(minimum=0, maximum=100)
```

---

### CONTENT_TAGGING Use Case

| 面向 | GENERAL | CONTENT_TAGGING |
|---|---|---|
| 遵守分類指令 | ✅ | ❌ 忽視，輸出 meta-label（「情感分析」而非「正面」）|
| 中文財經 | ✅ | ❌ ExceededContextWindowSizeError（64字即炸）|
| 英文內容 | ✅ | 🔶 能用，但 tag 很通用（`technology, performance`）|
| 政治/天氣新聞 | ✅ | ❌ Refused（guardrail 更嚴）|

**結論：CONTENT_TAGGING 是 Apple 內部系統用**（App Store/Siri 自動分類），不適合開發者自訂 prompt。所有用途繼續用 `GENERAL`。

---

### Tool Calling 完整評估

模型可在生成過程中呼叫 Python async 函數（類似 Claude function calling，完全 on-device）。

#### 定義方式

```python
@fm.generable("Tool parameters")
class MyParams:
    value: str = fm.guide("Description of value")

class MyTool(fm.Tool):
    name = "my_tool"
    description = "What this tool does"

    @property
    def arguments_schema(self) -> fm.GenerationSchema:
        return MyParams.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        val = args.value(str, for_property="value")  # 注意：用 args.value()，不是 args.content.get()
        return f"result: {val}"

session = fm.LanguageModelSession(tools=[MyTool()])
```

#### 評估結果（2026-06-07）

| 場景 | 結果 | 備註 |
|---|---|---|
| 多工具選擇（3 個 tool）| ✅ 完美 | 每次選對對應的 tool |
| 不需 tool 時自動繞過 | ✅ 完美 | 一般問答直接回答，不亂呼叫 |
| 多輪 session tool 記憶 | ✅ 完美 | 第 2 輪記得上輪 tool 結果 |
| Tool 拋出例外 | ✅ 優雅降解 | 不崩潰，通知用戶失敗 |
| 跨 tool 串接推理 | ⚠️ 失敗 | 同時觸發兩個 tool 而非依序，用幻想值計算 |
| 中文 city name 傳入 | ⚠️ 小問題 | 傳入「台北」而非「taipei」，tool 內需做正規化 |

**限制**：適合「單步 tool 呼叫」，不適合「A 結果餵給 B」的串接規劃任務（3B 模型規劃能力上限）。

---

### [Model A · AFM Core 3B · on-device · apple-fm-sdk] 2026-06-07 補測：GenerationOptions、SamplingMode、Session 歷史

### Session 多輪記憶修正

**先前評估「0/5」是錯誤的**。同一個 `LanguageModelSession` 物件連續 `respond()` 有完整多輪記憶（姓名、顏色、數字累加全通過）。失效的原因是 one-liner pattern 每次都 `new session()`，不是模型問題。

```python
s = fm.LanguageModelSession()         # 建立一次
await s.respond("我叫 Alice。")
await s.respond("我喜歡藍色。")
r = await s.respond("列出你知道的事。")  # ✅ Alice + 藍色都記得
```

**Transcript**：`s.transcript` 可讀，async `to_dict()`，每輪記 2 entries（user + response）。只能讀，無法注入新 session。

---

### GenerationOptions 完整評估

```python
options = fm.GenerationOptions(
    temperature=0.0,                  # 0.0 確定性 / 1.0 隨機
    maximum_response_tokens=30,       # 限制輸出長度
    sampling=fm.SamplingMode(fm.SamplingModeType.GREEDY)  # 完全確定性
)
r = await session.respond(prompt, options=options)
```

#### Temperature

| 值 | 行為 |
|---|---|
| `0.0` | 確定性，同 prompt 兩次輸出完全相同 ✅ |
| `0.5` | 輕微變化，適合翻譯/摘要 |
| `1.0` | 真隨機，每次不同 ✅ |

#### maximum_response_tokens — 速度槓桿

| limit | 輸出字數 | 速度 |
|---|---|---|
| 無限制 | 792 字 | 8.33s |
| 30 tokens | 42 字 | **0.61s** |
| 10 tokens | 10 字 | **0.25s** |

**最重要的發現**：限制 token 數可把慢速長文任務壓到 0.25s，比無限制快 10-30 倍。代價是輸出截斷在句子中間。適合只需要短答案的場景（分類、情感、是非題）。

#### SamplingMode

| 模式 | 結果 |
|---|---|
| `GREEDY` | ✅ 完全確定性，三次 bit-for-bit 相同，比 temperature=0.0 更嚴格 |
| `RANDOM + seed` | ❌ seed 無效，同 seed 三次輸出不同 |

#### json_schema 參數

`respond()` 支援 `json_schema={}` 傳入原始 JSON Schema dict（不需要 `@generable` class）。**實測 ❌ GenerationError status 255**，與 regex guide 同樣問題，不可用。

---

## 待測項目

- [x] ~~純文字財經 + 自行 parse~~ → 財經 Structured Output 已解鎖，不再需要
- [x] ~~Streaming 在長文生成的表現~~ → 見下方 2026-06-11 測試
- [x] ~~ImageAttachment 審圖~~ → v0.2.0 正常，見下方 2026-06-11 測試
- [x] ~~AFM Core Advanced 是否有 API 可選~~ → 見下方 2026-06-11 測試
- [x] ~~多輪記憶問題~~ → 修正：同 session 物件有記憶，one-liner 每次 new session 才失效
- [x] ~~contentTagging use case~~ → 不建議用（Apple 內部系統用）
- [x] ~~json_schema 參數~~ → **v0.1.1 修好，需加 `x-order` 頂層陣列** ✅
- [x] ~~RANDOM seed~~ → seed 參數無效
- [x] ~~財經 Structured Output~~ → macOS 27 已解鎖 ✅
- [x] ~~WWDC 2026-06-09 後重測~~ → 完成，見下方
- [x] ~~Shortcuts「使用模型」Action 能力測試~~ → 完成，見下方

---

### [Model A · AFM Core 3B · on-device · apple-fm-sdk 0.1.1] 2026-06-09 macOS 27 升級後測試結果

> ⚠️ **注意：** apple-fm-sdk 仍為 0.1.1，`server.py` 回報 `3B`。根據 2026-06-11 的測試，v0.2.0 + Xcode 27 後才切換至 Core Advanced（Model D）。因此本節測試的仍是 **Model A（3B）**，只是在 macOS 27 環境下跑。

**測試環境：** macOS 27.0 (26A5353q) · Python 3.14.5 · apple-fm-sdk 0.1.1

### 安裝方式（已簡化）

macOS 27 後官方 `pip install` 可直接使用，**不再需要 clone + patch**：

```bash
pip3 install apple-fm-sdk --break-system-packages
```

舊版需求（Xcode check 繞過）已廢棄。

---

### ⚠️ API Breaking Change：respond() 回傳型別

```python
# 舊版（macOS 26）
r = await session.respond("...")
print(r.content)   # ← r 是物件

# 新版（macOS 27）
r = await session.respond("...")
print(r)           # ← r 直接是 str
```

**影響範圍：** 所有使用 `r.content` 的程式碼需改為直接使用 `r`。

---

### 變更摘要

| 項目 | 舊版（macOS 26，3B）| 新版（macOS 27）| 狀態 |
|------|-------------------|----------------|------|
| 安裝方式 | clone + patch build_backend.py | `pip install apple-fm-sdk` | ✅ 簡化 |
| respond() 回傳 | 物件（`.content`） | 直接 `str` | ⚠️ Breaking |
| 財經 Structured Output | ❌ Hard Block | ✅ **完全通過** | 🔥 重大改善 |
| Context Window | ~5,501 字（4096 tokens） | **~14,600 字** | 📈 **2.6 倍** |
| 速度（暖身後） | 0.22s | 0.45s | 稍慢 |
| 中文品質 | 5/5 | 5/5（維持）| ✅ |

---

### json_schema 參數（v0.1.1 修好）

之前 GenerationError 255，macOS 27 後可用。格式需在**頂層**加 `x-order` 陣列：

```python
schema = {
    "type": "object",
    "title": "StockSignal",
    "additionalProperties": False,
    "x-order": ["ticker", "direction", "reason"],  # ← 必填，頂層陣列
    "properties": {
        "ticker":    {"type": "string"},
        "direction": {"type": "string"},
        "reason":    {"type": "string"}
    },
    "required": ["ticker", "direction", "reason"]
}
r = await session.respond("分析台積電", json_schema=schema)
content = r.value(dict)  # {"ticker": "2330", "direction": "買入", ...}
```

---

### 財經 Structured Output（已解鎖）

之前完全封鎖的場景現在正常運作：

```python
@fm.generable
class StockSignal:
    ticker: str
    direction: str  # BUY / SELL / HOLD
    reason: str

r = await session.respond("分析台積電現在的投資信號", generating=StockSignal)
# ✅ ticker='2330', direction='買入', reason='半導體需求強勁...'
```

---

### Context Window 測試（macOS 27）

| 輸入長度 | 結果 |
|---------|------|
| 5,501 字 | ✅（舊上限） |
| 8,000 字 | ✅ |
| 12,000 字 | ✅ |
| 14,600 字 | ✅ |
| **14,800 字** | ❌ ExceededContextWindowSizeError |

**新精確邊界：~14,600 字**（vs 舊版 5,501 字，約 2.6 倍）

---

### [Model B · AFM Core 3B · localhost:11436] + [Model C · AFM Cloud PCC · shortcuts] 2026-06-10 對比測試

### 背景

macOS 27 Shortcuts 新增「使用模型」Action，可透過 CLI 呼叫：

```bash
echo "<prompt>" | shortcuts run "Apple Intelligence" --output-type public.plain-text
```

此路徑走 **PCC 雲端（Private Cloud Compute）**，與 apple-fm-sdk on-device 是不同模型。本輪測試比較兩者能力差異。

---

### 基礎測試（12 題）

> **執行方式：** `shortcuts run "Apple Intelligence" --output-type public.plain-text`（PCC 雲端）
> 腳本：`~/Desktop/test_apple_intelligence.sh`

| 項目 | Shortcuts PCC | 備註 |
|------|--------------|------|
| 一般問答 | ✅ | 真正 LLM 推理，非單純改寫 |
| 長度控制 | ✅ | 20字/100字指令有效 |
| 標題＋內文格式 | ✅ | 可直接 parse |
| 語氣控制 | ✅ | 「輕鬆易懂」有效 |
| Hashtag 生成 | ✅ | 無空格、中英混合 |
| Carousel 3頁格式 | ✅ | 格式完全正確 |
| 一致性 | ✅ | **Deterministic**，同 prompt 輸出 bit-for-bit 相同 |
| 財經敏感詞攔截 | ✅ | 股票推薦、內線消息均擋 |
| 長文摘要（500字）| ⚠️ | 19.78s，太慢 |
| 速度（一般任務）| ✅ | 1.5–3s |

---

### 進階測試（9 題）

> **執行方式：** `shortcuts run "Apple Intelligence" --output-type public.plain-text`（PCC 雲端）
> 腳本：`~/Desktop/test_apple_intelligence_hard.sh`

| 項目 | 結果 |
|------|------|
| Prompt Injection 防禦 | ✅ 擋住，但觸發時耗時 34.72s |
| 格式干擾（新聞含「標題：」）| ✅ 不影響輸出格式 |
| 連續 3 次呼叫 | ✅ 無 throttle，1.47/1.54/1.45s |
| 完整 IG Pipeline 模擬 | ✅ 標題+內文+hashtag 一次輸出，15.81s |

---

### 極限測試（8 題）

> **執行方式：** `shortcuts run "Apple Intelligence" --output-type public.plain-text`（PCC 雲端）
> 腳本：`~/Desktop/test_apple_intelligence_extreme.sh`

| 測項 | 結果 | 說明 |
|------|------|------|
| 精確 50 字計數 | ⚠️ 輸出 51 字 | 計數誤差 ±3 字 |
| 6 條規則同時施加 | ❌ 2 項違規 | 標題字數錯、hashtag 缺 `#` 前綴 |
| 反幻覺（假數據 △△△◯◯◯）| ✅ 完美 | 不腦補，原文照搬佔位符 |
| 財務計算（四則）| ✅ 正確 | 920×10K=920萬，損益20萬，3.59s |
| 1500 字長文輸入 → 50 字摘要 | ✅ 優秀 | 12.62s，核心觀點全抓到 |
| 風格克隆（3 範例仿寫）| ⚠️ 形似神不似 | 40.54s |
| 五日行事曆（最長輸出）| ✅ 格式正確 | 11.52s，183 chars |
| 中日英混合輸入 | ✅ 正確輸出繁體中文 | 2.46s |

#### 速度異常模式

正常任務 1.5–5s；以下情境觸發 **12–40s**：

| 情境 | 耗時 |
|------|------|
| Prompt Injection 偵測 | 34.72s |
| 假佔位符輸入（△△△）| 37.52s |
| 風格克隆 | 40.54s |
| 精確字數計數 | 14.61s |

**推論：PCC 雲端在不確定時重試，非 on-device 行為。**

---

### on-device 3B（localhost:11436）vs PCC 雲端（Shortcuts）對比

> **執行方式：** 腳本 `~/Desktop/test_hongwan.py`
> - TEST A：`POST http://localhost:11436/api/generate`（apple-fm-sdk server，on-device 3B）
> - TEST B：`shortcuts run "Apple Intelligence" --input-path /tmp/prompt.txt`（PCC 雲端）

完整 IG 文案生成測試（Caption + Hashtag + 圖片 Prompt + 標題）：

| 項目 | on-device 3B | PCC 雲端 |
|------|-------------|---------|
| Caption 字數 | ~400 字 | ~350 字 |
| 鉤子品質 | ⚠️ 普通 | ✅ 反直覺問句 |
| Hashtag 格式 | ❌ 有空格、`#核心簡報`（翻譯錯）| ✅ 無空格、`#core_brief` 正確 |
| 圖片 Prompt | ✅ | ✅ |
| 標題 | ✅ | ✅ |
| 速度 | 9.59s | 5.34s |

**結論：PCC 雲端品質優於 on-device 3B。兩者輸出長度均約 350–400 字，無法達到 900 字以上的長文要求。**

---

### 能力邊界總結（2026-06-10 確認）

#### 適合用途
- 短文生成：標題、副標題、hashtag、圖片 prompt
- 文字壓縮：1500 字以內 → 50 字摘要
- 財務四則運算
- 多語言輸入 → 繁體中文輸出
- 行事曆規劃、多頁格式輸出
- 最多同時 3–4 條規則

#### 不適合用途
- 長文生成（1000 字以上）：上限約 350–450 字
- 精確字數控制（誤差 ±3 字）
- 超過 4 條規則同時施加
- 精確風格克隆
- 任何觸發「異常」判斷的輸入（30–40s）

#### Sub-worker 取代評估

| Claude 任務 | 可否換成 Apple Intelligence | 備註 |
|------------|--------------------------|------|
| IG hashtag 生成 | ✅ | Shortcuts PCC |
| IG 標題 / 副標題 | ✅ | Shortcuts PCC |
| IG 圖片 prompt | ✅ | Shortcuts PCC |
| **IG Caption（1000 字）**| ❌ | 僅能生 350–400 字，深度不足 |
| 新聞摘要（短）| ✅ | ≤ 1500 字輸入 |
| 複雜分析 / 非共識視角 | ❌ | 推理深度不足 |

---

### [Model D · AFM Core Advanced 20B MoE · on-device · apple-fm-sdk 0.2.0] 2026-06-11：v0.2.0 升級 + 剩餘待測項目

**測試環境：** macOS 27.0 · Python 3.14 · apple-fm-sdk 0.2.0 · Xcode 27 beta

### API Breaking Changes（v0.1.x → v0.2.0）

| 項目 | 舊版 | 新版 |
|------|------|------|
| Generable 定義方式 | `class Foo(fm.Generable):` | `@fm.generable()` + `@dataclass` |
| Structured Output 參數 | `response_format=Foo` | `generating=Foo` |
| ImageAttachment path | 字串 `"/path/to/img"` | `Path("/path/to/img")` 物件 |

### 速度基準重測（20B MoE）

| 任務 | 耗時 |
|------|------|
| 簡單一句話 | 0.26s |
| 中等摘要 | 1.18s |
| 財經 Structured Output | 0.59s |
| ImageAttachment 審圖 | 1.36s |
| 長文生成（~892 字） | 14.5s |

### ImageAttachment（新功能）

```python
from pathlib import Path
import apple_fm_sdk as fm

s = fm.LanguageModelSession()
img = fm.ImageAttachment(path=Path("/path/to/image.png"))
r = await s.respond([img, "這張圖是什麼？"])
```

✅ 正常，可描述圖片內容。注意 `path` 必須傳 `Path` 物件，不能傳字串。

### AFM Core Advanced 模型選擇

❌ **無 API 可選**。SDK 只暴露兩個 UseCase：`GENERAL` / `CONTENT_TAGGING`，無法指定用哪個底層模型。系統自動決定。

### Streaming

✅ **可用**，但 chunk 格式為**累積全文**（非 delta 增量）：

```python
async for chunk in session.stream_response("prompt"):
    print(chunk)  # chunk = 從頭到此的完整文字，非新增部分
```

- 首字延遲：~1.77s
- 總耗時：~2.92s（短文）
- server.py 實作 Ollama streaming 需自行計算 delta：`chunk[len(prev_chunk):]`

### 紅丸任務可行性評估

AFM 20B 能否取代 Claude 生成 IG Caption：

| 指標 | AFM 20B | 要求 |
|------|---------|------|
| 字數 | ~892 字 | ≥1000 字 |
| 耗時 | 14.5s | — |
| 財經深度 | 中等 | 高（非共識視角）|

**結論：無法取代紅丸。** 字數差一截、財經分析深度不足。適合短輸出任務（hashtag、審圖、分類）。

---

### [Model D · AFM Core Advanced 20B MoE · localhost:11436] 2026-06-11 能力對比測試

> **執行方式：** `POST localhost:11436/api/generate`
> 腳本：`~/Desktop/test_model_d.py`
> 目的：與 Model A/B/C 同題對比，確認 20B MoE 是否實質優於 3B

| # | 測項 | 結果 | 字數 | 耗時 |
|---|------|------|------|------|
| D01 | 紅丸完整 Caption（900–1500字）| ❌ | 371 | 6.25s |
| D02 | 非共識角度摘要（100字內）| ⚠️ 有分析感但仍淺 | 82 | 1.12s |
| D03 | 精確 50 字 | ⚠️ 模型在輸出末尾附加「50字」標記，實際超出 | 72 | 1.01s |
| D04 | 6 條規則同時施加 | ❌ 標題 9 字（要求 10）、hashtag 缺 `#` 前綴 | 118 | 1.35s |
| D05 | 財經 JSON Structured Output | ✅ 正確 JSON，有 ```json``` 包裹 | 114 | 0.96s |
| D06 | Tool Calling 規劃 | ✅ 正確列出兩個工具呼叫 | 34 | 0.35s |
| D07 | 1500字 → 恰好 20字 | ⚠️ 輸出 25 字 | 25 | 0.48s |
| D08 | 完整 IG Pipeline | ⚠️ 格式大致對，內文僅 18 字，hashtag 有空格 | 90 | 0.95s |

#### 關鍵發現：輸出長度是系統層 cap，非模型能力問題

| 模型 | 紅丸 Caption 實測字數 | 模型參數量 |
|------|----------------------|-----------|
| Model A（3B）| ~400 字 | 3B |
| Model B（3B HTTP）| ~400 字 | 3B |
| Model C（PCC Cloud）| ~350 字 | 未知（雲端）|
| Model D（20B MoE）| ~371 字 | 20B |

**20B MoE 比 3B 大 6 倍，輸出長度反而沒有增加。** Apple 在系統層對所有路徑施加了輸出長度限制，這是架構設計而非模型能力瓶頸。

---

## 四路徑能力總表（2026-06-11 完整版）

> 執行方式對應：A = `apple-fm-sdk` Python API、B = `localhost:11436` HTTP、C = `shortcuts run "Apple Intelligence"`、D = `localhost:11436`（0.2.0）

| 能力 | A（3B SDK）| B（3B HTTP）| C（PCC Shortcuts）| D（20B SDK）|
|------|:---------:|:----------:|:----------------:|:-----------:|
| 短文生成（<500字）| ✅ | ✅ | ✅ | ✅ |
| 長文生成（1000字+）| ❌ | ❌ | ❌ | ❌ |
| 財經 Structured Output | ✅ | ✅ | ⚠️ 不可靠 | ✅ |
| ImageAttachment 審圖 | ❌（v0.1.1）| — | — | ✅（v0.2.0）|
| 精確字數控制 | ❌ | ❌ | ❌ | ❌ |
| 複雜多規則（>4條）| ❌ | ❌ | ❌ | ❌ |
| Tool Calling | ✅ | — | — | ✅ |
| Streaming | ✅（累積輸出）| ✅（需算 delta）| — | ✅ |
| 速度（典型任務）| 0.22–2s | 0.35–1s | 1.5–5s | 0.35–1.2s |
| **替代紅丸**（IG Caption）| ❌ | ❌ | ❌ | ❌ |

**最終結論：四條路徑均無法替代紅丸。長文生成是所有 Apple AI 路徑的共同硬限制，原因是系統層輸出 cap 而非模型能力不足。短輸出任務（hashtag、摘要、分類、審圖）推薦 Model D（最快且財經 Structured Output 穩定）。**
