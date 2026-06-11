#!/bin/bash
# test_03_ai_actions.sh
# 測試 Shortcuts 呼叫 Apple Intelligence
# 核心問題：有沒有可以傳自訂 prompt 的 Action？

OUTDIR=/tmp/ai_action_tests
mkdir -p "$OUTDIR"

TEST_TEXT="The Federal Reserve raised interest rates by 25 basis points today, surprising markets. The decision was unanimous among committee members, signaling a hawkish shift in monetary policy. Treasury yields rose sharply following the announcement."

echo "測試文字："
echo "$TEST_TEXT"
echo ""

# ---- 測試 1：Summarize（系統內建 AI Action）----
echo "=============================="
echo "[Test 1] Summarize Text"
echo "=============================="
RESULT=$(echo "$TEST_TEXT" | shortcuts run "Summarize" --output-path "$OUTDIR/summarize_out.txt" 2>&1)
echo "Exit code: $?"
echo "stdout: $RESULT"
if [ -f "$OUTDIR/summarize_out.txt" ]; then
    echo "output file:"
    cat "$OUTDIR/summarize_out.txt"
fi

echo ""

# ---- 測試 2：Rewrite ----
echo "=============================="
echo "[Test 2] Rewrite"
echo "=============================="
RESULT=$(echo "$TEST_TEXT" | shortcuts run "Rewrite" --output-path "$OUTDIR/rewrite_out.txt" 2>&1)
echo "Exit code: $?"
echo "stdout: $RESULT"
if [ -f "$OUTDIR/rewrite_out.txt" ]; then
    cat "$OUTDIR/rewrite_out.txt"
fi

echo ""

# ---- 測試 3：Make Key Points ----
echo "=============================="
echo "[Test 3] Make Key Points"
echo "=============================="
RESULT=$(echo "$TEST_TEXT" | shortcuts run "Make Key Points" --output-path "$OUTDIR/keypoints_out.txt" 2>&1)
echo "Exit code: $?"
echo "stdout: $RESULT"
if [ -f "$OUTDIR/keypoints_out.txt" ]; then
    cat "$OUTDIR/keypoints_out.txt"
fi

echo ""

# ---- 測試 4：嘗試財經分析自訂 prompt（如果有相關捷徑）----
echo "=============================="
echo "[Test 4] Apple Intelligence（如果有自訂 prompt 捷徑）"
echo "=============================="
CUSTOM_PROMPT="你是一位投資分析師。請分析以下新聞對台灣股市的影響，給出非共識觀點：$TEST_TEXT"
RESULT=$(echo "$CUSTOM_PROMPT" | shortcuts run "Apple Intelligence" --output-path "$OUTDIR/custom_out.txt" 2>&1)
echo "Exit code: $?"
echo "stdout: $RESULT"
if [ -f "$OUTDIR/custom_out.txt" ]; then
    cat "$OUTDIR/custom_out.txt"
fi

echo ""

# ---- 測試 5：「人工智慧」捷徑（Apple Intelligence 自訂 prompt？）----
echo "=============================="
echo "[Test 5] 人工智慧 shortcut"
echo "=============================="
RESULT=$(echo "$TEST_TEXT" | shortcuts run "人工智慧" --output-path "$OUTDIR/ai_out.txt" 2>&1)
echo "Exit code: $?"
echo "stdout: $RESULT"
if [ -f "$OUTDIR/ai_out.txt" ]; then
    echo "output file:"
    cat "$OUTDIR/ai_out.txt"
fi

echo ""

# ---- 測試 6：「Safari 搜尋 API」—— Apple Intelligence 建立的捷徑 ----
echo "=============================="
echo "[Test 6] Safari 搜尋 API（AI 建立）"
echo "=============================="
RESULT=$(echo "Fed rate hike 2026 impact on Taiwan stocks" | shortcuts run "Safari 搜尋 API" --output-path "$OUTDIR/safari_api_out.txt" 2>&1)
echo "Exit code: $?"
echo "stdout: $RESULT"
if [ -f "$OUTDIR/safari_api_out.txt" ]; then
    echo "output file:"
    cat "$OUTDIR/safari_api_out.txt"
fi

echo ""
echo "=============================="
echo "測試完成，輸出存於 $OUTDIR"
ls -la "$OUTDIR"
echo "=============================="
