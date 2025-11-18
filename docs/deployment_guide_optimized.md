# 優化版 RAG 系統部署指南

**目標:** 將優化後的 Plain Text 格式部署到生產環境,取代現有的 Markdown 版本

**預期改善:**
- 檔案大小減少 15-35%
- 語義密度提升 20%
- 檢索準確度提升 40-60%

---

## 📋 前置準備

### 1. 環境需求

```bash
# Python 環境
python >= 3.9

# 必要套件
pip install google-genai loguru

# API Key
export GEMINI_API_KEY="your_api_key_here"
```

### 2. 資料準備

確保有完整的裁罰案件資料:

```bash
# 選項 A: 使用現有爬蟲重新爬取 (推薦)
cd ~/Projects/FSC
python src/crawlers/penalties.py

# 選項 B: 從備份還原
# 將 raw.jsonl 複製到 data/penalties/raw.jsonl

# 驗證資料
wc -l data/penalties/raw.jsonl
# 預期輸出: 495 data/penalties/raw.jsonl
```

---

## 🚀 完整部署流程

### Step 1: 生成優化檔案和 file_mapping.json

```bash
cd ~/Projects/FSC

# 完整生成 (Plain Text + file_mapping.json)
python scripts/generate_optimized_plaintext.py \
    --source penalties \
    --output data/plaintext_optimized/penalties_individual

# 選項: 使用 LLM 提取法條 (更準確但較慢,需額外 API 費用)
python scripts/generate_optimized_plaintext.py \
    --source penalties \
    --output data/plaintext_optimized/penalties_individual \
    --use-llm
```

**預期輸出:**
```
總案件數: 495
成功建立: 495 個檔案
輸出目錄: data/plaintext_optimized/penalties_individual
總大小: ~2,000 KB (~2 MB)
平均大小: ~4 KB

✓ file_mapping.json 已生成
  位置: data/penalties/file_mapping.json
```

**驗證:**
```bash
# 檢查檔案數量
ls data/plaintext_optimized/penalties_individual/*.txt | wc -l
# 預期: 495

# 檢查 file_mapping.json
python -c "import json; m=json.load(open('data/penalties/file_mapping.json')); print(f'Mapping entries: {len(m)}')"
# 預期: Mapping entries: 495
```

---

### Step 2: 上傳到 Gemini File Search Store

```bash
# 上傳所有優化檔案
python scripts/upload_optimized_to_gemini.py \
    --plaintext-dir data/plaintext_optimized/penalties_individual \
    --mapping-file data/penalties/file_mapping.json \
    --store-name fsc-penalties-optimized \
    --delay 1.5

# 如果有上傳失敗,可以重試
python scripts/upload_optimized_to_gemini.py \
    --plaintext-dir data/plaintext_optimized/penalties_individual \
    --store-name fsc-penalties-optimized \
    --retry-failed
```

**預期輸出:**
```
總檔案數: 495
成功上傳: 495
跳過(已上傳): 0
上傳失敗: 0
總大小: ~2 MB

✅ Gemini File Search Store:
   Store ID: fileSearchStores/fscpenaltiesoptimized-XXXXX
   Store 名稱: fsc-penalties-optimized

✅ file_mapping.json 已更新:
   位置: data/penalties/file_mapping.json
   包含 gemini_id 和 gemini_uri
```

**重要:** 記下 Store ID,稍後前端整合時需要使用。

**驗證:**
```bash
# 檢查 file_mapping.json 是否包含 gemini_id
python -c "
import json
m = json.load(open('data/penalties/file_mapping.json'))
with_gemini = sum(1 for v in m.values() if v.get('gemini_id'))
print(f'Entries with gemini_id: {with_gemini}/{len(m)}')
"
# 預期: Entries with gemini_id: 495/495
```

---

### Step 3: 整合到前端 (FSC-Penalties-Deploy)

#### 3.1 複製更新後的 file_mapping.json

```bash
cd ~/Projects/FSC

# 複製到前端專案
cp data/penalties/file_mapping.json \
   ~/Projects/FSC-Penalties-Deploy/data/file_mapping.json

# 驗證
ls -lh ~/Projects/FSC-Penalties-Deploy/data/file_mapping.json
```

#### 3.2 更新前端配置

編輯 `~/Projects/FSC-Penalties-Deploy/app.py` 或配置檔:

```python
# 原始 (Markdown 版本)
STORE_ID = "fileSearchStores/fscpenalties-tu709bvr1qti"

# 更新為優化版本
STORE_ID = "fileSearchStores/fscpenaltiesoptimized-XXXXX"  # 使用 Step 2 記下的 Store ID
```

#### 3.3 更新查詢結果顯示邏輯

**範例程式碼:**

```python
import json
from pathlib import Path

# 載入 file_mapping
file_mapping_path = Path('data/file_mapping.json')
with open(file_mapping_path, 'r', encoding='utf-8') as f:
    file_mapping = json.load(f)

def display_query_result(response):
    """顯示查詢結果,從 file_mapping 取得完整 metadata"""

    # 提取 Gemini 回應的引用來源
    if response.candidates[0].grounding_metadata:
        for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
            gemini_file_id = chunk.retrieved_context.uri.split('/')[-1]

            # 從 file_mapping 反查文件 ID
            doc_id = None
            for doc_id_candidate, doc_info in file_mapping.items():
                if doc_info.get('gemini_id') == f"files/{gemini_file_id}":
                    doc_id = doc_id_candidate
                    break

            if not doc_id:
                continue

            # 取得完整 metadata
            metadata = file_mapping[doc_id]

            # 顯示引用來源
            print("📄 引用來源:")
            print("━" * 80)
            print(f"標題: {metadata.get('title', 'N/A')}")
            print(f"日期: {metadata.get('date', 'N/A')}")
            print(f"來源: {metadata.get('source_raw', 'N/A')}")
            print(f"機構: {metadata.get('institution', 'N/A')}")
            print(f"罰款: {metadata.get('penalty_amount_text', 'N/A')}")
            print(f"發文字號: {metadata.get('doc_number', 'N/A')}")
            print()
            print(f"🔗 原始連結: {metadata.get('original_url', 'N/A')}")
            print()

            # 法條連結
            if metadata.get('applicable_laws'):
                print("📜 適用法條:")
                for law in metadata['applicable_laws']:
                    law_link = metadata.get('law_links', {}).get(law, '')
                    if law_link:
                        print(f"  • {law} - {law_link}")
                    else:
                        print(f"  • {law}")
            print("━" * 80)
```

#### 3.4 測試前端整合

```bash
cd ~/Projects/FSC-Penalties-Deploy

# 啟動前端
streamlit run app.py

# 測試查詢
# 例如: "董事出差報銷缺失"
# 預期: 看到優化後的檢索結果,包含完整的 metadata 顯示
```

---

### Step 4: 驗證和比較

#### 4.1 檢索效果驗證

建立測試查詢集,比較優化前後的效果:

```python
# scripts/test_queries.py
test_queries = [
    "董事出差報銷缺失",
    "保單借款購買保單",
    "違反保險法第148條之3",
    "內部控制制度缺失",
    "銀行業客服盜刷信用卡"
]

# 查詢舊 Store (Markdown)
old_store_id = "fileSearchStores/fscpenalties-tu709bvr1qti"

# 查詢新 Store (優化 Plain Text)
new_store_id = "fileSearchStores/fscpenaltiesoptimized-XXXXX"

# 比較:
# - Sources Count: 返回的來源數量
# - Relevance: 回答的相關性
# - Precision: 關鍵字匹配精確度
```

#### 4.2 預期改善效果

| 指標 | Markdown 版本 | 優化版本 | 改善幅度 |
|------|--------------|---------|---------|
| **檔案大小** | 12 KB | 4-5 KB | -60~65% |
| **Sources Count** | 2-3 | 4-5 | +50~100% |
| **查詢準確度** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | +40~60% |
| **關鍵字匹配** | 中等 | 高 | 明顯提升 |

---

## 📝 完整部署檢查清單

### 資料準備 ✓
- [ ] 爬取或準備完整的 495 筆裁罰案件資料
- [ ] 驗證 `data/penalties/raw.jsonl` 存在且有 495 行

### 優化檔案生成 ✓
- [ ] 執行 `generate_optimized_plaintext.py`
- [ ] 驗證生成 495 個 `.txt` 檔案
- [ ] 驗證 `file_mapping.json` 包含 495 筆資料
- [ ] 檢查 file_mapping 包含所有必要欄位:
  - `display_name`, `title`, `date`, `source_raw`
  - `institution`, `doc_number`, `penalty_amount_text`
  - `original_url`, `applicable_laws`, `law_links`

### Gemini 上傳 ✓
- [ ] 執行 `upload_optimized_to_gemini.py`
- [ ] 驗證所有 495 個檔案上傳成功
- [ ] 記下新的 Store ID
- [ ] 驗證 `file_mapping.json` 已更新:
  - 所有 entry 都有 `gemini_id`
  - 所有 entry 都有 `gemini_uri`

### 前端整合 ✓
- [ ] 複製 `file_mapping.json` 到前端專案
- [ ] 更新前端的 Store ID
- [ ] 實作查詢結果顯示邏輯 (從 file_mapping 取得 metadata)
- [ ] 測試查詢功能運作正常
- [ ] 測試 metadata 顯示正確 (標題、日期、原始連結等)

### 驗證測試 ✓
- [ ] 執行測試查詢集,驗證檢索效果
- [ ] 比較優化前後的差異
- [ ] 確認無 regression (功能不退步)

### 部署上線 ✓
- [ ] 備份舊版 Store ID (以防需要回滾)
- [ ] 部署前端更新
- [ ] 監控查詢效果和錯誤率

---

## 🔄 回滾計畫

如果優化版本出現問題,可以快速回滾到 Markdown 版本:

```python
# 前端配置回滾
STORE_ID = "fileSearchStores/fscpenalties-tu709bvr1qti"  # Markdown 版本

# 或使用舊的 file_mapping.json (如果有備份)
cp file_mapping.json.backup file_mapping.json
```

---

## 📊 費用估算

### Gemini API 費用

**上傳費用:** (一次性)
- 495 個檔案 × 平均 4 KB = ~2 MB
- Gemini File API 上傳: 免費

**查詢費用:** (持續)
- File Search 查詢: 按 API 使用量計費
- 預期與 Markdown 版本相同或稍低 (檔案更小)

**法條提取 (選用):**
- 使用 LLM 提取法條: 495 筆 × ~2K tokens = ~1M tokens
- Gemini 2.5 Flash: ~$0.075 / 1M input tokens
- **預估費用: ~$0.10 USD** (一次性)

---

## 🐛 常見問題

### Q1: 上傳失敗怎麼辦?

```bash
# 查看失敗的檔案
python scripts/upload_optimized_to_gemini.py --retry-failed

# 檢查 logs
tail -f logs/upload_optimized_to_gemini.log
```

### Q2: file_mapping.json 沒有 gemini_id?

確認上傳時有使用 `--update-mapping` 參數 (預設開啟):

```bash
python scripts/upload_optimized_to_gemini.py \
    --plaintext-dir data/plaintext_optimized/penalties_individual \
    --mapping-file data/penalties/file_mapping.json
```

### Q3: 前端查詢無結果?

檢查:
1. Store ID 是否正確更新
2. file_mapping.json 是否已複製到前端專案
3. Gemini API Key 是否有效

### Q4: 如何驗證檔案格式正確?

```bash
# 檢查單個檔案
cat data/plaintext_optimized/penalties_individual/fsc_pen_20250925_0001.txt

# 預期格式:
# 發文日期: YYYY-MM-DD
# 來源單位: XXX
# 機構名稱: XXX
# 罰款金額: XXX
# 發文字號: XXX
# ---
# (內容...)
```

---

## 📚 相關文檔

- **元資料策略:** `docs/metadata_strategy.md`
- **格式對比分析:** `docs/plaintext_vs_markdown_comparison.md`
- **優化格式分析:** `docs/plaintext_format_optimization.md`
- **實作進度:** `docs/optimization_progress.md`

---

## ✅ 部署後驗證

部署完成後,進行以下驗證:

### 1. 功能驗證
- [ ] 查詢功能正常運作
- [ ] 查詢結果包含 metadata (標題、日期、機構等)
- [ ] 原始連結可以正常存取
- [ ] 法條連結正確

### 2. 效能驗證
- [ ] 查詢速度無明顯變慢
- [ ] Sources Count 增加
- [ ] 查詢準確度提升

### 3. 使用者體驗驗證
- [ ] UI 顯示完整且美觀
- [ ] Metadata 資訊清晰易讀
- [ ] 無錯誤訊息或 broken links

---

**部署負責人:** _______
**部署日期:** _______
**Store ID (優化版本):** _______
**備註:** _______

---

**最後更新:** 2025-11-18
**版本:** 1.0
