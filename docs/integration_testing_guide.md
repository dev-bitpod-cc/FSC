# 整合測試指南

## 概述

本文檔說明如何執行完整的整合測試，驗證金管會爬蟲專案的所有核心功能。

## 測試腳本

### `test_integration_full.py` - 完整整合測試

**測試項目**：
1. ✅ 建立測試用 File Search Stores（公告 + 裁罰）
2. ✅ 上傳測試資料（含時效性標註）
3. ✅ 單一 Store 查詢測試
4. ✅ 多 Store 查詢測試
5. ✅ 時效性標註驗證
6. ✅ 參考文件數量控制

## 前置準備

### 1. 設定環境變數

確保 `.env` 中已設定 Gemini API Key：

```bash
GEMINI_API_KEY=your_api_key_here
```

### 2. 準備測試資料

執行以下腳本產生測試資料：

```bash
# 產生時效性標註測試資料
python scripts/test_temporal_annotation.py

# 產生裁罰案件測試資料（如果尚未執行）
python scripts/test_penalty_crawler.py

# 產生裁罰 Markdown
python scripts/test_penalty_individual_files.py
```

## 執行測試

### 基本執行

```bash
# 執行完整整合測試（保留測試 Stores）
python scripts/test_integration_full.py
```

### 執行後自動清理

```bash
# 執行測試並在完成後刪除測試 Stores
python scripts/test_integration_full.py --cleanup
```

## 測試流程說明

### 步驟 1: 建立測試 Stores

建立兩個獨立的測試 Stores：
- `fsc-integration-test-announcements` (公告測試)
- `fsc-integration-test-penalties` (裁罰測試)

如果 Stores 已存在，會重複使用。

### 步驟 2: 上傳測試資料

**公告資料**：
- 使用 `data/markdown/temporal_test/` 中的檔案
- 包含時效性標註（⭐ 最新版本 / ⚠️ 已過時）
- 包含修正歷程資訊
- 上傳前 3 個檔案

**裁罰資料**：
- 使用 `data/markdown/penalties_individual/` 中的檔案
- 包含完整的 metadata（處分金額、法條依據等）
- 上傳前 2 個檔案

如果測試資料目錄不存在，會自動建立簡化的測試檔案。

### 步驟 3: 單一 Store 查詢測試

**測試 3.1 - 只查詢公告**：
```python
fileSearchStoreNames = ['fsc-integration-test-announcements']
```
驗證能否正確查詢單一 Store。

**測試 3.2 - 只查詢裁罰**：
```python
fileSearchStoreNames = ['fsc-integration-test-penalties']
```
驗證裁罰案件 Store 查詢功能。

### 步驟 4: 多 Store 查詢測試 ⭐

**關鍵測試**：
```python
fileSearchStoreNames = [
    'fsc-integration-test-announcements',
    'fsc-integration-test-penalties'
]
```

驗證 Gemini File Search API 是否支援同時查詢多個 Stores。

**預期結果**：
- ✅ API 支援多 Store 查詢
- ✅ 能夠同時檢索公告和裁罰資料
- ✅ 查詢結果包含兩種資料類型

### 步驟 5: 時效性標註驗證

**System Instruction**：
```
【重要】時效性規則：
1. 優先使用標註「⭐ 最新版本」的文件
2. 如果檢索到多個相關公告，比較發文日期，使用最新的
3. 明確告知使用者你引用的是哪個日期的規定
4. 如果文件標註「⚠️ 此版本已過時」，提醒使用者這是過時版本
```

**測試查詢**：
```
保險業內部控制辦法的最新規定是什麼？請告訴我你引用的版本日期。
```

**預期結果**：
- ✅ 模型識別並使用最新版本文件
- ✅ 回應中提到版本日期
- ✅ 不使用過時版本

### 步驟 6: 參考文件數量控制

**System Instruction**：
```
請只列出前 3 個最相關的結果。
每個結果都要簡短說明。
```

**測試查詢**：
```
列出所有可用的文件
```

**預期結果**：
- ✅ 回應限制在前 3 個結果
- ✅ Prompt Engineering 方式可以控制數量

## 測試結果解讀

### 成功標準

所有以下測試都應該通過：

- ✓ 單一 Store 查詢（公告）
- ✓ 單一 Store 查詢（裁罰）
- ✓ 多 Store 查詢
- ✓ 時效性標註識別
- ✓ 參考文件數量控制

### 失敗處理

如果某項測試失敗：

1. **多 Store 查詢失敗**：
   - 檢查 API 版本是否支援多 Store
   - 考慮使用替代方案（單一 Store + Metadata 過濾）

2. **時效性標註無效**：
   - 檢查 Markdown 標註是否正確
   - 調整 System Instruction
   - 嘗試更明確的 Prompt

3. **參考文件控制無效**：
   - Gemini API 可能不支援直接控制數量
   - 使用 Prompt Engineering 作為主要方案

## 清理測試環境

### 手動清理

如果測試時沒有使用 `--cleanup` 參數，可以手動清理：

```bash
# 使用清理腳本
python scripts/cleanup_test_stores.py
```

### 自動清理

在測試完成後自動清理：

```bash
python scripts/test_integration_full.py --cleanup
```

## 故障排除

### 問題 1: API Key 無效

**錯誤訊息**：
```
請在 .env 中設定 GEMINI_API_KEY
```

**解決方案**：
1. 檢查 `.env` 檔案是否存在
2. 確認 API Key 格式正確
3. 驗證 API Key 有效性

### 問題 2: 測試資料不存在

**錯誤訊息**：
```
公告測試目錄不存在: data/markdown/temporal_test
```

**解決方案**：
```bash
# 產生時效性測試資料
python scripts/test_temporal_annotation.py
```

### 問題 3: Store 建立失敗

**錯誤訊息**：
```
建立 Store 失敗: ...
```

**解決方案**：
1. 檢查 API Key 權限
2. 確認 Gemini API 配額
3. 檢查網路連線

### 問題 4: 檔案上傳失敗

**錯誤訊息**：
```
上傳失敗: ...
```

**解決方案**：
1. 檢查檔案大小（不超過限制）
2. 確認檔案格式正確（Markdown）
3. 檢查 API 配額

## 進階測試

### 測試特定功能

如果只想測試特定功能，可以使用其他測試腳本：

```bash
# 只測試多 Store API 支援
python scripts/test_multi_store_query.py

# 只測試時效性標註
python scripts/test_temporal_annotation.py

# 只測試上傳功能
python scripts/test_upload_markdown_generation.py
```

### 使用實際資料測試

如果想使用實際爬取的資料進行測試：

```bash
# 1. 爬取實際資料
python scripts/test_penalty_crawler.py  # 裁罰案件

# 2. 產生 Markdown（含時效性標註）
python scripts/upload_to_gemini.py --type announcements --markdown-only
python scripts/upload_to_gemini.py --type penalties --markdown-only

# 3. 修改測試腳本使用實際資料目錄
# 編輯 test_integration_full.py，指向實際資料目錄
```

## 測試報告

測試完成後，腳本會輸出完整的測試報告：

```
======================================================================
測試總結
======================================================================
✓✓✓ 所有測試通過！

測試結果:
  單一 Store 查詢: ✓
  多 Store 查詢: ✓
  時效性標註: ✓
  參考文件控制: ✓

======================================================================
整合測試完成！
======================================================================
```

## 下一步

測試通過後，可以進行：

1. **生產環境部署**：
   ```bash
   # 爬取完整資料
   python scripts/crawl_full_production.py

   # 上傳到正式 Stores
   python scripts/upload_to_gemini.py --type announcements
   python scripts/upload_to_gemini.py --type penalties
   ```

2. **建立查詢介面**：
   - 實作 Web API
   - 建立使用者介面
   - 整合 System Instructions

3. **監控與優化**：
   - 監控查詢品質
   - 收集使用者反饋
   - 持續優化 Prompts

## 參考資料

- **專案文檔**：
  - `docs/multi_store_query_architecture.md` - 多 Store 查詢架構
  - `docs/implementation_summary.md` - 實作總結
  - `docs/penalties_data_structure.md` - 裁罰資料結構

- **相關腳本**：
  - `scripts/upload_to_gemini.py` - 通用上傳腳本
  - `scripts/test_temporal_annotation.py` - 時效性標註測試
  - `scripts/cleanup_test_stores.py` - 清理測試環境
