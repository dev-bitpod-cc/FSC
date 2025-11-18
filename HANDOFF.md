# Claude Code 交接說明

**日期**: 2025-11-18
**專案**: FSC 金管會裁罰案件爬蟲與 RAG 系統

## 當前狀態總覽 (2025-11-18)

### ✅ 已完成

1. **裁罰案件爬蟲** (495 筆)
   - 爬取程式: `src/crawlers/penalties.py`（✅ 已修正附件誤抓問題）
   - 資料位置: `data/penalties/raw.jsonl` (22 MB，不在 Git)
   - 格式化器: `src/processor/penalty_markdown_formatter.py`
   - 附件過濾率: 100%（0 筆誤抓）

2. **增強型映射檔生成** (495 筆)
   - 生成程式: `scripts/generate_file_mapping.py`
   - 映射檔位置: `data/penalties/file_mapping.json` (5.43 MB)
   - 包含內容:
     - 顯示名稱（日期_來源_機構）
     - 原始網頁連結 (100%)
     - 原始文字內容 (99.8%)
     - 適用法規 (86.7%，已優化)
     - 法規連結映射

3. **Gemini File Search Store**
   - 新 Store ID: `fileSearchStores/fscpenalties-tu709bvr1qti`
   - 上傳狀態: **進行中** (預計 492/495 成功)
   - 預期失敗: 3-4 筆（Gemini API 503 錯誤，已知限制）

4. **前端部署**
   - 專案: `FSC-Penalties-Deploy` (Streamlit)
   - 部署平台: Streamlit Cloud
   - 功能: RAG 查詢、模型選擇、來源篩選、映射檔整合
   - 最新提交:
     - `3c4dfce` - 整合映射檔，優化參考文件顯示
     - `c49d56a` - 優化映射檔法規提取邏輯

### ⚠️ 發現的問題與修正

#### 問題 1：爬蟲誤抓通用附件

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

#### 問題 2：法規提取重複和雜訊過多

**症狀**：映射檔中的適用法規欄位包含大量重複和雜訊
- 平均每案 6.8 條法規（實際核心違規通常只有 1-3 條）
- 最多 22 條法規（極端案例）
- 包含程序性法規（訴願法、行政執行法）
- 同一法條重複出現（不同前綴詞）

**問題範例**：
```json
"applicable_laws": [
  "依保險法第171條之1第4項",      // 裁罰依據
  "依據保險法第148條之3第1項",    // 違反法條
  "核有違反保險法第148條之3第1項", // 重複！
  "依訴願法第58條第1項",          // 程序性（救濟）
  "惟依訴願法第93條第1項",        // 程序性（救濟）
  "即依行政執行法第4條第1項"      // 程序性（執行）
]
```

**根本原因**：
1. 正則表達式提取所有法條，不區分違規法條和程序性法條
2. 未去除前綴詞（依、核、爰依等），導致相同法條被視為不同法條
3. 程序性法規（訴願法、行政執行法）是救濟和執行程序，不是違規內容

**優化策略**（已實作於 `scripts/generate_file_mapping.py`）：

1. **只提取核心違規法條**：
   ```python
   # 策略1: 優先提取明確標示違反的法條
   violation_patterns = [
       r'違反.*?([法名])第(\d+)條...',
       r'核.*?違反.*?([法名])第(\d+)條...',
   ]

   # 策略2: 如果沒找到違反相關的，才提取裁罰依據
   penalty_patterns = [
       r'依.*?([法名])第(\d+)條.*?(?:處|核處|罰鍰)',
       r'爰依.*?([法名])第(\d+)條...',
   ]
   ```

2. **過濾程序性法規**：
   ```python
   PROCEDURAL_LAWS = {
       '訴願法',           # 救濟程序
       '行政執行法',       # 執行程序
       '行政程序法',       # 行政程序
       '行政罰法',         # 行政罰則（通用規定）
   }
   ```

3. **移除前綴詞並去重**：
   ```python
   # 移除法名中的前綴詞
   law_name = re.sub(r'^(依|核|核已|核有|已|有|與|分別為|應依|爰依|按|惟|同)', '', law_name)

   # 過濾掉無效法名
   if law_name in ['法', '同法', '本法']:
       continue

   # 使用 set 自動去重
   laws = set()
   ```

**優化結果**：
- 平均法規數：**6.8 → 1.4** 條（↓79%）
- 最多法規數：**22 → 12** 條（↓45%）
- 中位數：**7 → 1** 條
- 法規分布：
  - 57% 的案例只有 1 條法規（281/495）
  - 77% 的案例≤ 2 條法規（379/495）

**優化前後對比範例**：

優化前（22 條）：
```
依保險法第171條之1第4項
依據保險法第148條之3第1項
核有違反保險法第148條之3第1項  // 重複
核已違反保險法第148條之3第1項  // 重複
依訴願法第58條第1項             // 程序性
惟依訴願法第93條第1項           // 程序性
即依行政執行法第4條第1項        // 程序性
...（共 22 條）
```

優化後（2 條）：
```
保險法第171條之1第4項    // 裁罰依據
保險法第148條之3第1項    // 違反法條（已去前綴、去重）
```

**注意事項**：

⚠️ **程序性法規的識別**
- 訴願法、行政執行法永遠不應該出現在違規法條清單中
- 這些是告訴受處分人如何救濟或執行的程序規定
- 如果看到這些法規，說明提取邏輯有問題

⚠️ **前綴詞的處理**
- 常見前綴：依、核、核已、核有、已、有、與、分別為、應依、爰依、按、惟、同
- 必須移除才能正確去重
- 移除後要檢查是否變成無效法名（如「法」、「同法」、「本法」）

⚠️ **違規法條 vs 裁罰依據**
- **違規法條**：被處罰人違反了什麼規定（如：銀行法第45條之1第1項）
- **裁罰依據**：依據哪條法律來處罰（如：銀行法第129條第7款）
- 通常一個案件有 1-2 條違規法條 + 1 條裁罰依據

⚠️ **特殊案例處理**
- 有些案件可能抓不到法規（0 條），這是正常的
  - 可能是文字格式特殊
  - 可能是簡化版公告
  - 保持 0 條，不要強制填充
- 證券投資信託及顧問法案件通常法規較多（7-12 條）
  - 這類案件確實涉及多條法規
  - 但仍應該去重和過濾程序性法規

**維護建議**：
- 如果未來發現新的程序性法規，加入黑名單
- 如果發現新的前綴詞模式，加入正則表達式
- 定期檢查法規數分布，確保符合預期（中位數應在 1-2 條）

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

**新 Store**（乾淨資料）：
```
Store ID: fileSearchStores/fscpenalties-tu709bvr1qti
Store Name: fsc-penalties
文件數: 預計 492 個 Markdown 檔案
狀態: 上傳中（100% 乾淨資料，無誤抓附件）
生成時間: 2025-11-14
```

**舊 Store**（已刪除）：
```
Store ID: fileSearchStores/fscpenalties-ma1326u8ck77
狀態: 已刪除（含誤抓附件）
```

## 待辦事項

1. ✅ **重新爬取並上傳**（使用修正後的爬蟲）
2. ✅ **生成檔名映射** (`file_id -> 顯示名稱，日期_來源_機構`)
3. ✅ **優化法規提取邏輯**（過濾程序性法規，去重）
4. ✅ **整合 FSC-Penalties-Deploy 前端**（映射檔已同步）
5. ⏳ **等待 Gemini 上傳完成**（預計 1.5 小時）
6. ⏳ **在 Streamlit Cloud 更新 Store ID**
7. ⏳ **測試線上查詢功能**

## 聯絡資訊

- Gemini API Key 位置: `.env` 檔案
- 前端部署: Streamlit Cloud
- Store 管理: 透過 Gemini API

---

## RAG 優化工作 (2025-11-18)

### 背景

前期工作比較了 FSC 和 Sanction 兩個專案對裁罰案件的處理方式：

- **FSC**: 爬取後結構化為 Markdown 上傳 → 查詢效果較差
- **Sanction**: 爬取後轉為優化 Plain Text 上傳 → 查詢效果較好

決定優化 FSC 專案，採用 Sanction 的 Plain Text 方式重新上傳。

### 已完成工作

1. **完整資料爬取** (630 筆，2004-2025)
   - 使用 FSC 裁罰爬蟲重新爬取全部資料
   - 包含網頁未顯示的歷史案件（5 筆）
   - 資料位置：`data/penalties/raw.jsonl`

2. **資料篩選** (490 筆，2012-01-01+)
   - 篩選 2012-01-01 之後的資料，對應 Sanction 的 490 筆
   - 腳本：`scripts/filter_penalties_2012.py`
   - 輸出：`data/penalties/filtered_2012.jsonl`

3. **優化 Plain Text 生成** (490 筆)
   - 參考 Sanction 的優化方式
   - 移除網頁雜訊，保留核心內容
   - 添加結構化欄位（發文日期、來源單位、罰款金額、發文字號）
   - 輸出目錄：`data/plaintext_optimized/penalties_individual/`
   - 檔案格式：`fsc_pen_YYYYMMDD_NNNN.txt`

4. **Store 清理**
   - 刪除所有測試用 Stores（9 個）
   - 保留 Deploy 專案使用的 Stores（2 個）：
     - `fileSearchStores/fscpenalties-tu709bvr1qti` (FSC-Penalties-Deploy)
     - `fileSearchStores/fscpenaltycases1762854180-9kooa996ag5a` (Sanction)

### 發現的問題

#### 問題：Upload Manifest 導致檔案缺失

**症狀**：
- 目錄中有 490 個檔案
- 上傳腳本只上傳 480 個
- 顯示「跳過已上傳」10 個檔案

**根本原因**：
- `GeminiUploader` 使用 `data/temp_uploads/upload_manifest.json` 記錄上傳狀態
- Manifest 保留了之前測試上傳的記錄
- 這 10 個檔案在測試中成功上傳到**已刪除的舊 Store**
- 新上傳任務載入 manifest 後誤以為已上傳，跳過這些檔案

**影響**：
- 新 Store 會缺少 10 個檔案（實際只有 480 個，應該有 490 個）
- 查詢時這 10 個案件無法被檢索到

**解決方案**：
```bash
# 清除 manifest
rm -f data/temp_uploads/upload_manifest.json

# 重新上傳全部 490 個檔案
python scripts/upload_optimized_to_gemini.py \
  --plaintext-dir data/plaintext_optimized/penalties_individual \
  --store-name fsc-penalties-plaintext \
  --delay 2.0
```

### 待完成工作

1. **刪除中斷的 Store**（換電腦前已中斷）
   ```bash
   # 中斷的 Store（只有 14/490 個檔案）
   # Store ID: fileSearchStores/fscpenaltiesplaintext-89kfbite755k

   python scripts/delete_stores_rest_api.py
   # 或使用 REST API 直接刪除：
   # DELETE https://generativelanguage.googleapis.com/v1beta/fileSearchStores/fscpenaltiesplaintext-89kfbite755k?force=true
   ```

2. **在新電腦重新上傳**（490 筆 Plain Text）
   ```bash
   # 1. 確保環境設定
   source venv/bin/activate

   # 2. 清除 manifest（重要！）
   rm -f data/temp_uploads/upload_manifest.json

   # 3. 上傳（使用穩定的 2 步驟方法，2.0 秒延遲）
   python scripts/upload_optimized_to_gemini.py \
     --plaintext-dir data/plaintext_optimized/penalties_individual \
     --store-name fsc-penalties-plaintext \
     --delay 2.0

   # 預計時間：約 80 分鐘（490 × 10 秒/檔案）
   # 預期成功率：99%+（參考之前 493/495 = 99.6%）
   ```

3. **驗證上傳完整性**
   ```bash
   python scripts/verify_gemini_upload.py \
     --store-id <new-store-id> \
     --local-dir data/plaintext_optimized/penalties_individual
   ```

4. **查詢效果測試**
   - 與 Sanction 專案比較查詢品質
   - 測試複雜查詢（多條件、時間範圍等）
   - 確認是否達到優化目標

### 重要提醒

⚠️ **Manifest 管理**
- 每次重新上傳前**必須**清除 `data/temp_uploads/upload_manifest.json`
- 否則會跳過之前成功的檔案，導致新 Store 資料不完整
- Manifest 機制是為斷點續傳設計，但跨 Store 時會造成問題

⚠️ **上傳方法**
- 使用 2 步驟方法：`upload_file()` + `import_file()`
- 不要使用新的 1 步驟 API（未經驗證，失敗率高）
- 延遲設定：2.0 秒/檔案（已驗證穩定）

⚠️ **Store ID 記錄**
- 上傳完成後記錄新 Store ID
- 更新前端專案配置
- 刪除舊的測試 Store

### 腳本清單

**資料準備**：
- `scripts/filter_penalties_2012.py` - 篩選 2012+ 資料
- `scripts/generate_optimized_plaintext.py` - 生成優化 Plain Text

**Store 管理**：
- `scripts/delete_stores_rest_api.py` - 使用 REST API 刪除 Stores
- `scripts/cleanup_unused_stores.py` - 清理未使用的 Stores

**上傳與驗證**：
- `scripts/upload_optimized_to_gemini.py` - 上傳 Plain Text
- `scripts/verify_gemini_upload.py` - 驗證上傳完整性

---

**最後更新**: 2025-11-18 18:30
**當前狀態**:
- ✅ 已爬取完整資料（630 筆）
- ✅ 已篩選 2012+ 資料（490 筆）
- ✅ 已生成優化 Plain Text（490 筆）
- ✅ 已清理測試 Stores（保留 2 個 Deploy 用）
- ✅ 已清除 upload manifest
- ⏳ **準備在新電腦重新上傳**

**下次繼續**:
1. 清除 `data/temp_uploads/upload_manifest.json`（已完成）
2. 上傳全部 490 個 Plain Text 檔案
3. 驗證上傳完整性（確保 490/490）
4. 測試查詢效果並與 Sanction 比較
