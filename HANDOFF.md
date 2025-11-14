# Claude Code 交接說明

**日期**: 2025-11-14
**專案**: FSC 金管會裁罰案件爬蟲與 RAG 系統

## 當前狀態總覽

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

**最後更新**: 2025-11-14 18:15
**當前狀態**:
- ✅ 已爬取乾淨資料（495 筆，0 誤抓附件）
- ✅ 已生成優化映射檔（法規去重，平均 1.4 條）
- ✅ 已整合前端（映射檔已同步到 FSC-Penalties-Deploy）
- ⏳ Gemini Store 上傳中（預計 18:45 完成）

**下次繼續**:
1. 在 Streamlit Cloud 更新 Store ID：`fileSearchStores/fscpenalties-tu709bvr1qti`
2. 測試查詢功能，確認映射檔顯示正常
