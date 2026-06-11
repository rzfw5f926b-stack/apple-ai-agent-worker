# 2026-06-09 晚間測試清單

## 執行順序

1. `test_01_pipeline_log.sh` — 確認晚班 19:35 是否失敗
2. `test_02_shortcuts_inventory.sh` — 清查所有捷徑，找 Apple Intelligence Actions
3. `test_03_ai_actions.sh` — 測試 Shortcuts 呼叫 Apple Intelligence（有沒有自訂 prompt）
4. `test_04_image_playground.sh` — 解鎖後測試 Image Playground 新風格

## 關鍵問題（優先解答）

| 問題 | 腳本 | 影響 |
|------|------|------|
| 19:35 晚班失敗原因？ | test_01 | 確認鎖屏問題範圍 |
| Shortcuts 有沒有自訂 AI prompt？ | test_02/03 | 決定能否做免費 AI pipeline |
| Image Playground 新風格實際品質？ | test_04 | 決定要不要放棄 mmx |

## 手動測試項目（腳本無法自動化）

- System Settings > Lock Screen > Require password → 改 **Never**，再跑 test_04 確認鎖屏問題解決
- Shortcuts app 內建立一個 time-based automation，鎖屏時觀察能不能觸發
