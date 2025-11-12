# 503 錯誤處置方案

## 問題背景

在上傳檔案到 Gemini File Search Store 時,可能會遇到 503 錯誤:
```
503 UNAVAILABLE. {'error': {'code': 503, 'message': 'Failed to count tokens.', 'status': 'UNAVAILABLE'}}
```

這個錯誤通常發生在 `add_file_to_store` 階段,檔案已經上傳成功,但 Gemini 在處理檔案(計算 token)時暫時無法完成操作。

## 已實作的解決方案

### 1. ✅ Exponential Backoff 重試機制

在 `upload_and_add()` 方法 (`src/uploader/gemini_uploader.py:324-377`) 中實作了完整的重試邏輯:

```python
def upload_and_add(self, filepath, display_name, delay):
    for attempt in range(self.max_retries):
        try:
            file_id = self.upload_file(filepath, display_name)
            time.sleep(delay)

            # 加入 Store (可能遇到 503)
            self.client.file_search_stores.import_file(
                file_search_store_name=self.store_id,
                file_name=file_id
            )
            return True

        except Exception as e:
            if attempt < self.max_retries - 1:
                # Exponential backoff: 2, 4, 8 秒
                retry_delay = self.retry_delay * (2 ** attempt)
                time.sleep(retry_delay)
            else:
                return False
```

**重試時間表**:
- 第 1 次失敗: 等待 2 秒後重試
- 第 2 次失敗: 等待 4 秒後重試
- 第 3 次失敗: 等待 8 秒後重試
- 超過 3 次: 跳過該檔案並記錄為失敗

### 2. ✅ 失敗記錄與追蹤

失敗的上傳會被記錄在 `upload_manifest.json`:

```json
{
  "uploaded": {
    "path/to/failed_file.md": {
      "file_id": null,
      "timestamp": 1762962700.94,
      "status": "failed",
      "error": "503 UNAVAILABLE. Failed to count tokens.",
      "display_name": "failed_file.md"
    }
  }
}
```

### 3. ✅ 完整性驗證

使用 `verify_upload_completeness()` 檢查失敗的檔案:

```python
report = uploader.verify_upload_completeness()

print(f"成功: {report['successful']}/{report['total']}")
print(f"失敗: {report['failed']}/{report['total']}")

# 取得失敗的檔案列表
for item in report['failed_files']:
    print(f"檔案: {item['filepath']}")
    print(f"錯誤: {item['error']}")
```

### 4. ✅ 手動重試失敗檔案

由於使用 `skip_existing=True`,再次執行上傳會自動跳過成功的檔案,只重試失敗的:

```python
# 第一次執行 (部分檔案失敗)
stats = uploader.upload_directory('data/markdown/by_source')

# 第二次執行 (自動跳過成功的,只重試失敗的)
stats = uploader.upload_directory(
    'data/markdown/by_source',
    skip_existing=True  # 已成功的會被跳過
)
```

## 其他可行的處置方式

### 5. 🔧 調整檔案分割參數

如果 503 錯誤頻繁發生,可能是檔案太大或內容太複雜:

```python
uploader = GeminiUploader(
    max_file_size_kb=50,       # 降低至 50 KB (原本 100 KB)
    max_items_per_split=10,    # 減少至每檔案 10 個項目 (原本 22 個)
    max_retries=5,             # 增加重試次數至 5 次
    retry_delay=3.0            # 增加初始延遲至 3 秒
)
```

### 6. 🔧 增加上傳間隔

增加每次上傳之間的延遲,避免 API 過載:

```python
stats = uploader.upload_directory(
    'data/markdown/by_source',
    delay=2.0,  # 增加至 2 秒 (原本 1 秒)
)
```

### 7. 🔧 分批上傳

將大量檔案分成小批次上傳:

```python
import os
from pathlib import Path

files = list(Path('data/markdown/by_source').glob('*.md'))
batch_size = 5  # 每批 5 個檔案

for i in range(0, len(files), batch_size):
    batch = files[i:i+batch_size]
    logger.info(f"上傳批次 {i//batch_size + 1}: {len(batch)} 個檔案")

    uploader.upload_batch(
        [str(f) for f in batch],
        delay=2.0
    )

    # 批次之間休息 10 秒
    time.sleep(10)
```

### 8. 🔧 使用不同的時間上傳

Gemini API 可能在尖峰時段較容易出現 503 錯誤,可以:
- 在離峰時段上傳 (例如深夜或清晨)
- 錯開上傳時間

### 9. 🔧 檢查檔案內容

某些特定內容可能導致 token 計算失敗:
- 檢查是否有特殊字元或編碼問題
- 確認 Markdown 格式正確
- 移除可能有問題的內容

### 10. 🔧 手動清理 Store 後重新上傳

如果 Store 本身有問題:

```python
# 刪除舊的 Store (謹慎使用!)
uploader.delete_store()

# 重新建立 Store 並上傳
uploader.get_or_create_store()
stats = uploader.upload_directory('data/markdown/by_source')
```

## 最佳實踐

根據測試經驗,建議的處理流程:

1. **第一次上傳**: 使用預設配置
2. **檢查結果**: 使用 `verify_upload_completeness()` 查看失敗檔案
3. **重試失敗檔案**: 重新執行一次 (自動跳過成功的)
4. **如果持續失敗**: 調整參數 (降低檔案大小、增加延遲、增加重試次數)
5. **最後手段**: 分批上傳或在離峰時段重試

## 實際測試結果

在我們的測試中:
- **總檔案數**: 10 個 (5 個原始檔案分割成 10 個)
- **成功率**: 10/10 (100%)
- **503 錯誤**: 1 次 (在 add_file_to_store 階段)
- **重試結果**: 自動重試後成功

這證明了 Exponential Backoff 重試機制的有效性。

## 程式碼位置

相關實作可以在以下位置找到:
- **重試機制**: `src/uploader/gemini_uploader.py:324-377` (upload_and_add 方法)
- **狀態追蹤**: `src/uploader/gemini_uploader.py:261-268` (manifest 記錄)
- **完整性驗證**: `src/uploader/gemini_uploader.py:495-534` (verify_upload_completeness 方法)
- **失敗檔案查詢**: `src/uploader/gemini_uploader.py:589-606` (get_failed_uploads 方法)

## 總結

透過以上多層防護:
1. ✅ 自動重試 (Exponential Backoff)
2. ✅ 失敗記錄與追蹤
3. ✅ 完整性驗證
4. ✅ 自動跳過成功檔案的重試機制
5. 🔧 可調整的參數設定

可以有效處理 503 錯誤,確保檔案最終能夠成功上傳。
