# 金管會爬蟲專案

自動化爬取金融監督管理委員會(金管會)的公告、法規、裁罰案件,並整合到 Google Gemini File Search 進行 RAG 查詢。

## 📋 專案狀態

- ✅ 專案架構建立完成
- ✅ 核心模組實作完成 (BaseCrawler, JSONL Storage, Index Manager)
- ✅ 重要公告爬蟲實作完成 (支援 POST 分頁)
- ✅ Markdown 格式化器完成（支援獨立檔案格式）
- ✅ Gemini 上傳器完成（重試、驗證、斷點續傳）
- ✅ 增量更新支援（自動去重）
- ✅ 測試成功 (150 筆公告資料上傳到 Gemini)
- ✅ 準備就緒，可進行生產部署

## 🚀 快速開始

### 環境需求

- Python 3.9+
- pip

### 安裝步驟

1. **建立虛擬環境**

```bash
# 建立虛擬環境
python3 -m venv venv

# 啟動虛擬環境
# macOS/Linux:
source venv/bin/activate

# Windows:
# venv\Scripts\activate
```

2. **安裝依賴套件**

```bash
pip install -r requirements.txt
```

3. **設定環境變數**

```bash
# 複製環境變數範例檔
cp .env.example .env

# 編輯 .env 並填入你的 Gemini API Key
# GEMINI_API_KEY=your_api_key_here
```

### 測試爬蟲

```bash
# 測試爬取 3 頁 (45 筆公告)
python scripts/test_crawler.py
```

### 測試 Markdown 格式化

```bash
# 將 JSONL 轉換為 Markdown
python scripts/test_markdown_formatter.py
```

### 生產環境部署 (需要 API Key)

```bash
# 全量爬取與上傳（~7,500 筆公告）
# 提示：背景執行請使用 nohup，詳見下方說明
python scripts/run_full_production.py

# 或使用完整上傳腳本（更多選項）
python scripts/upload_to_gemini_complete.py --mode upload

# 查看即時 log
tail -f logs/fsc_crawler.log
```

## 📁 專案結構

```
fsc-crawler/
├── README.md                  # 本文件
├── SPEC.md                    # 專案規格文件
├── FINDINGS.md                # 網站探索發現 (執行 explore_website.py 後產生)
├── requirements.txt           # Python 依賴
├── .env.example               # 環境變數範例
├── .gitignore
│
├── config/
│   ├── sources.yaml          # 資料源配置
│   └── crawler.yaml          # 爬蟲配置
│
├── src/
│   ├── crawlers/                  # 爬蟲模組
│   │   ├── base.py                # 抽象基類 ✅
│   │   ├── announcements.py       # 重要公告爬蟲 ✅
│   │   ├── laws.py                # 法規爬蟲 (預留)
│   │   └── penalties.py           # 裁罰爬蟲 (預留)
│   │
│   ├── processor/                 # 資料處理
│   │   └── markdown_formatter.py  # Markdown 格式化器 ✅
│   │
│   ├── storage/                   # 儲存系統
│   │   ├── jsonl_handler.py       # JSONL 操作 ✅
│   │   └── index_manager.py       # 索引管理 ✅
│   │
│   ├── uploader/                  # Gemini 上傳
│   │   └── gemini_uploader.py     # Gemini 上傳器 ✅
│   │
│   └── utils/                     # 工具
│       ├── logger.py              # 日誌設定 ✅
│       ├── config_loader.py       # 配置載入 ✅
│       └── helpers.py             # 輔助函數 ✅
│
├── data/                     # 資料目錄 (gitignore)
│   ├── announcements/        # 重要公告
│   ├── laws/                 # 法規 (預留)
│   └── penalties/            # 裁罰 (預留)
│
├── logs/                     # 日誌檔案
│
└── scripts/                        # 執行腳本
    ├── test_crawler.py             # 爬蟲測試 ✅
    ├── test_markdown_formatter.py  # Markdown 測試 ✅
    └── test_gemini_uploader.py     # Gemini 上傳測試 ✅
```

## 🎯 功能特色

### 已完成

- ✅ **模組化架構**: 支援多種資料源 (公告/法規/裁罰)
- ✅ **BaseCrawler**: 抽象基類,提供重試、錯誤處理、統計等通用功能
- ✅ **JSONL 儲存**: 高效的串流讀寫,支援大量資料
- ✅ **索引系統**: 提供日期、來源、ID 的快速查詢
- ✅ **增量更新**: 支援只爬取新增的資料
- ✅ **AnnouncementCrawler**: 重要公告爬蟲 (POST 分頁)
- ✅ **Markdown 格式化**: 轉換為適合 Gemini 的格式
- ✅ **智慧上傳器**: 自動分割、重試、驗證、清理的完整解決方案
  - 自動偵測並分割大檔案 (預設 100 KB 以上)
  - Exponential backoff 重試機制 (最多 3 次)
  - 上傳狀態追蹤與記錄 (manifest.json)
  - 完整性驗證報告
  - 自動清理暫存分割檔案
- ✅ **唯一 ID 生成**: 格式 `fsc_ann_YYYYMMDD_NNNN`
- ✅ **Brotli 解壓縮**: 處理金管會伺服器回應

### 待開發

- ⏳ **完整爬取**: 爬取全部 ~7,500 筆公告
- ⏳ **RAG 查詢**: 自然語言查詢介面
- ⏳ **法規爬蟲**: LawsCrawler 實作
- ⏳ **裁罰爬蟲**: PenaltiesCrawler 實作

## 📚 資料儲存設計

### JSONL 格式

每筆資料儲存為一行 JSON,方便串流處理和增量更新:

```jsonl
{"id": "fsc_ann_20251112_001", "date": "2025-11-12", "source": "bank_bureau", "title": "...", ...}
{"id": "fsc_ann_20251112_002", "date": "2025-11-12", "source": "securities_bureau", "title": "...", ...}
```

### 索引結構

提供快速查詢能力:

```json
{
  "by_date": {
    "2025-11-12": {"line_numbers": [1, 2], "count": 2}
  },
  "by_source": {
    "bank_bureau": {"count": 1200, "latest_line": 5600}
  },
  "by_id": {
    "fsc_ann_20251112_001": {"line": 1, "date": "2025-11-12"}
  }
}
```

### Metadata

記錄爬取狀態:

```json
{
  "data_type": "announcements",
  "total_count": 7499,
  "last_crawl_date": "2025-11-12",
  "date_range": ["2010-01-01", "2025-11-12"]
}
```

## 🔧 配置說明

### 爬蟲配置 (config/crawler.yaml)

```yaml
http:
  timeout: 30
  request_interval: 1.0  # 每秒 1 個請求 (中速)
  max_retries: 3

storage:
  format: "jsonl"
  enable_index: true

gemini:
  batch_size: 100
  chunking:
    max_tokens_per_chunk: 800
    max_overlap_tokens: 100
```

### 資料源配置 (config/sources.yaml)

定義所有資料源的 URL 和參數。

## 📖 使用範例

### 上傳到 Gemini File Search

```python
from src.uploader.gemini_uploader import GeminiUploader

# 初始化上傳器
uploader = GeminiUploader(
    api_key='your_api_key',
    store_name='fsc-announcements',
    max_retries=3,             # 失敗時最多重試 3 次
    retry_delay=2.0            # 重試延遲基數 (exponential backoff)
)

# 上傳整個目錄
stats = uploader.upload_directory(
    directory='data/markdown/individual',
    pattern='*.md',
    delay=1.0,              # 每次上傳間隔 1 秒
    skip_existing=True      # 跳過已上傳的檔案（斷點續傳）
)

# 驗證上傳完整性
report = uploader.verify_upload_completeness()
print(f"成功: {report['successful']}/{report['total']}")
print(f"失敗: {report['failed']}/{report['total']}")

# 取得失敗的上傳
failed = uploader.get_failed_uploads()
for item in failed:
    print(f"失敗檔案: {item['filepath']}")
    print(f"錯誤: {item['error']}")
```

**注意**: 每篇公告已格式化為獨立 Markdown 檔案（1-10 KB），無需分割。

### 爬取重要公告

```python
from src.crawlers.announcements import AnnouncementCrawler
from src.storage.jsonl_handler import JSONLHandler
from src.storage.index_manager import IndexManager

# 初始化
crawler = AnnouncementCrawler(config)
storage = JSONLHandler()
index_mgr = IndexManager()

# 爬取前 100 筆
items = crawler.crawl_all(start_page=1, end_page=7)

# 儲存
storage.write_items('announcements', items)

# 建立索引
index_mgr.build_index('announcements', items)
```

### 增量更新 (開發中)

```python
# 取得上次爬取日期
metadata = index_mgr.load_metadata('announcements')
last_date = metadata['last_crawl_date']

# 只爬取新資料
new_items = crawler.crawl_since(last_date)

# 追加儲存
storage.write_items('announcements', new_items, mode='a')

# 更新索引
index_mgr.update_index('announcements', new_items)
```

## 🧪 測試

```bash
# 執行網站探索測試
python scripts/explore_website.py

# (待實作) 執行 100 筆測試
python scripts/test_small.py

# (待實作) 執行完整爬取
python scripts/run_crawler.py
```

## 📝 開發進度

- [x] 專案架構設計
- [x] BaseCrawler 實作
- [x] JSONL 儲存系統
- [x] 索引管理系統
- [x] 網站分析 (POST 分頁機制)
- [x] AnnouncementCrawler 實作
- [x] Markdown 格式化器
- [x] 150 筆測試 (10 頁)
- [x] 智慧上傳器 (自動分割、重試、驗證、清理)
- [x] ID 生成與索引
- [x] 成功上傳 150 筆公告到 Gemini File Search
- [ ] 全量爬取 (~7,500 筆)
- [ ] RAG 查詢介面
- [ ] 法規與裁罰爬蟲

## 🤝 貢獻

這是一個個人專案,歡迎提出建議和改進。

## 📄 授權

MIT License

## 🔗 相關連結

- [金管會重要公告](https://www.fsc.gov.tw/ch/home.jsp?id=97&parentpath=0,2)
- [Gemini File Search 文件](https://ai.google.dev/gemini-api/docs/file-search)
- [專案規格文件](SPEC.md)
