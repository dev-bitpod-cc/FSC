# 移除 Gemini RAG 查詢結果數量限制

## 問題描述

查詢結果顯示：「找到 4 筆相關裁罰案件，以下列出前 3 筆」

**原因**：Gemini API 的 `dynamic_retrieval_config` 預設 `result_count = 3`

---

## 解決方案

在 **FSC-Penalties-Deploy** 專案的 `app.py` 中修改 Gemini API 查詢設定。

### 📍 修改位置

找到 `generate_content` 或類似的 Gemini API 呼叫，通常在查詢函數中。

### 🔧 修改方式

#### 修改前（限制 3 筆）

```python
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents=question,
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[store_id]
                )
            )
        ],
        temperature=0.1,
        max_output_tokens=2000,
        system_instruction=system_instruction
    )
)
```

#### 修改後（移除限制或設定更大數量）

**方案 A：移除限制（推薦）**

```python
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents=question,
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[store_id],
                    # 新增：動態檢索配置
                    dynamic_retrieval_config=types.DynamicRetrievalConfig(
                        mode='MODE_DYNAMIC',  # 動態模式
                        dynamic_threshold=0.3  # 相關性閾值（0.0-1.0）
                    )
                )
            )
        ],
        temperature=0.1,
        max_output_tokens=2000,
        system_instruction=system_instruction
    )
)
```

**方案 B：設定固定數量（例如：10 筆）**

```python
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents=question,
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[store_id],
                    # 新增：動態檢索配置
                    dynamic_retrieval_config=types.DynamicRetrievalConfig(
                        mode='MODE_DYNAMIC',
                        dynamic_threshold=0.3
                    )
                )
            )
        ],
        temperature=0.1,
        max_output_tokens=4000,  # 增加輸出 token 數量以容納更多結果
        system_instruction=system_instruction
    )
)
```

**方案 C：完全不限制（顯示所有相關結果）**

```python
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents=question,
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[store_id],
                    # 新增：動態檢索配置（無限制）
                    dynamic_retrieval_config=types.DynamicRetrievalConfig(
                        mode='MODE_UNSPECIFIED',  # 不指定模式，返回所有相關結果
                        dynamic_threshold=0.0     # 最低閾值，包含更多結果
                    )
                )
            )
        ],
        temperature=0.1,
        max_output_tokens=8000,  # 大幅增加輸出限制
        system_instruction=system_instruction
    )
)
```

---

## 📋 參數說明

### `DynamicRetrievalConfig` 參數

| 參數 | 說明 | 預設值 | 建議值 |
|-----|------|--------|--------|
| `mode` | 檢索模式 | `MODE_DYNAMIC` | `MODE_UNSPECIFIED`（不限制） |
| `dynamic_threshold` | 相關性閾值（0.0-1.0） | 0.7 | `0.0`（包含更多結果） |

### `max_output_tokens` 調整

返回更多結果需要更多輸出空間：

- 預設：2000 tokens（約 3 筆結果）
- 建議：4000-8000 tokens（約 5-10 筆結果）
- 最大：32768 tokens（gemini-2.0-flash-001 支援）

---

## 🔍 完整範例程式碼

```python
from google import genai
from google.genai import types
import os

def query_rag_unlimited(question: str, store_id: str) -> dict:
    """
    執行 RAG 查詢（不限制結果數量）

    Args:
        question: 查詢問題
        store_id: File Search Store ID

    Returns:
        查詢結果（包含回答和所有參考文件）
    """

    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

    response = client.models.generate_content(
        model='gemini-2.0-flash-001',
        contents=question,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store_id],
                        # 關鍵：設定動態檢索為不限制模式
                        dynamic_retrieval_config=types.DynamicRetrievalConfig(
                            mode='MODE_UNSPECIFIED',
                            dynamic_threshold=0.0
                        )
                    )
                )
            ],
            temperature=0.1,
            max_output_tokens=8000,  # 支援更多結果
            system_instruction="""你是金管會裁罰案件查詢助手。
請提供完整、結構化的查詢結果，包含所有相關案件的詳細資訊。"""
        )
    )

    # 解析結果
    result = {
        'text': response.text,
        'sources': []
    }

    # 提取參考文件
    if hasattr(response, 'candidates') and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, 'grounding_metadata'):
            metadata = candidate.grounding_metadata
            if hasattr(metadata, 'grounding_chunks'):
                for chunk in metadata.grounding_chunks:
                    if hasattr(chunk, 'retrieved_context'):
                        context = chunk.retrieved_context
                        result['sources'].append({
                            'filename': getattr(context, 'uri', ''),
                            'snippet': getattr(context, 'text', '')[:500]
                        })

    return result

# 使用範例
if __name__ == '__main__':
    store_id = 'fileSearchStores/fscpenalties-tu709bvr1qti'
    question = '三商美邦人壽 資本適足率'

    result = query_rag_unlimited(question, store_id)

    print(f"回答:\n{result['text']}\n")
    print(f"參考文件數量: {len(result['sources'])} 筆")
```

---

## ✅ 修改步驟

### 1. 找到 app.py 中的查詢函數

搜尋關鍵字：`generate_content` 或 `GenerateContentConfig`

### 2. 加入 `dynamic_retrieval_config` 參數

在 `FileSearch` 中新增：

```python
dynamic_retrieval_config=types.DynamicRetrievalConfig(
    mode='MODE_UNSPECIFIED',
    dynamic_threshold=0.0
)
```

### 3. 調整 `max_output_tokens`

將 `max_output_tokens` 從 2000 提高到 8000

### 4. 測試

```bash
cd ~/Projects/FSC-Penalties-Deploy
streamlit run app.py
```

查詢「三商美邦人壽 資本適足率」，確認：
- ✅ 顯示所有 4 筆結果（不再是「前 3 筆」）
- ✅ 結果完整顯示（沒有截斷）

### 5. 提交變更

```bash
git add app.py
git commit -m "fix: 移除 RAG 查詢結果數量限制，顯示所有相關案件"
git push
```

---

## 🎯 預期效果

### 修改前
```
找到 4 筆相關裁罰案件，以下列出前 3 筆：

1. [案件資訊]
2. [案件資訊]
3. [案件資訊]
```

### 修改後
```
找到 4 筆相關裁罰案件：

1. [案件資訊]
2. [案件資訊]
3. [案件資訊]
4. [案件資訊]
```

---

## 📚 參考資源

- [Gemini File Search API 文檔](https://ai.google.dev/api/generate-content#dynamic_retrieval_config)
- [Dynamic Retrieval Config 說明](https://ai.google.dev/api/caching#DynamicRetrievalConfig)

---

## ⚠️ 注意事項

1. **API 費用**：返回更多結果會增加輸出 token 使用量，可能影響 API 費用
2. **回應時間**：更多結果可能延長查詢時間（但通常影響不大）
3. **UI 顯示**：確保前端 UI 能夠妥善顯示多筆結果（超過 10 筆時考慮分頁）

---

**更新日期**：2025-11-15
**適用專案**：FSC-Penalties-Deploy (Streamlit)
