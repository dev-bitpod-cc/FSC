# 智慧上傳器使用指南

智慧上傳器 (`GeminiUploader`) 是一個完整的解決方案,用於將 Markdown 檔案上傳到 Google Gemini File Search,並自動處理大檔案分割、失敗重試、狀態追蹤和清理工作。

## 🌟 核心特性

### 1. 自動檔案分割

當檔案超過指定大小時 (預設 100 KB),自動分割成多個小檔案:

- 按照 Markdown 項目數量分割 (預設每個檔案 22 個項目)
- 保持每個項目的完整性 (使用 `# ` 開頭作為分隔符)
- 自動產生檔名: `original_name_part1_of_3.md`

**範例:**
- `securities_bureau.md` (340 KB, 67 項) → 分割成 4 個檔案
- `insurance_bureau.md` (129 KB, 42 項) → 分割成 2 個檔案
- `bank_bureau.md` (108 KB, 33 項) → 分割成 2 個檔案

### 2. Exponential Backoff 重試機制

上傳失敗時自動重試,每次重試間隔時間遞增:

- 第 1 次失敗: 等待 2 秒後重試
- 第 2 次失敗: 等待 4 秒後重試
- 第 3 次失敗: 等待 8 秒後重試
- 超過最大重試次數後跳過該檔案

**配置:**
```python
uploader = GeminiUploader(
    max_retries=3,      # 最大重試次數
    retry_delay=2.0     # 初始延遲基數 (秒)
)
```

### 3. 上傳狀態追蹤

使用 `upload_manifest.json` 記錄每個檔案的上傳狀態:

```json
{
  "uploaded": {
    "path/to/file.md": {
      "file_id": "files/abc123",
      "timestamp": 1762962700.94,
      "status": "success",
      "display_name": "file.md"
    }
  },
  "split_files": [
    "data/temp_uploads/large_file_part1_of_3.md",
    "data/temp_uploads/large_file_part2_of_3.md"
  ]
}
```

**用途:**
- 跨多次執行時記住已上傳的檔案
- 支援 `skip_existing=True` 功能
- 追蹤失敗的上傳以便後續處理

### 4. 完整性驗證

上傳完成後自動驗證:

```python
report = uploader.verify_upload_completeness()

# 報告內容:
{
    'total': 10,
    'successful': 9,
    'failed': 1,
    'pending': 0,
    'successful_files': [...],
    'failed_files': [...],
    'pending_files': [...]
}
```

### 5. 自動清理暫存檔案

上傳完成後自動刪除分割產生的暫存檔案:

- 只刪除成功上傳的分割檔案
- 保留失敗的檔案以便檢查
- 如果暫存目錄為空,自動刪除該目錄
- 可使用 `auto_cleanup=False` 關閉自動清理

## 📋 使用方式

### 基本使用

```python
from src.uploader.gemini_uploader import GeminiUploader

# 初始化
uploader = GeminiUploader(
    api_key='your_api_key',
    store_name='fsc-announcements',
    max_file_size_kb=100,
    max_items_per_split=22,
    max_retries=3,
    retry_delay=2.0
)

# 上傳目錄 (一行搞定所有事情!)
stats = uploader.upload_directory(
    directory='data/markdown/by_source',
    pattern='*.md',
    delay=1.0,
    skip_existing=True,
    auto_split=True,
    auto_cleanup=True
)

print(f"上傳完成: {stats['uploaded_files']}/{stats['total_files']}")
print(f"分割檔案: {stats['split_files']}")
print(f"失敗: {stats['failed_files']}")
```

### 進階使用: 手動處理失敗檔案

```python
# 第一次上傳 (部分檔案可能失敗)
stats = uploader.upload_directory('data/markdown/by_source')

# 取得失敗的上傳
failed = uploader.get_failed_uploads()

for item in failed:
    print(f"檔案: {item['filepath']}")
    print(f"錯誤: {item['error']}")
    print(f"時間: {item['timestamp']}")
    print()

# 第二次執行時,自動跳過已成功上傳的檔案
# 只重新嘗試失敗的檔案
stats = uploader.upload_directory(
    'data/markdown/by_source',
    skip_existing=True  # 跳過已上傳的檔案
)
```

### 批次上傳指定檔案

```python
filepaths = [
    'data/markdown/file1.md',
    'data/markdown/file2.md',
    'data/markdown/large_file.md'  # 會自動分割
]

stats = uploader.upload_batch(
    filepaths,
    delay=1.0,
    skip_existing=True,
    auto_split=True,
    auto_cleanup=True
)
```

### 手動分割檔案 (不推薦,通常不需要)

```python
from pathlib import Path

# 檢查檔案是否需要分割
if uploader._should_split_file(Path('large_file.md')):
    # 分割檔案
    split_files = uploader._split_markdown_file(Path('large_file.md'))
    print(f"分割成 {len(split_files)} 個檔案")

    # 上傳分割後的檔案
    for split_file in split_files:
        uploader.upload_and_add(str(split_file))

    # 手動清理
    uploader.cleanup_split_files()
```

## 🔧 配置參數

### GeminiUploader 初始化參數

| 參數 | 預設值 | 說明 |
|-----|-------|------|
| `api_key` | 環境變數 | Gemini API Key |
| `store_name` | `'fsc-announcements'` | File Search Store 名稱 |
| `max_file_size_kb` | `100` | 檔案大小上限 (KB),超過自動分割 |
| `max_items_per_split` | `22` | 每個分割檔案的最大項目數 |
| `max_retries` | `3` | 上傳失敗時最大重試次數 |
| `retry_delay` | `2.0` | 重試延遲基數 (秒),使用 exponential backoff |

### upload_directory / upload_batch 參數

| 參數 | 預設值 | 說明 |
|-----|-------|------|
| `delay` | `1.0` | 每次上傳間隔秒數 |
| `skip_existing` | `True` | 跳過已上傳的檔案 |
| `auto_split` | `True` | 自動分割大檔案 |
| `auto_cleanup` | `True` | 完成後自動清理分割檔案 |

## 📊 統計資訊

上傳完成後會返回詳細的統計資訊:

```python
stats = {
    'total_files': 5,        # 原始檔案數
    'uploaded_files': 10,    # 實際上傳數 (含分割檔案)
    'failed_files': 0,       # 失敗數
    'total_bytes': 629357,   # 總位元組數
    'split_files': 8,        # 分割產生的檔案數
    'skipped_files': 0       # 跳過的檔案數 (已上傳)
}
```

## 🚨 常見問題

### Q: 上傳時遇到 503 錯誤怎麼辦?

A: 503 錯誤通常是 Gemini API 的暫時性問題,智慧上傳器會自動重試:
- 自動重試 3 次 (可配置)
- 使用 exponential backoff 避免頻繁請求
- 如果持續失敗,請檢查檔案內容或降低 `max_items_per_split` 參數

### Q: 如何調整分割大小?

A: 有兩種方式:

1. **按檔案大小** (推薦):
```python
uploader = GeminiUploader(max_file_size_kb=50)  # 50 KB 以上分割
```

2. **按項目數量**:
```python
uploader = GeminiUploader(max_items_per_split=10)  # 每檔案 10 個項目
```

### Q: 可以停用自動清理嗎?

A: 可以,在上傳時設定 `auto_cleanup=False`:

```python
stats = uploader.upload_directory(
    'data/markdown/by_source',
    auto_cleanup=False  # 保留分割檔案
)

# 稍後手動清理
uploader.cleanup_split_files()
```

### Q: 如何只重新上傳失敗的檔案?

A: 使用 `skip_existing=True` (預設啟用):

```python
# 第一次執行 (某些檔案可能失敗)
stats = uploader.upload_directory('data/markdown/by_source')

# 第二次執行 (自動跳過成功的,只重試失敗的)
stats = uploader.upload_directory(
    'data/markdown/by_source',
    skip_existing=True  # 已上傳的會被跳過
)
```

### Q: manifest 檔案可以刪除嗎?

A: 可以刪除,但會失去上傳歷史記錄:
- 刪除後所有檔案都會被視為"未上傳"
- 重新執行會重新上傳所有檔案
- 建議保留 manifest 以支援增量更新

位置: `data/temp_uploads/upload_manifest.json`

## 🎯 最佳實踐

1. **使用預設配置**: 預設配置經過測試,適合大多數情況
2. **啟用 skip_existing**: 避免重複上傳已成功的檔案
3. **啟用 auto_cleanup**: 自動清理暫存檔案,節省磁碟空間
4. **保留 manifest**: 支援增量更新和斷點續傳
5. **適當的延遲**: `delay=1.0` 可避免 API 速率限制
6. **定期驗證**: 使用 `verify_upload_completeness()` 檢查上傳狀態

## 📝 測試腳本

使用提供的測試腳本快速驗證功能:

```bash
python scripts/test_smart_uploader.py
```

這個腳本會:
1. 初始化智慧上傳器
2. 上傳 `data/markdown/by_source` 目錄
3. 自動分割大檔案
4. 顯示詳細的上傳進度
5. 驗證上傳完整性
6. 清理暫存檔案
7. 顯示最終報告

## 🔗 相關文件

- [README.md](../README.md) - 專案概覽
- [SPEC.md](../SPEC.md) - 專案規格
- [Gemini File Search API](https://ai.google.dev/gemini-api/docs/file-search) - 官方文件
