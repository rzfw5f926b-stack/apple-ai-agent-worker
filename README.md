# Apple Foundation Models SDK — 能力研究專案

**建立日期：2026-06-07**
**目標：** 測試 Apple on-device AI 的能力邊界，評估能否作為 Ai Agent 的低成本 sub-worker

---

## 安裝紀錄

### 需求
- macOS 26 (Tahoe) — Darwin 25.x
- Apple Silicon (M1+)
- Apple Intelligence 啟用
- Python 3.10+
- Command Line Tools（不需要完整 Xcode）

### 安裝方式（繞過 Xcode check）

官方 `pip install apple-fm-sdk` 需要完整 Xcode，但實際只需要 Swift CLT。
繞過方式：clone repo，修改 `build_backend.py` 的兩個 check，再從本地安裝。

```bash
git clone https://github.com/apple/python-apple-fm-sdk.git /tmp/python-apple-fm-sdk
# 修改 build_backend.py：註解掉 CommandLineTools check 和 xcodebuild check
pip3 install /tmp/python-apple-fm-sdk --break-system-packages
```

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
    await s.respond("我叫 username。")
    await s.respond("我喜歡藍色。")
    r = await s.respond("列出你知道關於我的事。")
    # ✅ 正確列出：username + 藍色
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

## 2026-06-07 測試結果

### 模型基本資訊

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

## 2026-06-07 補測：Generation Guides、CONTENT_TAGGING、Tool Calling

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

模型可在生成過程中呼叫 Python async 函數（類似 Ai Agent function calling，完全 on-device）。

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

## 2026-06-07 補測：GenerationOptions、SamplingMode、Session 歷史

### Session 多輪記憶修正

**先前評估「0/5」是錯誤的**。同一個 `LanguageModelSession` 物件連續 `respond()` 有完整多輪記憶（姓名、顏色、數字累加全通過）。失效的原因是 one-liner pattern 每次都 `new session()`，不是模型問題。

```python
s = fm.LanguageModelSession()         # 建立一次
await s.respond("我叫 username。")
await s.respond("我喜歡藍色。")
r = await s.respond("列出你知道的事。")  # ✅ username + 藍色都記得
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

- [ ] 純文字財經 + 自行 parse 的實際可行性
- [ ] Streaming 在長文生成的表現
- [ ] WWDC 2026-06-09 後重測：新功能、bug 修復、翻譯 bug
- [x] ~~多輪記憶問題~~ → 修正：同 session 物件有記憶，one-liner 每次 new session 才失效
- [x] ~~contentTagging use case~~ → 不建議用（Apple 內部系統用）
- [x] ~~json_schema 參數~~ → GenerationError 255，不可用
- [x] ~~RANDOM seed~~ → seed 參數無效
