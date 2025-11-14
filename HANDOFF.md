# Claude Code 交接說明

**日期**: 2025-11-14
**專案**: FSC 金管會裁罰案件爬蟲與 RAG 系統

## 當前狀態總覽

### ✅ 已完成

1. **裁罰案件爬蟲** (495 筆)
   - 爬取程式: `src/crawlers/penalties.py`
   - 資料位置: `data/penalties/raw.jsonl` (22 MB，不在 Git)
   - 格式化器: `src/processor/penalty_markdown_formatter.py`

2. **Gemini File Search Store 上傳**
   - Store ID: `fileSearchStores/fscpenalties-ma1326u8ck77`
   - 上傳狀態: **493/495 成功** (99.6%)
   - 失敗案件: 2 筆（Gemini API 503 錯誤）

3. **前端部署**
   - 專案: `FSC-Penalties-Deploy` (Streamlit)
   - 部署平台: Streamlit Cloud
   - 功能: RAG 查詢、模型選擇、來源篩選

### ⚠️ 發現的問題與修正

#### 問題：爬蟲誤抓通用附件

**症狀**：494/495 筆案件都包含兩個不相關的附件
- 失智者經濟安全保障推動計畫 (365 KB)
- 金管會永續發展目標自願檢視報告 (2.99 MB)

**根本原因**：
爬蟲從整個頁面抓取所有 `<a>` 標籤，包括側邊欄/頁尾的通用連結。

**驗證方法**：
```bash
python scripts/verify_penalty_html_structure.py
```

驗證結果確認：
- ✅ 內容選擇器 `div.zbox` 正確
- ❌ 附件都在內容區域外（側邊欄/頁尾）
- ✅ 內容區域內實際沒有附件

**已修正**：
1. `src/crawlers/penalties.py` (第 188-237 行)
   - 只從內容區域 (`content_div`) 抓取附件
   - 新增關鍵字過濾清單

2. `src/processor/penalty_markdown_formatter.py` (第 186-237 行)
   - 在生成 Markdown 時也過濾這些附件
   - 雙重保險

### 📊 上傳失敗分析

**失敗案件**：
1. `fsc_pen_20250731_0003` - 三商美邦人壽（資本適足率案件）
2. `fsc_pen_20201126_0134` - 玉山商業銀行（理專挪用案件）

**錯誤訊息**：
```
503 UNAVAILABLE - Failed to count tokens
```

**已嘗試的解決方案**：
- ✅ 移除無關附件 → 仍失敗
- ✅ 增加重試次數 (5 次) → 仍失敗
- ✅ 增加延遲時間 → 仍失敗

**結論**：
可能是這兩筆案件的內容觸發 Gemini API 的限制或 bug。建議接受 99.6% 的成功率。

## 下一步建議

### 選項 A: 重新爬取並上傳（推薦）

在新電腦上執行：

```bash
# 1. Clone 並設定環境
git clone <your-repo>
cd FSC
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 設定 API Key
cp .env.example .env
# 編輯 .env，填入 GEMINI_API_KEY

# 3. 重新爬取（使用修正後的爬蟲，約 15 分鐘）
python scripts/crawl_all_penalties.py

# 4. 刪除舊 Store
python scripts/delete_gemini_store.py --store-id fileSearchStores/fscpenalties-ma1326u8ck77

# 5. 重新上傳全部（預期 495/495 全部成功）
python scripts/upload_to_gemini.py --type penalties
```

**優點**：
- 乾淨的資料（無誤抓附件）
- 可能解決那 2 筆失敗問題
- 提升查詢品質

### 選項 B: 保持現狀

接受 493/495 (99.6%) 的結果，標記為已知限制。

## 重要檔案清單

### 資料檔案（不在 Git）
- `data/penalties/raw.jsonl` - 原始爬取資料 (22 MB)
- `data/temp_markdown/penalties/*.md` - 生成的 Markdown 檔案
- `logs/*.log` - 執行日誌

### 程式碼（已在 Git）
- `src/crawlers/penalties.py` - 裁罰爬蟲（✅ 已修正附件問題）
- `src/processor/penalty_markdown_formatter.py` - Markdown 格式化器（✅ 已修正）
- `src/uploader/gemini_uploader.py` - Gemini 上傳器
- `scripts/crawl_all_penalties.py` - 完整爬取腳本
- `scripts/upload_to_gemini.py` - 上傳腳本
- `scripts/retry_failed_uploads.py` - 重試失敗案件
- `scripts/verify_penalty_html_structure.py` - HTML 結構驗證工具

### 文檔
- `docs/implementation_summary.md` - 實作總結
- `docs/multi_store_query_architecture.md` - 多 Store 查詢架構
- `CLAUDE.md` - Claude Code 專案指引

## 環境變數

需要在 `.env` 設定：
```
GEMINI_API_KEY=your_api_key_here
```

## Store 資訊

```
Store ID: fileSearchStores/fscpenalties-ma1326u8ck77
Store Name: fsc-penalties
文件數: 493 個 Markdown 檔案
狀態: 運行中（含誤抓附件，建議重建）
```

## 待辦事項

1. ⏳ **重新爬取並上傳**（使用修正後的爬蟲）
2. ⏳ **生成檔名映射** (`file_id -> 顯示名稱`)
3. ⏳ **測試線上查詢功能**
4. ⏳ **整合 FSC-Penalties-Deploy 前端**

## 聯絡資訊

- Gemini API Key 位置: `.env` 檔案
- 前端部署: Streamlit Cloud
- Store 管理: 透過 Gemini API

---

**最後更新**: 2025-11-14
**下次繼續**: 在新電腦上重新爬取並上傳乾淨資料
