#!/bin/bash
# test_02_shortcuts_inventory.sh
# 清查所有捷徑，重點找 Apple Intelligence 相關 Actions

echo "=============================="
echo "全部捷徑清單（含 UUID）"
echo "=============================="
shortcuts list --show-identifiers

echo ""
echo "=============================="
echo "Apple Intelligence 相關（關鍵字過濾）"
echo "=============================="
shortcuts list | grep -iE "intelligence|summarize|rewrite|writing|ai |apple ai|siri|prompt|generate|ask"

echo ""
echo "=============================="
echo "所有資料夾"
echo "=============================="
shortcuts list --folders

echo ""
echo "=============================="
echo "IG 相關捷徑"
echo "=============================="
shortcuts list | grep -i "IG\|image\|instagram"
