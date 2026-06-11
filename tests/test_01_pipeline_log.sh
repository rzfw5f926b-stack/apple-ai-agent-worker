#!/bin/bash
# test_01_pipeline_log.sh
# 確認晚班 19:35 pipeline 是否因鎖屏失敗

PIPELINE_LOG=~/Documents/Claude/Projects/Instagram\ Auto-Post\ Pipeline/pipeline.log

echo "=============================="
echo "最後 50 行 pipeline.log"
echo "=============================="
tail -50 "$PIPELINE_LOG"

echo ""
echo "=============================="
echo "搜尋 19:3x 時段紀錄"
echo "=============================="
grep -n "19:3" "$PIPELINE_LOG" | tail -20

echo ""
echo "=============================="
echo "搜尋錯誤關鍵字"
echo "=============================="
grep -iE "error|fail|鎖|unlock|lock|捷徑|shortcut" "$PIPELINE_LOG" | tail -20
