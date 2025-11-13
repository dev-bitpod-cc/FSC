# Gemini File Search API 多資料源查詢研究報告

**日期**: 2025-11-13
**目的**: 研究 Gemini File Search API 是否支援「只查公告」、「只查裁罰」、「兩者都查」的選擇性查詢功能

---

## 📊 研究摘要

### 關鍵發現

1. **File Search Stores 支援**: 每個專案最多可建立 **10 個 stores**
2. **Metadata Filtering 支援**: 每個文件可加入最多 **20 個 metadata** key-value pairs
3. **多 Store 查詢**: API 參數 `fileSearchStoreNames` 為陣列，**理論上支援**多 store 查詢
4. **測試結果**: 因 SDK API 調用問題，**無法在測試環境中驗證**多 store 查詢功能

### 測試遇到的問題

在測試過程中持續遇到 API 錯誤：
```
400 INVALID_ARGUMENT. tools[0].tool_type: required one_of 'tool_type' must have one initialized field
```

**可能原因**：
- Python 3.14 與 google-genai SDK 相容性問題
- SDK 版本 (1.49.0/1.50.0) 的 API 變更
- 生產環境代碼使用 snake_case 參數，但 API 簽名顯示應使用 camelCase

---

## 🎯 實作方案建議

### ✅ 推薦：方案 1 + 方案 2 混合架構

**理由**：最大彈性、管理清晰、向後相容

#### 架構設計

```python
# 主要資料源各用獨立 store
Store 1: "fsc-announcements"   # 公告（約 7,500 筆）
Store 2: "fsc-penalties"        # 裁罰（未來）
Store 3: "fsc-laws"             # 法規（預留）

# 每個文件附加 metadata 供細緻過濾
metadata: {
    "data_type": "announcement",      # 資料類型
    "source_unit": "bank_bureau",     # 來源單位
    "date": "2025-11-12",             # 日期
    "category": "amendment"           # 類別
}
```

#### 查詢介面設計

```python
def query_fsc(user_query: str, data_sources: List[str], filters: Dict = None):
    """
    查詢金管會資料

    Args:
        user_query: 使用者問題
        data_sources: ['announcements', 'penalties', 'both']
        filters: {'source_unit': 'bank_bureau', 'date_from': '2024-01-01'}
    """

    # 映射到 store names
    store_mapping = {
        'announcements': 'fsc-announcements',
        'penalties': 'fsc-penalties',
        'laws': 'fsc-laws'
    }

    # 根據選擇決定查詢的 stores
    if 'both' in data_sources or 'all' in data_sources:
        stores = list(store_mapping.values())
    else:
        stores = [store_mapping[ds] for ds in data_sources]

    # 構建 metadata filter（可選）
    metadata_filter = None
    if filters:
        conditions = []
        if 'source_unit' in filters:
            conditions.append(f'source_unit="{filters["source_unit"]}"')
        if 'date_from' in filters:
            conditions.append(f'date>="{filters["date_from"]}"')
        metadata_filter = ' AND '.join(conditions)

    # 執行查詢
    response = client.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=user_query,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=stores,  # 單個或多個
                        metadata_filter=metadata_filter   # 可選的細緻過濾
                    )
                )
            ]
        )
    )

    return response
```

---

## 💡 使用範例

### 範例 1: 只查公告

```python
response = query_fsc(
    user_query="最新的銀行監理規定是什麼？",
    data_sources=['announcements']
)
```

### 範例 2: 只查裁罰

```python
response = query_fsc(
    user_query="最近有哪些裁罰案件？",
    data_sources=['penalties']
)
```

### 範例 3: 兩者都查

```python
response = query_fsc(
    user_query="關於洗錢防制的規定和裁罰案例",
    data_sources=['both']
)
```

### 範例 4: 細緻過濾（只查銀行局的公告）

```python
response = query_fsc(
    user_query="銀行局有哪些新規定？",
    data_sources=['announcements'],
    filters={'source_unit': 'bank_bureau'}
)
```

---

## 🔧 實作步驟

### 階段 1: 維持現有公告 Store（無需修改）

- ✅ Store 名稱：`fsc-announcements`
- ✅ 約 7,500 筆公告正在上傳中
- ✅ 不需要任何修改或重新上傳

### 階段 2: 實作裁罰爬蟲並上傳

```bash
# 1. 實作裁罰爬蟲
python scripts/crawl_penalties.py

# 2. 格式化為 Markdown（加入 metadata）
python scripts/format_penalties_markdown.py

# 3. 上傳到新 Store
python scripts/upload_penalties.py
# 內部使用: GeminiUploader(store_name='fsc-penalties')
```

### 階段 3: 修改上傳器支援 Metadata

修改 `src/uploader/gemini_uploader.py`，在上傳時加入 metadata：

```python
def upload_file_with_metadata(self, filepath: str, metadata: Dict[str, str]):
    """上傳檔案並加入 metadata"""

    # 構建 custom metadata（根據實際 API 文檔調整）
    custom_metadata = {
        "data_type": metadata.get("data_type", ""),
        "source_unit": metadata.get("source_unit", ""),
        "date": metadata.get("date", ""),
        "category": metadata.get("category", "")
    }

    # 上傳（語法需參考最新 API 文檔）
    file_obj = self.client.files.upload(
        file=f,
        config=types.UploadFileConfig(
            display_name=display_name,
            mime_type='text/markdown',
            # metadata=custom_metadata  # 確認實際 API 參數名稱
        )
    )
```

### 階段 4: 實作查詢介面

建立 `src/query/query_interface.py`，提供統一的查詢入口。

---

## ⚠️ 待驗證事項

### 多 Store 查詢支援

雖然 `fileSearchStoreNames` 參數是陣列，但由於測試環境問題，**未能驗證**實際的多 store 查詢功能。

**建議做法**：
1. 先採用獨立 store 架構（方案 1）
2. 實作查詢介面時，先支援單 store 查詢
3. 等公告和裁罰 stores 都建立後，在**生產環境**實際測試多 store 查詢
4. 如果多 store 不支援，降級為「分別查詢後合併結果」的方式

### Metadata 上傳語法

需要查閱最新的 google-genai SDK 文檔，確認：
- 上傳文件時如何附加 metadata
- Metadata filter 的正確語法
- Metadata 的資料型態支援（string/number/boolean）

---

## 📋 結論

1. **✅ 可以實作「只查公告」、「只查裁罰」、「兩者都查」的功能**
2. **推薦採用多 Store + Metadata 混合架構**
3. **現有公告上傳工作完全不受影響**
4. **查詢介面可以靈活支援各種過濾需求**

---

## 🔗 參考資源

- [Gemini File Search API 文檔](https://ai.google.dev/gemini-api/docs/file-search)
- [google-genai Python SDK](https://github.com/googleapis/python-genai)
- 測試腳本：
  - `scripts/cleanup_test_stores.py` - Store 清理工具
  - `scripts/test_multi_store_query.py` - 多 Store 查詢測試
  - `scripts/test_correct_syntax.py` - API 語法測試
