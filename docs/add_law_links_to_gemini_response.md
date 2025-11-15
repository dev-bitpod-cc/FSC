# 為 Gemini 查詢結果中的法條添加連結

## 問題描述

Gemini 查詢結果中顯示：
```
法律依據：保險法第143條之6第2款第1目、第6目規定。
```

但這些法條沒有超連結，用戶無法點擊查看法規內容。

---

## 解決方案

在 **FSC-Penalties-Deploy/app.py** 中，處理 Gemini 回應時，自動將法條文字轉換為帶連結的 Markdown 格式。

---

## 📋 實作步驟

### 1. 創建法條連結插入函數

在 `app.py` 中添加以下函數：

```python
import re

def insert_law_links_to_text(text: str, file_mapping: dict) -> str:
    """
    將文字中的法條替換為帶連結的 Markdown 格式

    Args:
        text: 原始文字（Gemini 的回答）
        file_mapping: file_mapping.json 的內容

    Returns:
        插入連結後的文字
    """
    # 收集所有 law_links
    all_law_links = {}

    for file_id, info in file_mapping.items():
        law_links = info.get('law_links', {})
        all_law_links.update(law_links)

    if not all_law_links:
        return text

    # 按法條文字長度排序（從長到短），避免短的先被匹配
    sorted_laws = sorted(all_law_links.items(), key=lambda x: len(x[0]), reverse=True)

    for law_text, url in sorted_laws:
        # 跳過太短的匹配（避免誤匹配）
        if len(law_text) < 6:
            continue

        # 跳過簡寫版本（只替換完整法條）
        if law_text.startswith('第') and not any(law_text.startswith(prefix) for prefix in ['第一', '第二', '第三']):
            # 簡寫版本（如「第171條之1」）可能會誤匹配，需要更謹慎
            # 檢查前面是否有法律名稱
            if not any(law_name in law_text for law_name in ['法', '條例', '辦法', '規則']):
                # 對於簡寫版本，只在有明確上下文時替換
                pattern = f'([、，；])({re.escape(law_text)})'
                text = re.sub(pattern, f'\\1[{law_text}]({url})', text)
                continue

        # 跳過已經有連結的文字
        if f'[{law_text}]' in text:
            continue

        # 轉義特殊字符
        escaped_law = re.escape(law_text)

        # 替換（允許多次替換）
        pattern = f'(?<!\\[)({escaped_law})(?!\\])'
        text = re.sub(pattern, f'[{law_text}]({url})', text)

    return text


def process_gemini_response(response_text: str, sources: list, file_mapping: dict) -> str:
    """
    處理 Gemini 回應，插入法條連結

    Args:
        response_text: Gemini 的回答
        sources: 參考文件列表
        file_mapping: file_mapping.json 的內容

    Returns:
        處理後的文字
    """
    # 插入法條連結
    processed_text = insert_law_links_to_text(response_text, file_mapping)

    return processed_text
```

### 2. 修改查詢結果顯示邏輯

找到顯示 Gemini 回答的地方（通常在查詢按鈕的 callback 中），修改如下：

#### 修改前

```python
# 顯示 Gemini 回答
st.markdown("---")
st.markdown(result['text'])
```

#### 修改後

```python
# 載入映射檔
mapping = load_file_mapping()  # 之前已經定義的函數

# 處理回答，插入法條連結
processed_text = process_gemini_response(
    result['text'],
    result.get('sources', []),
    mapping
)

# 顯示處理後的回答
st.markdown("---")
st.markdown(processed_text)
```

---

## 📝 完整範例程式碼

```python
import streamlit as st
import re
import json
from pathlib import Path

# ===== 載入映射檔 =====
@st.cache_data
def load_file_mapping():
    """載入檔案映射檔"""
    mapping_file = Path(__file__).parent / 'file_mapping.json'

    if not mapping_file.exists():
        return {}

    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"⚠️ 載入映射檔失敗: {e}")
        return {}


# ===== 法條連結插入 =====
def insert_law_links_to_text(text: str, file_mapping: dict) -> str:
    """
    將文字中的法條替換為帶連結的 Markdown 格式

    Args:
        text: 原始文字（Gemini 的回答）
        file_mapping: file_mapping.json 的內容

    Returns:
        插入連結後的文字
    """
    # 收集所有 law_links
    all_law_links = {}

    for file_id, info in file_mapping.items():
        law_links = info.get('law_links', {})
        all_law_links.update(law_links)

    if not all_law_links:
        return text

    # 按法條文字長度排序（從長到短），避免短的先被匹配
    sorted_laws = sorted(all_law_links.items(), key=lambda x: len(x[0]), reverse=True)

    replaced_count = 0

    for law_text, url in sorted_laws:
        # 跳過太短的匹配（避免誤匹配）
        if len(law_text) < 6:
            continue

        # 跳過已經有連結的文字
        if f'[{law_text}]' in text:
            continue

        # 轉義特殊字符
        escaped_law = re.escape(law_text)

        # 替換
        pattern = f'(?<!\\[)({escaped_law})(?!\\])'
        new_text = re.sub(pattern, f'[{law_text}]({url})', text)

        if new_text != text:
            replaced_count += 1
            text = new_text

    return text


def process_gemini_response(response_text: str, file_mapping: dict) -> str:
    """
    處理 Gemini 回應，插入法條連結

    Args:
        response_text: Gemini 的回答
        file_mapping: file_mapping.json 的內容

    Returns:
        處理後的文字
    """
    # 插入法條連結
    processed_text = insert_law_links_to_text(response_text, file_mapping)

    return processed_text


# ===== 在查詢結果顯示處使用 =====
def display_query_result(result: dict):
    """顯示查詢結果"""

    # 載入映射檔
    mapping = load_file_mapping()

    # 處理 Gemini 回答，插入法條連結
    processed_text = process_gemini_response(result['text'], mapping)

    # 顯示處理後的回答
    st.markdown("---")
    st.subheader("✅ 查詢結果")
    st.markdown(processed_text)  # 這裡會顯示帶連結的法條

    # ... 其他顯示邏輯（參考文件等）
```

---

## 🎯 預期效果

### 修改前（無連結）

```
法律依據：保險法第143條之6第2款第1目、第6目規定。
```

### 修改後（有連結）

```
法律依據：[保險法第143條之6第2款第1目](https://law.moj.gov.tw/...)、
[第6目](https://law.moj.gov.tw/...)規定。
```

用戶點擊連結後，會跳轉到法規資料庫查看該法條內容。

---

## ✅ 測試步驟

1. **修改 app.py**
   - 加入上述函數
   - 修改查詢結果顯示邏輯

2. **確認 file_mapping.json 已同步**
   ```bash
   ls -lh ~/Projects/FSC-Penalties-Deploy/file_mapping.json
   ```

3. **本地測試**
   ```bash
   cd ~/Projects/FSC-Penalties-Deploy
   streamlit run app.py
   ```

4. **查詢測試案例**
   - 輸入：「三商美邦人壽 資本適足率」
   - 檢查：法條是否變成可點擊的連結
   - 點擊連結：確認跳轉到正確的法規資料庫頁面

5. **提交到 GitHub**
   ```bash
   git add app.py
   git commit -m "feat: 為 Gemini 回答中的法條自動添加連結"
   git push
   ```

---

## 🔧 進階優化

### 1. 處理複合引用

對於「第143條之6第2款第1目、第6目」這種格式：

```python
# 在 insert_law_links_to_text 中添加特殊處理
def handle_compound_references(text: str, all_law_links: dict) -> str:
    """處理複合法條引用"""

    # 匹配格式：法律名稱第X條第Y款第Z目、第W目
    pattern = r'([^\s]+法)第(\d+)條(?:之(\d+))?第(\d+)款第(\d+)目、第(\d+)目'

    def replace_compound(match):
        law_name = match.group(1)
        article = match.group(2)
        sub_article = match.group(3) or ''
        clause = match.group(4)
        point1 = match.group(5)
        point2 = match.group(6)

        # 構建兩個完整法條
        law1 = f"{law_name}第{article}條"
        if sub_article:
            law1 += f"之{sub_article}"
        law1 += f"第{clause}款第{point1}目"

        law2 = f"{law_name}第{article}條"
        if sub_article:
            law2 += f"之{sub_article}"
        law2 += f"第{clause}款第{point2}目"

        # 查找連結
        url1 = all_law_links.get(law1, '')
        url2 = all_law_links.get(law2, '')

        if url1 and url2:
            return f"[{law1}]({url1})、[第{point2}目]({url2})"
        elif url1:
            return f"[{law1}]({url1})、第{point2}目"
        else:
            return match.group(0)  # 保持原樣

    return re.sub(pattern, replace_compound, text)
```

### 2. 快取處理結果

```python
@st.cache_data
def get_all_law_links(file_mapping: dict) -> dict:
    """提取並快取所有法條連結（避免重複處理）"""
    all_law_links = {}

    for file_id, info in file_mapping.items():
        law_links = info.get('law_links', {})
        all_law_links.update(law_links)

    return all_law_links
```

---

## 📚 參考資源

- `file_mapping.json` - 包含所有法條連結的映射檔
- `scripts/generate_file_mapping.py` - 生成映射檔的腳本
- `scripts/update_law_links_with_abbreviations.py` - 更新法條連結的腳本

---

**更新日期**：2025-11-15
**適用專案**：FSC-Penalties-Deploy (Streamlit)
**問題**：Gemini 查詢結果中的法條沒有連結
**解決方案**：在前端處理回答時，使用 file_mapping.json 自動插入法條連結
