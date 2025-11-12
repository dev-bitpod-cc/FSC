# 檔案分割策略對比說明

## 您的問題

> "分割成3個檔案,上傳後以3個檔案存在?不管選用那個檔案名稱方案,會有3個同名檔案?"

**答案**: 是的!您完全指出了問題所在。

## 問題示例

### ❌ 錯誤做法:按來源合併後分割

**目前的做法** (`format_by_source` + 自動分割):

1. 將所有證券期貨局的公告合併成 `securities_bureau.md` (包含 67 篇不同公告)
2. 因為檔案太大 (340 KB),自動分割成:
   - `securities_bureau_part1_of_4.md` (包含第 1-22 篇公告)
   - `securities_bureau_part2_of_4.md` (包含第 23-44 篇公告)
   - `securities_bureau_part3_of_4.md` (包含第 45-66 篇公告)
   - `securities_bureau_part4_of_4.md` (包含第 67 篇公告)

**問題**:

```
參考文件:
1. securities_bureau_part2_of_4.md  ❌ 使用者不知道裡面有什麼
2. securities_bureau_part3_of_4.md  ❌ 使用者不知道裡面有什麼
3. bank_bureau_part1_of_2.md        ❌ 使用者不知道裡面有什麼
```

- ❌ 檔名沒有語意
- ❌ 每個檔案包含 22 篇不同的公告
- ❌ 使用者無法從檔名知道內容
- ❌ 無法溯源到具體是哪篇公告

## ✅ 正確做法:每篇公告獨立檔案

### 使用新的 `format_individual_files()` 方法

```python
from src.processor.markdown_formatter import BatchMarkdownFormatter
from src.storage.jsonl_handler import JSONLHandler

handler = JSONLHandler()
formatter = BatchMarkdownFormatter()
formatter.handler = handler

# 每篇公告建立獨立檔案
result = formatter.format_individual_files(
    data_type='announcements',
    output_dir='data/markdown/individual'
)
```

**結果**:

```
共建立 150 個檔案,每個檔案對應一篇公告:

fsc_ann_20251112_0001_保險局_修正「財產保險業經營傷害保險及健康保險業務管理辦法」.md
fsc_ann_20251112_0002_保險局_訂定「規範財產保險業得以取具足資證明要保人投保意願之相關證據取代要保人及被保險人於要保書簽章之業務」.md
fsc_ann_20251112_0003_銀行局_指定中華民國電子支付商業同業公會為外籍移工國外小額匯兌業務管理辦法第二十一條所稱之同業公會.md
...
```

**優點**:

```
RAG 查詢結果:
1. fsc_ann_20251112_0001_保險局_修正「財產保險業經營傷害保險及健康保險業務管理辦法」.md  ✅ 清楚
2. fsc_ann_20251110_0042_證券期貨局_內部控制規範修正.md  ✅ 清楚
3. fsc_ann_20251108_0123_保險局_財務報告編制準則.md  ✅ 清楚
```

- ✅ 檔名包含公告 ID
- ✅ 檔名包含來源單位 (中文)
- ✅ 檔名包含公告標題
- ✅ 每個檔案 = 一篇公告
- ✅ 使用者可以直接看出內容
- ✅ 不需要分割 (每篇公告檔案都很小)

## 對比表

| 項目 | 按來源合併 + 自動分割 | 每篇公告獨立檔案 |
|-----|---------------------|----------------|
| 檔案數量 | 10 個 (分割後) | 150 個 (原始公告數) |
| 檔名語意性 | ❌ 無意義 | ✅ 包含標題、來源、ID |
| 檔案內容 | ❌ 混合 22 篇不同公告 | ✅ 每個檔案一篇公告 |
| RAG 可讀性 | ❌ 使用者看不懂 | ✅ 使用者一目了然 |
| 檔案大小 | 🔶 100-130 KB (需分割) | ✅ 1-10 KB (不需分割) |
| 管理難度 | ❌ 複雜 (需追蹤哪些公告在哪個分割檔) | ✅ 簡單 (一對一映射) |

## 實際範例

### 按來源合併後分割 ❌

```
securities_bureau_part2_of_4.md 包含:
- 第 23 篇: 關於證券商內部控制的規定
- 第 24 篇: 關於期貨交易的新規範
- 第 25 篇: 關於財務報告的修正
- ...
- 第 44 篇: 關於投資人保護的措施

使用者看到檔名 "securities_bureau_part2_of_4.md"
→ 完全不知道裡面有什麼! 🤔❓
```

### 每篇公告獨立檔案 ✅

```
每個檔案:
- fsc_ann_20251110_0042_證券期貨局_證券商內部控制規範修正.md
- fsc_ann_20251109_0015_證券期貨局_期貨交易新規範發布.md
- fsc_ann_20251108_0089_證券期貨局_財務報告編制準則修正.md

使用者看到檔名 "證券商內部控制規範修正"
→ 立刻知道內容! ✅👍
```

## 檔案大小對比

### 按來源合併

| 檔案 | 大小 | 包含公告數 | 是否需要分割 |
|-----|------|-----------|------------|
| securities_bureau.md | 340 KB | 67 篇 | ✅ 需要 (分成 4 個檔) |
| insurance_bureau.md | 129 KB | 42 篇 | ✅ 需要 (分成 2 個檔) |
| bank_bureau.md | 108 KB | 33 篇 | ✅ 需要 (分成 2 個檔) |

### 每篇公告獨立

| 檔案類型 | 平均大小 | 包含公告數 | 是否需要分割 |
|---------|---------|-----------|------------|
| 單篇公告 .md | 1-10 KB | 1 篇 | ❌ 不需要! |

**總結**: 每篇公告獨立檔案後,檔案都很小 (1-10 KB),完全不需要分割!

## 上傳策略建議

### 推薦流程

1. **格式化為獨立檔案**:
```bash
python scripts/test_individual_format.py
# 產生 150 個獨立的 .md 檔案
```

2. **直接上傳** (不需要分割):
```python
uploader = GeminiUploader(
    max_file_size_kb=100,  # 單篇公告都小於 100 KB,不會觸發分割
    auto_split=False        # 可以關閉自動分割
)

stats = uploader.upload_directory('data/markdown/individual')
```

3. **結果**:
- 上傳 150 個檔案
- 每個檔案對應一篇公告
- 檔名都是語意化的
- RAG 查詢時使用者能看懂

## 技術細節

### 檔名格式

```
{ID}_{來源}_{標題}.md

範例:
fsc_ann_20251112_0001_保險局_修正「財產保險業經營傷害保險及健康保險業務管理辦法」.md

組成:
- ID: fsc_ann_20251112_0001 (唯一識別碼)
- 來源: 保險局 (中文,使用者看得懂)
- 標題: 修正「財產保險業經營傷害保險及健康保險業務管理辦法」 (前 50 字)
```

### 程式碼位置

- **新方法**: `src/processor/markdown_formatter.py:320-416` (`format_individual_files`)
- **測試腳本**: `scripts/test_individual_format.py`
- **輸出目錄**: `data/markdown/individual/`

## 總結

回答您的問題:

**Q: 分割成3個檔案,上傳後以3個檔案存在?**
A: 是的,之前的做法會產生 3 個檔案 (例如 `securities_bureau_part1_of_3.md`)

**Q: 不管選用那個檔案名稱方案,會有3個同名檔案?**
A: 不是同名,而是會有 3 個類似名稱的檔案 (`partX_of_3`),但每個檔案都包含不同的 22 篇公告,使用者無法從檔名知道內容。

**解決方案**:
改用「每篇公告獨立檔案」的策略,就不會有這個問題了!每個檔案都有獨特且有意義的檔名,對應到一篇公告。

---

**下一步行動**:

1. 執行 `python scripts/test_individual_format.py` 產生獨立檔案
2. 使用新的檔案目錄 `data/markdown/individual/` 上傳
3. 享受清楚明瞭的 RAG 查詢結果! 🎉
