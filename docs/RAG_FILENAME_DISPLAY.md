# RAG 查詢時的檔案名稱顯示

## 問題

在 Gemini File Search RAG 查詢時,查詢結果會列出參考文件。這些參考文件會如何顯示它們的名稱?

## 回答

根據 Gemini File Search 的設計,參考文件的顯示名稱取決於上傳時設定的 `display_name` 參數。

### 目前的實作

在我們的智慧上傳器中 (`src/uploader/gemini_uploader.py`):

```python
def upload_file(self, filepath, display_name=None):
    # 顯示名稱
    if not display_name:
        display_name = filepath_obj.name  # 使用檔案名稱

    # 上傳檔案
    file_obj = self.client.files.upload(
        file=f,
        config=types.UploadFileConfig(
            display_name=display_name,  # 這就是 RAG 會顯示的名稱
            mime_type='text/markdown'
        )
    )
```

### 當前的檔案命名

由於我們對大檔案進行了自動分割,目前的檔案名稱是:

| 原始檔案 | 上傳後的顯示名稱 |
|---------|----------------|
| securities_bureau.md | securities_bureau_part1_of_4.md |
| securities_bureau.md | securities_bureau_part2_of_4.md |
| securities_bureau.md | securities_bureau_part3_of_4.md |
| securities_bureau.md | securities_bureau_part4_of_4.md |
| insurance_bureau.md | insurance_bureau_part1_of_2.md |
| insurance_bureau.md | insurance_bureau_part2_of_2.md |
| bank_bureau.md | bank_bureau_part1_of_2.md |
| bank_bureau.md | bank_bureau_part2_of_2.md |
| inspection_bureau.md | inspection_bureau.md |
| unknown.md | unknown.md |

### 問題分析

這樣的命名方式有以下問題:

1. **不具語意性**: `securities_bureau_part2_of_4.md` 無法讓使用者知道這是哪一篇公告
2. **無法溯源**: 使用者看到參考文件時,不知道是哪個日期、哪個主題的公告
3. **不易理解**: 一般使用者不會知道 `bank_bureau` 是「銀行局」

## 建議的改進方案

### 方案 1: 使用公告標題作為檔案名稱 ✅ 推薦

將每篇公告作為單獨的檔案上傳,使用公告標題作為 display_name:

```python
# 在 Markdown 格式化時,每篇公告產生獨立檔案
for item in announcements:
    filename = f"{item['id']}_{sanitize_filename(item['title'])}.md"
    # 例如: fsc_ann_20251112_0001_銀行局核准設立新銀行.md
```

**優點**:
- 使用者能直接看到公告標題
- 可以透過檔名找到原始公告
- 語意清楚

**範例顯示**:
```
參考文件:
1. fsc_ann_20251112_0001_銀行局核准設立新銀行.md
2. fsc_ann_20251110_0042_證券商內部控制規範修正.md
3. fsc_ann_20251108_0123_保險業財務報告編制準則.md
```

### 方案 2: 使用結構化的 display_name

包含更多資訊在檔名中:

```python
display_name = f"{source_name}_{date}_{title[:30]}.md"
# 例如: 銀行局_20251112_核准設立新銀行_第1篇共3篇.md
```

**優點**:
- 包含日期、來源、標題
- 如果分割,也能知道是第幾部分

**範例顯示**:
```
參考文件:
1. 銀行局_20251112_核准設立新銀行_第1篇共3篇.md
2. 證券期貨局_20251110_內部控制規範修正.md
```

### 方案 3: 使用 Metadata 而非檔名

Gemini File Search 支援在檔案內容中加入 metadata:

```markdown
---
id: fsc_ann_20251112_0001
title: 銀行局核准設立新銀行
source: 銀行局
date: 2025-11-12
url: https://www.fsc.gov.tw/...
---

# 銀行局核准設立新銀行

...內容...
```

然後檔名可以保持簡單:
```python
display_name = item['id'] + '.md'
# 例如: fsc_ann_20251112_0001.md
```

**優點**:
- Metadata 可以被 RAG 系統讀取
- 查詢時可以根據 metadata 過濾
- 檔名保持簡潔

## 實作建議

### 立即可做的改進

修改 `src/processor/markdown_formatter.py` 的 `format_by_source_split()` 方法:

```python
def format_announcement(self, item: Dict[str, Any]) -> str:
    """格式化單筆公告為 Markdown"""

    # 加入更豐富的 metadata
    md_lines = []

    # YAML front matter (Gemini 可以讀取)
    md_lines.append("---")
    md_lines.append(f"id: {item['id']}")
    md_lines.append(f"title: {item['title']}")
    md_lines.append(f"source: {source_mapping.get(item['metadata']['source'], item['metadata']['source'])}")
    md_lines.append(f"date: {item['date']}")
    if item['url']:
        md_lines.append(f"url: {item['url']}")
    md_lines.append("---")
    md_lines.append("")

    # 原有的格式化邏輯...
    md_lines.append(f"# {title}")
    # ...
```

### 長期建議

考慮改變上傳策略:

1. **每篇公告一個檔案** (推薦)
   - 不分割,每篇公告都是完整的
   - 使用語意化的檔名
   - 更易於管理和查詢

2. **使用 Gemini 的分塊功能**
   - 讓 Gemini 自動處理文件分塊
   - 我們只需要上傳完整的公告
   - Gemini 會自動建立索引和嵌入

## 範例程式碼

### 改進後的上傳方式

```python
from src.processor.markdown_formatter import MarkdownFormatter
from src.storage.jsonl_handler import JSONLHandler

# 讀取所有公告
handler = JSONLHandler()
announcements = handler.read_all('announcements')

# 格式化器
formatter = MarkdownFormatter()

# 為每篇公告建立單獨檔案
output_dir = Path('data/markdown/individual')
output_dir.mkdir(parents=True, exist_ok=True)

for item in announcements:
    # 建立語意化的檔名
    safe_title = item['title'][:50].replace('/', '_').replace('\\', '_')
    filename = f"{item['id']}_{safe_title}.md"

    # 格式化
    md_content = formatter.format_announcement(item)

    # 儲存
    filepath = output_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)

# 上傳 (每個檔案都有語意化的名稱)
uploader.upload_directory(str(output_dir))
```

### 查詢時的顯示

使用者查詢後,Gemini 會顯示類似:

```
根據您的查詢,我找到以下相關文件:

1. fsc_ann_20251112_0001_銀行局核准設立新銀行.md
2. fsc_ann_20251110_0042_證券商內部控制規範修正.md
3. fsc_ann_20251108_0123_保險業財務報告編制準則.md

這些文件包含了相關的資訊...
```

## 結論

**回答您的問題**:

被列出的參考文件會顯示我們在上傳時設定的 `display_name`。目前使用的是:
- `securities_bureau_part2_of_4.md`
- `bank_bureau_part1_of_2.md`
- 等等...

**建議改進**:

為了讓使用者更容易理解參考文件,建議:
1. 每篇公告作為獨立檔案上傳
2. 使用語意化的檔名: `{ID}_{標題}.md`
3. 在檔案內容中加入豐富的 metadata (YAML front matter)

這樣使用者在看到參考文件時,可以立即知道:
- 這是哪個單位的公告 (從標題可見)
- 什麼時候發布的 (從 ID 可見: fsc_ann_20251112)
- 主要內容是什麼 (從標題可見)

---

**相關程式碼位置**:
- Upload display_name 設定: `src/uploader/gemini_uploader.py:235`
- Markdown 格式化: `src/processor/markdown_formatter.py`
- 建議的改進位置: 新增 `format_individual_files()` 方法
