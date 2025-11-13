# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

這是一個金管會(金融監督管理委員會)爬蟲專案,用於自動化爬取公告、法規、裁罰案件,並整合到 Google Gemini File Search 進行 RAG 查詢。

**專案使用繁體中文**,所有文檔、註解、變數命名請遵循此慣例。

## 最新更新 (2025-11-13)

### ✅ 裁罰案件系統完成
- 實作裁罰案件爬蟲 (`src/crawlers/penalties.py`)
- 實作裁罰 Markdown 格式化器 (`src/processor/penalty_markdown_formatter.py`)
- 完成測試腳本與驗證

### ✅ 時效性標註機制完成
- 實作版本追蹤器 (`src/processor/version_tracker.py`)
- 修改公告格式化器，加入時效性標註
- 自動識別最新版本與過時版本
- 顯示修正歷程

### ✅ 多 Store 查詢架構設計完成
- 完整架構文檔 (`docs/multi_store_query_architecture.md`)
- 支援獨立或同時查詢公告/裁罰
- 時效性處理機制
- 參考文件數量控制方案

詳見 `docs/implementation_summary.md` 了解完整實作狀態。

## 環境設定

### 初始設定
```bash
# 建立並啟動虛擬環境
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入 GEMINI_API_KEY
```

### 常用指令

**測試爬蟲** (爬取前3頁,45筆公告):
```bash
python scripts/test_crawler.py
```

**測試 Markdown 格式化**:
```bash
python scripts/test_markdown_formatter.py
```

**測試 Gemini 上傳** (需要 API Key):
```bash
python scripts/test_gemini_uploader.py
```

## 核心架構

### 模組化設計理念

專案採用**可擴充的模組化架構**,設計目標是支援多種資料源(公告/法規/裁罰):

```
BaseFSCCrawler (抽象基類)
    ├── AnnouncementCrawler (重要公告 - 當前實作)
    ├── LawsCrawler (法規查詢 - 預留)
    └── PenaltiesCrawler (裁罰案件 - 預留)
```

### 關鍵設計模式

1. **抽象基類模式** (`src/crawlers/base.py`)
   - 提供通用的 HTTP 請求、重試邏輯、錯誤處理
   - 子類只需實作三個方法: `get_list_url()`, `parse_list_page()`, `parse_detail_page()`
   - 包含自動重試機制(`fetch_with_retry`)和請求統計

2. **JSONL 串流儲存** (`src/storage/jsonl_handler.py`)
   - 使用 JSONL 格式(每行一個 JSON)支援大量資料
   - 提供串流讀寫(`stream_read`)避免記憶體溢出
   - 支援增量更新(`get_last_item`, `append_item`)

3. **雙索引系統** (`src/storage/index_manager.py`)
   - **index.json**: 提供按日期、來源、ID 的快速查詢
   - **metadata.json**: 記錄總筆數、日期範圍、最後爬取時間
   - 增量更新時只更新新增部分,不需重建全部索引

### 資料流程

```
1. AnnouncementCrawler.crawl_all()
   └─> crawl_page() 發送 POST 請求取得列表頁
       └─> parse_list_page() 解析公告列表
           └─> fetch_detail() 爬取每筆詳細頁
               └─> parse_detail_page() 解析詳細內容

2. JSONLHandler.write_items() 儲存到 data/{source}/raw.jsonl

3. IndexManager.build_index() 或 update_index()
   └─> 產生 index.json 和 metadata.json

4. (未來) 批次上傳到 Gemini File Search Store
```

## 金管會網站特殊處理

### POST 表單分頁機制

金管會使用 JavaScript 函數 `list(page)` 進行分頁,實際是 POST 表單提交:

```python
# src/crawlers/announcements.py
form_data = {
    'id': '97',                          # 頁面 ID
    'contentid': '97',
    'parentpath': '0,2',
    'mcustomize': 'multimessage_list.jsp',
    'page': str(page),                   # 頁碼 (字串)
    'pagesize': '15',                    # 每頁筆數
}
response = session.post(url, data=form_data)
```

### HTML 解析注意事項

1. **列表結構**: 使用 `<li role="row">` 而非 `<table>`
2. **跳過表頭**: `rows[1:]` 第一個 `li[role="row"]` 是表頭
3. **相對 URL**: 需使用 `urljoin(base_url, href)` 轉換完整 URL
4. **SSL 憑證**: 金管會憑證有問題,需設定 `session.verify = False`

### CSS 選擇器

```python
rows = soup.select('li[role="row"]')[1:]  # 跳過表頭
for row in rows:
    no = row.select_one('span.no')        # 編號
    date = row.select_one('span.date')    # 日期
    unit = row.select_one('span.unit')    # 來源單位
    link = row.select_one('span.title > a')  # 標題連結
```

## 配置系統

### config/sources.yaml

定義所有資料源的配置和映射表:

- `sources`: 各資料源的 URL 和參數
- `source_units`: 中文單位名稱 → 標準化代碼映射
- `announcement_categories`: 公告類型關鍵字映射

### config/crawler.yaml

爬蟲行為配置:
- `http`: 請求參數 (timeout, interval, retries)
- `storage`: 儲存格式設定
- `gemini`: Gemini API 和 chunking 配置

## 增量更新機制

```python
from src.storage.jsonl_handler import JSONLHandler
from src.storage.index_manager import IndexManager

# 1. 讀取上次爬取日期
metadata = index_mgr.load_metadata('announcements')
last_date = metadata['last_crawl_date']

# 2. 只爬取新資料
new_items = crawler.crawl_since(last_date)

# 3. 追加儲存 (append mode)
storage.write_items('announcements', new_items, mode='a')

# 4. 更新索引 (只更新新增部分)
index_mgr.update_index('announcements', new_items)
```

## 資料結構

### 爬取原始資料格式

```python
{
    'id': 'fsc_ann_20251112_0001',       # 自動生成
    'page': 1,
    'list_index': '1',
    'date': '2025-11-12',
    'source_raw': '保險局',               # 原始來源名稱
    'title': '修正「財產保險業經營...」',
    'detail_url': 'https://...',
    'content': {
        'text': '...',                    # 純文字
        'html': '...'                     # HTML (截短)
    },
    'attachments': [                      # 附件列表
        {'name': '...', 'url': '...', 'type': 'pdf'}
    ],
    'metadata': {
        'announcement_number': '金管證發字第...號',
        'category': 'amendment',          # 標準化類型
        'source': 'insurance_bureau'      # 標準化來源
    }
}
```

## 常見問題與解決方案

### 問題: 爬蟲返回 0 筆資料

1. 檢查是否跳過表頭: `rows[1:]`
2. 檢查 POST 參數是否正確
3. 使用 `scripts/debug_post.py` 測試單獨的 POST 請求
4. 檢查 `link_elem` 選擇器: `span.title > a`

### 問題: SSL 憑證錯誤

金管會憑證缺少 Subject Key Identifier,需要:
```python
session.verify = False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

### 問題: 記憶體不足 (大量資料)

使用串流讀取:
```python
for item in storage.stream_read('announcements'):
    process(item)  # 逐筆處理
```

## 擴充新資料源

新增爬蟲步驟:

1. 在 `config/sources.yaml` 新增資料源配置
2. 建立 `src/crawlers/new_source.py` 繼承 `BaseFSCCrawler`
3. 實作三個必要方法:
   - `get_list_url(page)`: URL 生成邏輯
   - `parse_list_page(html)`: 列表頁解析
   - `parse_detail_page(html, list_item)`: 詳細頁解析
4. 資料自動儲存到 `data/new_source/`
5. 索引自動建立

## 最新更新 (2025-11-13)

### ✅ 附件自動下載和上傳功能

已完成附件自動下載和上傳功能，大幅提升 Gemini File Search 查詢效果。

**實作內容**：
- `config/crawler.yaml` - 新增 `attachments` 配置區塊
- `src/crawlers/announcements.py` - 新增 `_download_attachments()` 方法
- `src/uploader/gemini_uploader.py` - 新增 `upload_announcement_with_attachments()` 方法

**核心功能**：
- 自動下載公告附件（PDF、DOC、DOCX）
- 智慧型檔案類型識別（處理 `pdf&flag=doc` 等 URL 參數）
- 指數退避重試機制（最多 3 次）
- 檔案大小限制（預設 50 MB）
- 串流下載支援大檔案
- Markdown + PDF 同時上傳到同一個 Gemini Store

**重要性**：
- 修正條文對照表（新舊條文並列）包含在附件中
- 對於理解「改了什麼」至關重要
- Gemini File Search 原生支援 PDF，可自動提取和索引
- 查詢時 Gemini 會同時檢索公告正文和附件內容

**配置範例**：
```yaml
# config/crawler.yaml
attachments:
  download: true
  types: ['pdf', 'doc', 'docx']
  max_size_mb: 50
  save_path: "data/attachments"
  retry_on_error: true
  max_retries: 3
```

**使用範例**：
```python
# 上傳公告及附件
from src.uploader.gemini_uploader import GeminiUploader

uploader = GeminiUploader(api_key='...', store_name='fsc-announcements')
result = uploader.upload_announcement_with_attachments(
    markdown_path='data/markdown/individual/fsc_ann_20251112_0001.md',
    attachments_dir=None,  # 自動從文件 ID 推導
    delay=2.0
)
```

**測試與部署**：
- 測試腳本：`scripts/test_attachment_download.py`
- 部署指南：`docs/deployment_with_attachments.md`
- 策略分析：`docs/attachment_handling_strategy.md`

**檔案結構**：
```
data/
├── announcements/
│   └── raw.jsonl              # 包含附件元資料
└── attachments/
    └── announcements/
        └── fsc_ann_YYYYMMDD_NNNN/
            ├── attachment_1.pdf  # 修正說明
            ├── attachment_2.pdf  # 對照表
            └── attachment_3.pdf  # 修正條文
```

---

## 待實作功能

- [ ] 法規查詢爬蟲 (`src/crawlers/laws.py`)
- [ ] 裁罰案件爬蟲 (`src/crawlers/penalties.py`)
- [ ] RAG 查詢介面
- [ ] 文件關係偵測（甲文件取代乙文件）
- [ ] 時效性排序（Markdown 標註 + Prompt Engineering）

## 除錯工具

**查看 JSONL 內容**:
```python
from src.storage.jsonl_handler import JSONLHandler
storage = JSONLHandler()

# 讀取所有
items = storage.read_all('announcements')

# 串流讀取 (大檔案)
for item in storage.stream_read('announcements'):
    print(item['title'])

# 取得最後一筆
last = storage.get_last_item('announcements')
```

**查詢索引**:
```python
from src.storage.index_manager import IndexManager
index_mgr = IndexManager()

# 取得特定日期的行號
line_numbers = index_mgr.get_items_by_date('announcements', '2025-11-12')

# 取得特定來源的統計
stats = index_mgr.get_items_by_source_unit('announcements', 'bank_bureau')
```

## 日誌系統

專案使用 `loguru` 進行日誌記錄:

```python
from src.utils.logger import setup_logger

logger = setup_logger(level="INFO")  # DEBUG, INFO, WARNING, ERROR
```

日誌檔案位置: `logs/fsc_crawler.log`

## 重要參考文件

- **SPEC.md**: 完整的專案規格設計文件
- **FINDINGS.md**: 金管會網站結構分析結果
- **README.md**: 使用說明和快速開始
