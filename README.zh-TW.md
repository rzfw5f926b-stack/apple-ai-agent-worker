# apple-ai-agent-worker

**Apple 內建的免費模型，可以幫你的主 AI agent 分擔哪些工作？**

有 Apple Intelligence 的 Mac 都內建裝置端模型；macOS 27 起，捷徑也能呼叫 Apple 的 Private Cloud Compute（PCC）雲端模型。每次呼叫都不用錢。這個 repo 是把它們當成主 agent（Claude、GPT 等）的 *sub-worker* 的實測報告：哪些工作交給它很穩、哪些會錯、怎麼從程式呼叫、怎麼檢查它的答案。

[English](README.md)

> 2026 年 10 月在 macOS 27.0.1、Apple Silicon 上實測。Apple 會隨系統更新模型，更新後請重跑 [`bench/`](bench/)。

## 結論：哪些可以交出去

| ✅ 交給它 | ⚠️ 交給它，但要驗證 | ❌ 留給主 agent |
|---|---|---|
| 大量摘要、改寫、翻譯 | 算術、百分比、日期——用程式重算 | 多步推理、規劃 |
| 清單分類、打標籤（JSON 標籤） | 圖片 OCR——數字要抽查 | 分數和精確計算（PCC 算 3/8 + 5/12 = 1.0417） |
| 抽欄位成 JSON（財經文字也可以） | 翻譯——偏字面 | 精確字數（「剛好 100 字」） |
| 長文裡找某個事實（約 3.2 萬 tok 以內） | 可能被 guardrail 擋的內容——重試一次 | 長篇寫作（輸出上限約 350–450 個中文字） |
| 短文草稿、標題、hashtag | | 需要整體判斷、仿寫風格、同時超過 4 條規則 |
| QR code、條碼解碼（裝置端） | | 單一個小問題（自己答比較快） |

最划算的用法：讓 Apple 模型先**壓縮原始資料**（摘要、抽出的欄位、標籤），主 agent 只拿處理過的小結果。

## 選後端

| 後端 | 呼叫方式 | 速度 | 限制 | 用途 |
|---|---|---|---|---|
| **Cloud**（PCC） | `shortcuts run` + 捷徑 | 約 0.8–1.6 s，同時 4 個也差不多 | 每日用量上限（沒公開數字）；輸入約 3.2 萬 tok | **預設。** 整體最強，整數運算和日期都對 |
| **Cloud Pro**（PCC） | `shortcuts run` + 捷徑 | 差不多 | 連跑約 47 次就撞到用量上限 | Cloud 失敗時的備援 |
| **裝置端**（`fm` CLI） | `/usr/bin/fm respond` | 短答約 0.2 s | context 8192 tok（含輸出） | 保證 JSON 格式（`--schema`）、看圖、QR／條碼、離線或私密資料 |
| 裝置端（SDK／HTTP） | `apple-fm-sdk`、[`server.py`](docs/server.md) | 跟 `fm` 差不多 | 同上 | 工具需要 Ollama／OpenAI 相容 API 時 |

雲端模型**不能**從 `fm` 呼叫，只能透過捷徑。Apple 官方說兩個雲端模型都有[每日用量上限](https://support.apple.com/zh-tw/127901)，但沒給數字，所以批次工作一定要能退回裝置端。

## 準備

需求：macOS 27 以上、Apple Silicon、已開啟 Apple Intelligence；雲端模型要有網路。

**1. 自己建兩個捷徑。** 雲端模型沒有自己的指令列工具，要從程式呼叫，唯一的方法是自己在「捷徑」app 建一個捷徑，再用 `shortcuts run "<捷徑名稱>"` 執行它。這個 repo 的範例和腳本都假設捷徑叫下面這兩個名字：

| 捷徑名稱 | 「使用模型」動作選的模型 |
|---|---|
| `Ask Apple Cloud` | Private Cloud Compute |
| `Ask Apple Cloud Pro` | Cloud Pro |

在「捷徑」app 新增一個捷徑，命名為 **Ask Apple Cloud**，放三個動作：

1. **接收**文字輸入（讓 `shortcuts run -i` 能把 prompt 傳進去）
2. **使用模型**——模型選 **Private Cloud Compute**；要求填「捷徑輸入」
3. **停止並輸出**模型的回應

接著複製一份，改名為 **Ask Apple Cloud Pro**，模型改選 **Cloud Pro**。用 `shortcuts list | grep "Ask Apple"` 確認兩個都在。（動作名稱可能因系統語言略有不同。想用別的名字也可以，執行腳本時用 `SHORTCUTS_CHAIN`／`SC` 傳進去。）

**2. 確認裝置端模型：** `fm available` 應該回報 `System model available`。

## 從 agent 呼叫

```bash
# 雲端：prompt 寫成檔案。-o 的檔名一定要 .txt 結尾。
printf '%s' "$PROMPT" > in.txt
shortcuts run "Ask Apple Cloud" -i in.txt -o out.txt && cat out.txt

# 裝置端
fm respond --no-stream '分類這則標題：...'
cat article.txt | fm respond --no-stream -i '用一句話摘要'
fm respond --no-stream -g --schema label.json '分類：...'               # 輸出保證符合 schema
fm respond --no-stream --image qr.png --tool barcode --text 'QR code 內容是什麼？'
```

[`examples/delegate.sh`](examples/delegate.sh) 把上面包好了錯誤處理：依序試 Cloud、Cloud Pro，都失敗就改用 `fm`，並在 stderr 告訴你是哪個後端回答的。

```bash
examples/delegate.sh "用一句話摘要：..."
cat notes.txt | SHORTCUTS_CHAIN="我的捷徑" examples/delegate.sh
```

小技巧：

- 每次 `shortcuts run` 都是獨立的，不記得前文；多輪就把前面的對話一起放進 prompt。
- 要它「最後一行只寫答案」，程式比較好擷取。
- 雲端最多同時跑 4 個（例如 thread pool），每個用自己的輸入、輸出檔。
- 大批次之前先跑 1 筆，確認還沒撞到用量上限。

## 驗證答案

- **成功** = 結束碼 0、輸出檔存在、內容非空。空白 prompt 會得到結束碼 0 加空輸出。
- **失敗** = 結束碼 1、訊息在 stderr、不產生輸出檔。會看到三種訊息（依系統語言顯示）：

  | stderr（繁中系統） | 意思 | 怎麼辦 |
  |---|---|---|
  | `模型無法為此要求提供回應…` | guardrail 擋下（無害的 prompt 也會） | 重試或換說法，再不行改用 `fm` |
  | `已達到此模型的使用上限…` | 用量上限 | 換後端（Cloud ↔ Cloud Pro ↔ `fm`） |
  | `要求超出允許的最大長度。` | 輸入太長（超過約 3.2 萬 tok） | 切段 |

- 數字和日期一律用程式重算；分數絕對不要信。
- 分類、抽取抽幾筆跟原文比對。

## 踩過的坑

- `shortcuts run -o out.out`（檔名不是 `.txt` 結尾）結束碼是 0，但**檔案根本沒寫出來**。
- 不加 `-o` 的話，stdout 拿到的是 RTF，不是純文字。
- 兩個雲端模型被問是誰，都只回「Apple 開發的基礎模型」，從輸出分不出是哪個。
- 裝置端 `fm` 的 `--model` 只有 `system` 一個選項，實際跑哪個裝置端模型由系統決定。

## 實測結果（2026-10-24）

22 題，每題 3 輪（長文題 1 輪）。腳本和原始輸出：[`bench/`](bench/)。

| 類別 | Cloud | Cloud Pro | 裝置端 `fm` | 備註 |
|---|---|---|---|---|
| 整數、百分比、複利 | 15/15 | 12/15 | 6/15 | Cloud Pro 把 984.9 自己四捨五入成 985；`fm` 答 1234 + 5678 = 7912 |
| 分數（3/8 + 5/12） | 0/3 | 3/3 | 0/3 | Cloud 穩定答 1.0417（正解 0.7917） |
| 星期、天數、閏年、時區 | 12/12 | 12/12 | 0/12 | |
| 禁止詞 | 6/6 | 6/6 | 6/6 | |
| 精確字數（100、50 字） | 4/6 | 4/6 | 0/6 | |
| 純 prompt 要求 JSON 分類（無 schema） | 6/6 | 6/6 | 6/6 | |
| 只用繁體字（不混簡體） | 3/3 | 1/1 | 3/3 | Cloud Pro 從這題起撞到用量上限 |
| prompt 含「內部資訊」字樣 | 3/3 | — | 3/3 | |
| 簡單邏輯 | 5/6 | — | 6/6 | Cloud 有 1 次被 guardrail 誤擋 |
| 長文找資訊 9k／18k／4.5 萬字 | 1/1 · 1/1 · 1/1 | — | 1/1 · 0/1 · — | 4.5 萬字花 15 s；`fm` 在 18k 字超出 context |
| **合計** | **56/62** | **44/46** | **31/62** | |

更早的裝置端測試（2026 年 9 月，`fm` CLI）：

| ✅ 放心用 | ⚠️ 要覆核 | ❌ 不要用 |
|---|---|---|
| 分類（schema enum）30/30（自由文字 27/30） | 字數控制（目標的 0.87–1.2 倍） | 算術、日期、星期、時區 |
| 結構化抽取 9/9；財經抽取 18/18 | OCR（`--tool ocr`）——數字要覆核 | 不開 `--tool` 就問圖片內容（會編造） |
| 人名、地點、時間 15/15 | 多輪對話記憶 | 多個 tool 串接 |
| 繁中摘要、改寫 15/15 | 寫小說（常半途改口） | 超過約 7.5k tok 的輸入 |
| 7k tok 內長文找資訊 54/54 | 投資問題（會加免責或拒答） | |
| QR、條碼 3/3；常識 23/24 | 翻譯（偏字面，偶有大陸用詞） | |

## 其他

- [`docs/server.md`](docs/server.md)——`server.py`：把裝置端模型包成 Ollama／OpenAI 相容 HTTP 服務；也有 2026 年 6 月的 SDK 測試結果（20B MoE 速度、看圖、串流）。
- [`docs/research-log.zh-TW.md`](docs/research-log.zh-TW.md)——2026 年 6 月到 10 月依時間順序的完整研究紀錄。後面的測試會更正前面的結論。
- [`experiments/`](experiments/)——早期探測捷徑內建 AI 動作的腳本。

## 授權

MIT
