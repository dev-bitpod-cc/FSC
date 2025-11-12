# RAG 查詢結果顯示指南

## 概述

本文檔說明如何處理和顯示 Gemini File Search RAG 查詢結果，特別是關於 Markdown 格式的處理。

## Markdown 格式在 RAG 中的表現

### 1. 上傳格式

**✅ 使用 Markdown 格式上傳到 File Search Store**

- Gemini 完全支援 Markdown 格式
- Markdown 的結構化標記有助於 RAG 理解文件層級
- Google 官方推薦使用 Markdown 作為 RAG 輸入格式

**我們的 Markdown 格式結構**：

```markdown
# [公告標題]

## 📋 基本資訊

- **文件編號**: `fsc_ann_YYYYMMDD_NNNN`
- **發布日期**: YYYY-MM-DD
- **來源單位**: [單位名稱]
- **單位代碼**: [代碼]
- **公告類型**: [類型]

## 📄 內容

[公告內容文字...]

## 📎 相關附件

1. **附件名稱** ([PDF](url))

---

*標籤: 日期:YYYY-MM-DD | 來源:source_code | 類型:category*
```

**優點**：
- 清楚的標題層級（Gemini 能理解文件結構）
- Metadata 明確標記（日期、來源、類型）
- 內容與元資訊分離
- 適合語意檢索

---

## 2. RAG 查詢回應格式

### 回應結構

Gemini RAG 查詢會返回以下內容：

```python
response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents="查詢問題",
    config=types.GenerateContentConfig(
        tools=[types.Tool(file_search=...)]
    )
)

# 回應包含:
# 1. response.text - AI 生成的自然語言回答
# 2. response.candidates[0].grounding_metadata - 參考文件資訊
# 3. response.candidates[0].grounding_chunks - 引用的原始段落
```

### 三種內容類型

#### A. AI 回答 (response.text)

**格式**: 自然語言
**包含 Markdown**: ❌ 否

```python
print(response.text)
# 輸出範例:
# "根據金管會 2025-11-12 的公告，保險局修正了「財產保險業經營傷害保險及
#  健康保險業務管理辦法」，主要修正內容包括..."
```

✅ **可以直接顯示**，Gemini 已經將 Markdown 轉換為自然語言

---

#### B. 參考文件檔名 (grounding_metadata)

**格式**: 語意化檔名
**包含 Markdown**: ❌ 否

```python
for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
    print(chunk.retrieval_metadata.file_name)

# 輸出範例:
# "fsc_ann_20251112_0001_保險局_修正「財產保險業經營傷害保險及健康保險業務管理辦法」.md"
```

✅ **可以直接顯示**，檔名已經是語意化的（包含 ID、來源、標題）

---

#### C. 引用段落 (grounding_chunks)

**格式**: 原始 Markdown 文字
**包含 Markdown**: ⚠️ **是的，包含原始 Markdown 語法**

```python
for chunk in response.candidates[0].grounding_chunks:
    print(chunk.text)

# 輸出範例:
# "## 📋 基本資訊\n\n- **文件編號**: `fsc_ann_20251112_0001`\n- **發布日期**: 2025-11-12..."
```

❌ **不能直接顯示**，使用者會看到 `##`、`**`、`` ` `` 等 Markdown 符號

---

## 3. 前端顯示處理方案

### 推薦方案：使用 Markdown 渲染器

**✅ 在前端使用 Markdown 渲染器將引用段落轉換為 HTML**

#### JavaScript 範例 (React/Next.js)

```javascript
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
});

function ReferenceChunk({ chunk }) {
  // 渲染 Markdown 為 HTML
  const html = md.render(chunk.text);

  return (
    <div
      className="reference-chunk"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
```

**推薦的 Markdown 渲染器**：
- **markdown-it** (JavaScript) - 功能完整、擴充性強
- **marked** (JavaScript) - 輕量、快速
- **react-markdown** (React) - React 元件化
- **Python-Markdown** (Python 後端) - 伺服器端渲染

#### Python 範例 (後端渲染)

```python
import markdown

def render_chunk(chunk_text: str) -> str:
    """將 Markdown 轉換為 HTML"""
    md = markdown.Markdown(extensions=[
        'extra',      # 支援表格、定義清單等
        'codehilite', # 程式碼高亮
        'toc'         # 目錄
    ])
    return md.convert(chunk_text)

# 使用
html = render_chunk(chunk.text)
```

---

## 4. CSS 樣式建議

渲染後的 HTML 需要適當的樣式：

```css
/* 引用段落容器 */
.reference-chunk {
  background: #f5f5f5;
  border-left: 4px solid #2196F3;
  padding: 1rem;
  margin: 1rem 0;
  border-radius: 4px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* 標題 */
.reference-chunk h2 {
  color: #333;
  font-size: 1.2rem;
  margin-top: 0;
  margin-bottom: 0.5rem;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 0.3rem;
}

/* 列表 */
.reference-chunk ul {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.reference-chunk li {
  margin: 0.3rem 0;
}

/* 粗體（Metadata 標籤） */
.reference-chunk strong {
  color: #2196F3;
  font-weight: 600;
}

/* 程式碼（ID、日期等） */
.reference-chunk code {
  background: #e8f4f8;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
}

/* 連結 */
.reference-chunk a {
  color: #2196F3;
  text-decoration: none;
}

.reference-chunk a:hover {
  text-decoration: underline;
}

/* 分隔線 */
.reference-chunk hr {
  border: none;
  border-top: 1px solid #e0e0e0;
  margin: 1rem 0;
}
```

---

## 5. 完整顯示範例

### Python 後端 API

```python
from google import genai
from google.genai import types
import markdown

def query_rag(question: str) -> dict:
    """RAG 查詢並格式化結果"""

    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=question,
        config=types.GenerateContentConfig(
            tools=[types.Tool(
                file_search=types.FileSearchTool(
                    file_search_config=types.FileSearchConfig(
                        file_search_store='fileSearchStores/your-store-id'
                    )
                )
            )]
        )
    )

    # Markdown 渲染器
    md = markdown.Markdown(extensions=['extra', 'codehilite'])

    # 整理結果
    result = {
        'answer': response.text,  # 自然語言回答
        'references': []
    }

    # 處理參考文件
    if hasattr(response.candidates[0], 'grounding_metadata'):
        for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
            result['references'].append({
                'file_name': chunk.retrieval_metadata.file_name,
                'chunk_text_raw': chunk.text,  # 原始 Markdown
                'chunk_text_html': md.convert(chunk.text)  # 渲染後 HTML
            })

    return result
```

### 前端顯示 (React)

```jsx
import React from 'react';
import 'highlight.js/styles/github.css';  // 程式碼高亮樣式

function RAGResult({ result }) {
  return (
    <div className="rag-result">
      {/* AI 回答 */}
      <section className="answer-section">
        <h2>回答</h2>
        <p>{result.answer}</p>
      </section>

      {/* 參考文件 */}
      <section className="references-section">
        <h2>參考文件</h2>

        {result.references.map((ref, index) => (
          <div key={index} className="reference-item">
            {/* 檔名 */}
            <div className="file-name">
              <strong>📄 {ref.file_name}</strong>
            </div>

            {/* 引用段落（渲染後的 HTML） */}
            <div
              className="reference-chunk"
              dangerouslySetInnerHTML={{ __html: ref.chunk_text_html }}
            />
          </div>
        ))}
      </section>
    </div>
  );
}

export default RAGResult;
```

---

## 6. 安全考量

### XSS 防護

使用 `dangerouslySetInnerHTML` 時需要注意安全性：

```javascript
import DOMPurify from 'dompurify';

function SafeMarkdownRender({ markdown }) {
  const md = new MarkdownIt();
  const dirty = md.render(markdown);
  const clean = DOMPurify.sanitize(dirty);  // 清理潛在的 XSS

  return (
    <div dangerouslySetInnerHTML={{ __html: clean }} />
  );
}
```

**推薦工具**：
- **DOMPurify** (JavaScript) - 前端 HTML 清理
- **Bleach** (Python) - 後端 HTML 清理

---

## 7. 替代方案（不推薦）

### 方案 B：移除 Markdown 格式（純文字）

如果不想使用 Markdown 渲染器，可以移除格式：

```python
import re

def strip_markdown(text: str) -> str:
    """移除 Markdown 格式，保留純文字"""
    # 移除標題符號
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # 移除粗體
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # 移除程式碼標記
    text = re.sub(r'`(.*?)`', r'\1', text)
    # 移除連結 [text](url)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # 移除 emoji（選擇性）
    text = re.sub(r'[📋📄📎]', '', text)
    return text
```

**缺點**：
- ❌ 失去視覺層級結構
- ❌ 失去格式化資訊（粗體、連結等）
- ❌ 可讀性較差

**不推薦使用**，除非有特殊需求（如純文字介面、無障礙設計）。

---

## 8. 總結

### 設計決策

| 內容類型 | 格式 | 處理方式 |
|---------|------|---------|
| AI 回答 | 自然語言 | ✅ 直接顯示 |
| 參考檔名 | 語意化字串 | ✅ 直接顯示 |
| **引用段落** | **Markdown** | **⚠️ 使用 Markdown 渲染器** |

### 實作清單

- [x] 上傳格式使用 Markdown
- [x] 產生語意化檔名
- [ ] **前端整合 Markdown 渲染器**（markdown-it / react-markdown）
- [ ] **設計引用段落的 CSS 樣式**
- [ ] **實作 XSS 防護**（DOMPurify / Bleach）
- [ ] 測試 RAG 查詢與顯示流程

### 推薦工具

**前端（JavaScript/TypeScript）**：
- **Markdown 渲染**: markdown-it, react-markdown
- **XSS 防護**: DOMPurify
- **語法高亮**: highlight.js, prism.js

**後端（Python）**：
- **Markdown 渲染**: Python-Markdown, mistune
- **XSS 防護**: Bleach
- **HTML 清理**: lxml.html.clean

---

## 9. 下一步

1. 在前端專案中安裝 Markdown 渲染器
2. 建立 RAG 查詢測試頁面
3. 設計參考段落的 UI/UX
4. 實作完整的查詢 → 顯示流程
5. 測試各種查詢場景

---

**文檔版本**: 1.0
**更新日期**: 2025-11-13
**維護者**: FSC Crawler Team
