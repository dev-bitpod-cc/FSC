# 移除「以下列出前 3 筆」限制 - 簡單解決方案

## 問題

查詢結果顯示：**「找到 4 筆相關裁罰案件，以下列出前 3 筆」**

## ✅ 解決方案（Prompt Engineering）

這個問題是 Gemini 模型自行決定只顯示部分結果。最簡單的解決方法是**修改 system instruction**，明確要求顯示所有結果。

---

## 📝 修改步驟（FSC-Penalties-Deploy/app.py）

### 1. 找到查詢函數中的 `system_instruction`

搜尋：`system_instruction` 或 `generate_content`

### 2. 修改前

```python
system_instruction = """你是金管會裁罰案件查詢助手。
請提供結構化的查詢結果。"""

response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents=question,
    config=types.GenerateContentConfig(
        tools=[...],
        temperature=0.1,
        max_output_tokens=2000,
        system_instruction=system_instruction
    )
)
```

### 3. 修改後

```python
system_instruction = """你是金管會裁罰案件查詢助手。

**重要指示**：
1. 請列出「所有」找到的相關裁罰案件，不要省略任何一筆
2. 每筆案件都要完整顯示資訊
3. 不要使用「以下列出前 N 筆」這樣的限制性語句
4. 如果找到 X 筆案件，請全部列出

**回答格式**：
找到 X 筆相關裁罰案件：

### 1. [第一筆案件名稱]
- **日期**：...
- **發文字號**：...
- **來源單位**：...
- **被處罰對象**：...
- **違規事項**：...
- **裁罰金額**：...
- **法律依據**：...

### 2. [第二筆案件名稱]
...

[以此類推，列出所有案件]
"""

response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents=question,
    config=types.GenerateContentConfig(
        tools=[...],
        temperature=0.1,
        max_output_tokens=8000,  # 增加輸出限制以容納更多結果
        system_instruction=system_instruction
    )
)
```

### 關鍵修改點：

1. ✅ **明確指示**：「列出所有找到的案件，不要省略」
2. ✅ **禁止限制語句**：「不要使用『以下列出前 N 筆』」
3. ✅ **提供格式範例**：讓模型知道如何組織多筆結果
4. ✅ **增加輸出限制**：`max_output_tokens` 從 2000 提高到 8000

---

## 📋 完整範例程式碼

```python
from google import genai
from google.genai import types
import os

def query_all_cases(question: str, store_id: str) -> dict:
    """
    執行 RAG 查詢（顯示所有結果）

    Args:
        question: 查詢問題
        store_id: File Search Store ID

    Returns:
        查詢結果
    """

    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

    # 關鍵：明確要求列出所有結果的 system instruction
    system_instruction = """你是金管會裁罰案件查詢助手。

**重要指示**：
1. 請列出「所有」找到的相關裁罰案件，不要省略任何一筆
2. 每筆案件都要完整顯示資訊
3. 不要使用「以下列出前 N 筆」這樣的限制性語句
4. 如果找到 X 筆案件，請全部列出

**回答格式**：
找到 X 筆相關裁罰案件：

### 1. [第一筆案件名稱]
- **日期**：...
- **發文字號**：...
- **來源單位**：...
- **被處罰對象**：...
- **違規事項**：...
- **裁罰金額**：...
- **法律依據**：...

### 2. [第二筆案件名稱]
...

[以此類推，列出所有案件]
"""

    response = client.models.generate_content(
        model='gemini-2.0-flash-001',
        contents=question,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    # 根據您的實際 API 版本使用正確的語法
                    # 可能是 file_search 或 fileSearch
                    file_search=types.FileSearch(
                        file_search_store_names=[store_id]
                    )
                )
            ],
            temperature=0.1,
            max_output_tokens=8000,  # 支援更多結果
            system_instruction=system_instruction
        )
    )

    return {
        'text': response.text,
        'sources': _extract_sources(response)
    }

def _extract_sources(response):
    """提取參考文件"""
    sources = []

    if hasattr(response, 'candidates') and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, 'grounding_metadata'):
            metadata = candidate.grounding_metadata
            if hasattr(metadata, 'grounding_chunks'):
                for chunk in metadata.grounding_chunks:
                    if hasattr(chunk, 'retrieved_context'):
                        context = chunk.retrieved_context
                        sources.append({
                            'filename': getattr(context, 'uri', ''),
                            'snippet': getattr(context, 'text', '')[:500]
                        })

    return sources

# 使用範例
if __name__ == '__main__':
    store_id = 'fileSearchStores/fscpenalties-tu709bvr1qti'
    question = '三商美邦人壽 資本適足率'

    result = query_all_cases(question, store_id)

    print(result['text'])
    print(f"\n參考文件數量: {len(result['sources'])} 筆")
```

---

## 🎯 預期效果

### 修改前
```
找到 4 筆相關裁罰案件，以下列出前 3 筆：

### 1. 三商美邦人壽（2024-07-12）
...

### 2. 三商美邦人壽（2015-08-28）
...

### 3. 三商美邦人壽（2012-03-26）
...
```

### 修改後
```
找到 4 筆相關裁罰案件：

### 1. 三商美邦人壽（2024-07-12）
...

### 2. 三商美邦人壽（2015-08-28）
...

### 3. 三商美邦人壽（2012-03-26）
...

### 4. 三商美邦人壽（2009-XX-XX）
...
```

---

## ✅ 測試清單

修改完成後，請測試：

- [ ] 查詢「三商美邦人壽 資本適足率」
- [ ] 確認顯示「找到 4 筆」且全部列出（不是「前 3 筆」）
- [ ] 每筆案件資訊完整
- [ ] 沒有被截斷的內容
- [ ] 參考文件區塊也顯示所有來源

---

## 📚 其他可能的調整

### 如果仍然只顯示部分結果

1. **進一步增加 max_output_tokens**
   ```python
   max_output_tokens=12000  # 或更高（最大 32768）
   ```

2. **在查詢問題中加入提示**
   ```python
   enhanced_question = f"{question}\n\n請列出所有相關的裁罰案件，不要省略任何一筆。"
   ```

3. **使用 Gemini 2.0 Flash Thinking（如果可用）**
   ```python
   model='gemini-2.0-flash-thinking-exp'  # 實驗性模型，可能有更好的理解能力
   ```

---

## 📌 重要提示

1. **API 費用**：`max_output_tokens=8000` 會增加輸出 token 使用量
2. **回應時間**：更多內容可能延長查詢時間（但通常影響不大）
3. **Streamlit 顯示**：確保前端 UI 能妥善顯示多筆結果

---

## 🔧 故障排除

**問題**：修改後仍然顯示「前 3 筆」

**可能原因**：
1. `system_instruction` 沒有正確傳遞到 API
2. `max_output_tokens` 太小（建議至少 6000）
3. Gemini 模型判斷只有 3 筆真正相關

**解決方法**：
1. 確認 `system_instruction` 參數有正確傳入
2. 檢查 console 輸出，確認 API 請求成功
3. 嘗試不同的查詢問題測試

---

**更新日期**：2025-11-15
**方法**：Prompt Engineering（最簡單、最有效）
**適用專案**：FSC-Penalties-Deploy (Streamlit)
