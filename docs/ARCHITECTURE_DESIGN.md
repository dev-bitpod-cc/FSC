# 金管會爬蟲架構設計 - 完整說明

## 您的三個關鍵問題

### 1️⃣ 既然上傳時是以單篇公告為一個檔案單元,那就不需要智慧分割了

**✅ 正確!** 應該簡化上傳器,移除分割功能。

### 2️⃣ 爬文資料的儲存,要能夠新增爬文,也要能夠用另一個 Gemini API Key 上傳到另一個 File Search Store 去重建索引

**✅ 目前已支援!** 設計說明如下。

### 3️⃣ 這些被分出來上傳的單篇公告 md,上傳結束後會刪除嗎?

**💡 關鍵設計決策!** 需要決定儲存策略。

---

## 建議的完整架構

### 資料流程圖

```
┌─────────────────┐
│   爬蟲抓取資料    │
│  (150 筆公告)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  儲存為 JSONL    │ ← 主要儲存格式 (永久保存)
│ raw.jsonl       │    每行一筆 JSON
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  建立索引        │
│  index.json     │ ← 快速查詢用
│  metadata.json  │
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌─────────────────┐   ┌─────────────────┐
│ 產生 Markdown   │   │  增量爬取       │
│ (按需產生)      │   │ (追加到 JSONL)  │
│ 暫存檔案        │   └─────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 上傳到 Gemini   │
│ (每篇公告獨立)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 上傳完成後      │
│ 刪除暫存 MD 檔  │ ← 節省磁碟空間
└─────────────────┘
```

---

## 詳細設計

### 儲存策略

#### 方案 A: JSONL 為主儲存,Markdown 為暫存 ✅ 推薦

**設計理念**:
- **JSONL** = 唯一真相來源 (Source of Truth)
- **Markdown** = 暫存格式,用於上傳後即刪除
- **Gemini** = 查詢索引,隨時可從 JSONL 重建

**優點**:
- ✅ 避免 7,500 個 Markdown 檔案
- ✅ 節省磁碟空間
- ✅ JSONL 易於增量更新
- ✅ 可隨時從 JSONL 重新產生 Markdown

**缺點**:
- ⚠️ 需要時才產生 Markdown (多一個步驟)

**檔案結構**:
```
data/
├── announcements/
│   ├── raw.jsonl           # 主儲存 (7,500 行)
│   ├── index.json          # 索引
│   └── metadata.json       # 元資料
├── temp_markdown/          # 暫存目錄 (上傳後刪除)
│   ├── fsc_ann_*.md       # 暫存的 Markdown 檔案
│   └── .gitignore         # 不納入版控
└── upload_manifest.json    # 上傳記錄
```

#### 方案 B: JSONL + Markdown 雙儲存

**設計理念**:
- 同時保留 JSONL 和 Markdown
- Markdown 作為永久儲存

**優點**:
- ✅ Markdown 可直接閱讀
- ✅ 不需要重新產生

**缺點**:
- ❌ 7,500 個 Markdown 檔案
- ❌ 列舉檔案時速度慢
- ❌ Git 操作慢 (如果納入版控)
- ❌ 磁碟空間大 (~75 MB)
- ❌ 增量更新時要同步兩種格式

---

## 推薦的實作方案 (方案 A)

### 工作流程

#### 1. 爬取資料 (增量支援)

```python
from src.crawlers.announcements import AnnouncementCrawler

crawler = AnnouncementCrawler(config)

# 首次爬取
items = crawler.crawl_all(start_page=1, end_page=500)
storage.write_items('announcements', items)

# 增量爬取 (只爬最新的)
new_items = crawler.crawl_latest(days=7)  # 最近 7 天
storage.append_items('announcements', new_items)
```

#### 2. 產生暫存 Markdown

```python
from src.processor.markdown_formatter import BatchMarkdownFormatter

formatter = BatchMarkdownFormatter()

# 產生到暫存目錄
result = formatter.format_individual_files(
    data_type='announcements',
    output_dir='data/temp_markdown',  # 暫存目錄
    cleanup=False  # 先不清理,上傳後再清
)

print(f"產生 {result['created_files']} 個暫存 Markdown 檔案")
```

#### 3. 上傳到 Gemini (支援多個 Store)

```python
from src.uploader.gemini_uploader import GeminiUploader

# Store 1: 生產環境
uploader_prod = GeminiUploader(
    api_key='prod_api_key',
    store_name='fsc-announcements-prod'
)

stats = uploader_prod.upload_directory(
    'data/temp_markdown',
    auto_split=False,  # 不需要分割
    skip_existing=True
)

# Store 2: 測試環境
uploader_test = GeminiUploader(
    api_key='test_api_key',
    store_name='fsc-announcements-test'
)

stats = uploader_test.upload_directory(
    'data/temp_markdown',
    auto_split=False,
    skip_existing=False  # 測試環境全部重新上傳
)
```

#### 4. 清理暫存檔案

```python
import shutil
from pathlib import Path

# 上傳完成後刪除暫存目錄
temp_dir = Path('data/temp_markdown')
if temp_dir.exists():
    shutil.rmtree(temp_dir)
    print(f"已清理暫存目錄: {temp_dir}")
```

#### 5. 完整的上傳腳本

```python
# scripts/upload_to_gemini.py
def upload_to_gemini(
    api_key: str,
    store_name: str,
    force_regenerate: bool = False
):
    """
    完整的上傳流程

    Args:
        api_key: Gemini API Key
        store_name: Store 名稱
        force_regenerate: 強制重新產生 Markdown
    """
    temp_dir = Path('data/temp_markdown')

    try:
        # 1. 檢查是否需要產生 Markdown
        if force_regenerate or not temp_dir.exists():
            logger.info("產生暫存 Markdown 檔案...")
            formatter = BatchMarkdownFormatter()
            result = formatter.format_individual_files(
                data_type='announcements',
                output_dir=str(temp_dir)
            )
            logger.info(f"產生 {result['created_files']} 個檔案")
        else:
            logger.info("使用現有的暫存 Markdown 檔案")

        # 2. 上傳到 Gemini
        logger.info(f"上傳到 Store: {store_name}")
        uploader = GeminiUploader(
            api_key=api_key,
            store_name=store_name,
            max_retries=3
        )

        stats = uploader.upload_directory(
            str(temp_dir),
            skip_existing=True,
            auto_split=False  # 不需要分割
        )

        logger.info(f"上傳完成: {stats['uploaded_files']}/{stats['total_files']}")

        # 3. 驗證完整性
        report = uploader.verify_upload_completeness()
        if report['failed'] > 0:
            logger.warning(f"有 {report['failed']} 個檔案上傳失敗")
            return False

        return True

    finally:
        # 4. 清理暫存檔案
        if temp_dir.exists():
            logger.info("清理暫存檔案...")
            shutil.rmtree(temp_dir)
            logger.info("清理完成")
```

---

## 效能分析

### 檔案數量對比

| 情境 | JSONL | Markdown | 總檔案數 |
|-----|-------|----------|---------|
| 方案 A (推薦) | 1 個 | 0 個 (暫存) | **1 個** |
| 方案 B | 1 個 | 7,500 個 | **7,501 個** |

### 列舉檔案速度測試

```python
import time
from pathlib import Path

# 測試列舉 7,500 個檔案
start = time.time()
files = list(Path('data/temp_markdown').glob('*.md'))
elapsed = time.time() - start

print(f"列舉 {len(files)} 個檔案: {elapsed:.2f} 秒")
# 預期: macOS ~0.05 秒, Windows ~0.2 秒
```

**結論**: 7,500 個檔案的列舉速度可接受,但:
- ❌ Git 操作會變慢 (git status, git add)
- ❌ 備份時間變長
- ❌ 磁碟空間浪費

---

## 增量更新設計

### JSONL 增量寫入

```python
class JSONLHandler:
    def append_items(self, data_type: str, new_items: List[Dict]) -> int:
        """
        追加新資料到 JSONL (增量更新)

        Args:
            data_type: 資料類型
            new_items: 新增的資料列表

        Returns:
            追加的筆數
        """
        filepath = self.get_filepath(data_type)

        # 檢查重複 (透過 ID)
        existing_ids = self._get_existing_ids(data_type)

        unique_items = [
            item for item in new_items
            if item.get('id') not in existing_ids
        ]

        # 追加寫入
        with open(filepath, 'a', encoding='utf-8') as f:
            for item in unique_items:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        logger.info(f"追加 {len(unique_items)} 筆新資料")

        # 更新索引
        self.index_manager.update_index(data_type, unique_items)

        return len(unique_items)
```

### Gemini 增量上傳

```python
# 只上傳新增的公告
def upload_new_announcements(uploader, since_date):
    """
    只上傳指定日期之後的新公告

    Args:
        uploader: GeminiUploader 實例
        since_date: 起始日期 (例如: '2025-11-01')
    """
    # 1. 從 JSONL 讀取新公告
    handler = JSONLHandler()
    all_items = handler.read_all('announcements')
    new_items = [
        item for item in all_items
        if item.get('date', '') >= since_date
    ]

    logger.info(f"找到 {len(new_items)} 筆新公告")

    # 2. 產生新公告的 Markdown (暫存)
    temp_dir = Path('data/temp_markdown_new')
    formatter = BatchMarkdownFormatter()

    for item in new_items:
        md_content = formatter.format_announcement(item)
        filename = f"{item['id']}_{item['title'][:30]}.md"
        filepath = temp_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)

    # 3. 上傳 (skip_existing=True 會自動跳過已上傳的)
    stats = uploader.upload_directory(
        str(temp_dir),
        skip_existing=True
    )

    # 4. 清理
    shutil.rmtree(temp_dir)

    return stats
```

---

## 重建索引 (切換 Store)

### 使用情境

1. 切換到新的 API Key
2. 建立測試環境的 Store
3. 災難恢復 (重建整個 Store)

### 實作

```python
def rebuild_store(
    api_key: str,
    store_name: str,
    delete_old_store: bool = False
):
    """
    從 JSONL 重建整個 Gemini Store

    Args:
        api_key: 新的 API Key
        store_name: 新的 Store 名稱
        delete_old_store: 是否刪除舊的 Store
    """
    uploader = GeminiUploader(
        api_key=api_key,
        store_name=store_name
    )

    # 刪除舊 Store (選擇性)
    if delete_old_store:
        try:
            uploader.delete_store()
            logger.info("已刪除舊 Store")
        except:
            pass

    # 從 JSONL 重建
    temp_dir = Path('data/temp_markdown_rebuild')

    try:
        # 1. 產生所有 Markdown
        formatter = BatchMarkdownFormatter()
        result = formatter.format_individual_files(
            data_type='announcements',
            output_dir=str(temp_dir)
        )

        logger.info(f"產生 {result['created_files']} 個檔案")

        # 2. 全部上傳到新 Store
        stats = uploader.upload_directory(
            str(temp_dir),
            skip_existing=False,  # 全部重新上傳
            auto_split=False
        )

        logger.info(f"重建完成: {stats['uploaded_files']} 個檔案")

        return stats

    finally:
        # 3. 清理暫存
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
```

---

## 簡化後的 GeminiUploader

### 移除不必要的功能

```python
class GeminiUploader:
    """簡化版 Gemini 上傳器 (針對個別檔案上傳)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        store_name: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        初始化上傳器

        Args:
            api_key: Gemini API Key
            store_name: Store 名稱
            max_retries: 最大重試次數
            retry_delay: 重試延遲基數
        """
        # 移除 max_file_size_kb, max_items_per_split (不再需要)
        # 移除 temp_dir, split_files (不再需要分割)

        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # ... 其他初始化
```

---

## 最終建議

### ✅ 採用方案 A

1. **主儲存**: JSONL (`data/announcements/raw.jsonl`)
2. **暫存**: Markdown 檔案 (`data/temp_markdown/*.md`)
3. **上傳**: 從暫存目錄上傳
4. **清理**: 上傳後刪除暫存 Markdown
5. **重建**: 隨時可從 JSONL 重新產生並上傳

### 優點總結

- ✅ 只保留 1 個 JSONL 檔案 (7,500 行)
- ✅ 避免 7,500 個 Markdown 檔案
- ✅ 節省磁碟空間 (~75 MB)
- ✅ Git 操作快速
- ✅ 支援增量更新
- ✅ 支援多 Store (不同 API Key)
- ✅ 可隨時重建索引

### 實作清單

- [ ] 簡化 `GeminiUploader` (移除分割功能)
- [ ] 實作 `JSONLHandler.append_items()` (增量寫入)
- [ ] 實作 `upload_to_gemini.py` (完整上傳流程)
- [ ] 實作 `rebuild_store.py` (重建 Store)
- [ ] 更新文檔

---

## 回答您的問題

### Q1: 不需要智慧分割了?
**A**: ✅ 正確!應該移除分割功能,簡化上傳器。

### Q2: 能否用另一個 API Key 重建索引?
**A**: ✅ 可以!從 JSONL 重新產生 Markdown → 上傳到新 Store → 清理暫存。

### Q3: 上傳後會刪除 MD 檔案嗎?
**A**: ✅ 建議刪除!Markdown 是暫存格式,JSONL 才是主儲存。避免 7,500 個檔案拖垮速度。
