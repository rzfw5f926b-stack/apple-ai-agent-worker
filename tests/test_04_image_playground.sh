#!/bin/bash
# test_04_image_playground.sh
# 解鎖 Mac 後測試 Image Playground
# 確認：1) 新風格種類  2) 寫實風品質  3) 鎖屏修復後能否跑通

OUTDIR=/tmp/ip_style_tests
mkdir -p "$OUTDIR"

run_test() {
    local name="$1"
    local prompt="$2"
    local outfile="$OUTDIR/${name}.png"

    echo "------"
    echo "[${name}]"
    echo "Prompt: $prompt"
    START=$(date +%s%3N)
    RESULT=$(echo "$prompt" | shortcuts run "IG Image Generate" --output-path "$outfile" 2>&1)
    END=$(date +%s%3N)
    ELAPSED=$(( END - START ))
    echo "Exit: $? | Time: ${ELAPSED}ms"
    if [ -n "$RESULT" ]; then echo "Output: $RESULT"; fi
    if [ -f "$outfile" ]; then
        SIZE=$(wc -c < "$outfile")
        echo "File: $outfile (${SIZE} bytes) ✅"
    else
        echo "File: NOT created ❌"
    fi
    echo ""
}

echo "=============================="
echo "Image Playground 風格測試"
echo "Mac 必須解鎖才能跑"
echo "=============================="
echo ""

# ---- 基本確認：原本可用的 prompt ----
run_test "baseline_vault" \
    "A golden vault door, dramatic cinematic lighting, deep black background, no text"

# ---- 新風格測試：寫實/照片風 ----
run_test "realistic_hammer" \
    "A photorealistic iron hammer striking a metallic surface, sparks flying, studio lighting, no text"

run_test "realistic_chart" \
    "A photorealistic stock chart on a trading screen, dramatic lighting, dark background, no text"

# ---- 風格關鍵字測試 ----
run_test "style_cinematic" \
    "A compass on dark surface, cinematic photography style, dramatic shadows, no text"

run_test "style_3d_render" \
    "A gold coin stack, 3D render, photorealistic, deep black background, no text"

run_test "style_watercolor" \
    "A balance scale with coins, watercolor painting style, soft colors, no text"

# ---- 封鎖詞確認：macOS 27 有沒有鬆動 ----
run_test "block_test_panic" \
    "A market panic scene, red arrows falling, dramatic lighting, no text"

run_test "block_test_nvidia" \
    "A nvidia chip glowing, dramatic lighting, dark background, no text"

run_test "block_test_crisis" \
    "A financial crisis vortex, spinning coins, dark background, no text"

echo "=============================="
echo "全部測試完成"
echo "輸出圖片存於: $OUTDIR"
ls -la "$OUTDIR"
echo ""
echo "用 Quick Look 看結果："
echo "  qlmanage -p $OUTDIR/*.png"
echo "=============================="
