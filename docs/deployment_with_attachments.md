# 附件下載功能部署說明

## 📋 部署概要

本次更新為金管會爬蟲專案新增了**附件自動下載功能**，能夠下載公告的 PDF、DOC、DOCX 附件（特別是修正條文對照表），並支援上傳到 Gemini File Search。

### 更新內容

**修改的檔案**：
1. `config/crawler.yaml` - 新增附件下載配置
2. `src/crawlers/announcements.py` - 實作附件下載邏輯
3. `src/uploader/gemini_uploader.py` - 支援附件上傳

**新增的檔案**：
- `scripts/test_attachment_download.py` - 測試腳本
- `docs/attachment_handling_strategy.md` - 策略分析文件（參考用）

---

## 🎯 部署目標

- ✅ 自動下載公告的 PDF 附件（包含修正條文對照表）
- ✅ 支援檔案類型：PDF, DOC, DOCX
- ✅ 自動重試機制（最多 3 次）
- ✅ 檔案大小限制（預設 50 MB）
- ✅ 附件上傳到 Gemini File Search

---

## 📦 部署前準備

### 1. 檢查當前狀態

```bash
# 在遠端機器上檢查當前爬取/上傳進度
ps aux | grep python  # 查看正在執行的程序

# 如果正在上傳公告到 Gemini，建議等待完成
# 因為需要重新爬取資料
```

### 2. 備份現有資料（可選）

```bash
# 備份當前已爬取的資料
cd /path/to/FSC
cp -r data/announcements data/announcements.backup.$(date +%Y%m%d)

# 備份配置
cp config/crawler.yaml config/crawler.yaml.backup
```

### 3. 停止正在執行的程序

```bash
# 如果有程序正在執行，先停止
# 找到 PID
ps aux | grep "python.*fsc"

# 停止程序（使用對應的 PID）
kill <PID>

# 或使用 pkill（小心使用）
pkill -f "python.*fsc"
```

---

## 🚀 部署步驟

### 步驟 1：更新程式碼

```bash
# 切換到專案目錄
cd /path/to/FSC

# 拉取最新程式碼
git pull origin main

# 或者，如果是從本地部署，使用 rsync 同步
# rsync -avz --exclude='venv' --exclude='data' --exclude='logs' \
#   /local/path/FSC/ user@remote:/path/to/FSC/
```

### 步驟 2：檢查配置檔案

確認 `config/crawler.yaml` 包含以下設定：

```yaml
# 附件下載設定
attachments:
  download: true  # 是否下載附件
  types:  # 下載的檔案類型
    - pdf
    - doc
    - docx
  max_size_mb: 50  # 單檔最大大小 (MB)
  save_path: "data/attachments"  # 儲存路徑
  retry_on_error: true  # 下載失敗時重試
  max_retries: 3  # 最大重試次數
```

### 步驟 3：執行測試（推薦）

```bash
# 啟動虛擬環境
source venv/bin/activate

# 執行測試腳本（爬取前3筆公告，測試下載）
python3 scripts/test_attachment_download.py
```

**預期輸出**：
```
======================================================================
測試結果
======================================================================
成功下載: 4 個附件
失敗/跳過: 1 個附件
✓ 附件下載功能正常
```

如果測試成功，繼續下一步。如果失敗，檢查錯誤訊息並解決問題。

---

## 🔄 重新爬取策略

由於需要下載附件，有以下幾種策略：

### 策略 A：完整重新爬取（推薦 ⭐）

**適用情況**：首次部署附件功能，需要完整資料

```bash
# 1. 清理舊資料（可選，如已備份）
rm -rf data/announcements
mkdir -p data/announcements

# 2. 重新爬取（使用現有腳本）
python3 scripts/crawl_announcements.py --start-page 1 --end-page 500

# 預計時間：
# - 7,500 筆公告 ≈ 500 頁
# - 爬取時間：~5-7 小時（包含附件下載）
# - 附件總大小：約 3-5 GB
```

**優點**：
- ✅ 資料最完整
- ✅ 確保所有附件都下載

**缺點**：
- ❌ 需要較長時間（5-7 小時）
- ❌ 需要較大儲存空間（+3-5 GB）

---

### 策略 B：增量補充附件（較快）

**適用情況**：已有公告資料，只補充附件

```bash
# 1. 保留現有公告資料
# data/announcements/raw.jsonl 不刪除

# 2. 修改腳本，只下載附件（需自行實作）
# 或者：只重新爬取最近 N 天的公告

python3 scripts/crawl_announcements.py \
  --start-page 1 \
  --end-page 10 \
  --force-update  # 強制更新已存在的公告
```

**優點**：
- ✅ 較快完成（~1-2 小時）
- ✅ 保留現有資料

**缺點**：
- ⚠️ 舊公告不會有附件
- ⚠️ 需要修改腳本支援

---

### 策略 C：只爬取重要公告（最快）

**適用情況**：測試或只關注最新公告

```bash
# 只爬取最近 50 頁（約 750 筆公告）
python3 scripts/crawl_announcements.py --start-page 1 --end-page 50
```

**優點**：
- ✅ 最快完成（~1 小時）
- ✅ 涵蓋最新、最重要的公告

**缺點**：
- ❌ 資料不完整

---

## 📊 預期結果

### 檔案結構

爬取完成後，目錄結構如下：

```
data/
├── announcements/
│   ├── raw.jsonl                     # 公告資料（包含附件元資料）
│   ├── index.json                    # 索引
│   └── metadata.json                 # 統計資訊
└── attachments/
    └── announcements/
        ├── fsc_ann_20251112_0001/
        │   ├── attachment_1.pdf      # 修正說明
        │   ├── attachment_2.pdf      # 對照表
        │   └── attachment_3.pdf      # 修正條文
        ├── fsc_ann_20251112_0002/
        │   └── attachment_1.pdf
        └── ...
```

### 附件元資料

每個公告的 JSONL 記錄會包含附件資訊：

```json
{
  "id": "fsc_ann_20251112_0001",
  "title": "修正「財產保險業經營傷害保險及健康保險業務管理辦法」",
  "attachments": [
    {
      "name": "傷健險管理辦法修正條文對照表",
      "url": "https://www.fsc.gov.tw/...",
      "type": "pdf",
      "local_path": "data/attachments/announcements/fsc_ann_20251112_0001/attachment_1.pdf",
      "size_bytes": 78500,
      "downloaded": true
    }
  ]
}
```

### 統計資訊

```bash
# 檢查下載的附件數量
find data/attachments/announcements -name "*.pdf" | wc -l

# 檢查總大小
du -sh data/attachments/announcements

# 範例輸出：
# 6,000 個 PDF
# 3.2 GB
```

---

## 📤 上傳到 Gemini File Search

爬取完成後，上傳到 Gemini：

### 上傳腳本（需更新）

**注意**：目前的上傳腳本可能需要修改以支援附件。使用新增的方法：

```python
from src.uploader.gemini_uploader import GeminiUploader

uploader = GeminiUploader(
    api_key='YOUR_API_KEY',
    store_name='fsc-announcements'
)

# 上傳公告及附件
for announcement_dir in Path('data/announcements_markdown').iterdir():
    result = uploader.upload_announcement_with_attachments(
        markdown_path=str(announcement_dir / 'announcement.md'),
        attachments_dir=None,  # 自動從 ID 推導
        delay=2.0
    )
    print(f"上傳完成: {result['total_files']} 個檔案")
```

### 預期上傳時間

- **Markdown 公告**：7,500 個 × 2 秒 = 4.2 小時
- **PDF 附件**：6,000 個 × 3 秒 = 5 小時
- **總計**：約 **9-10 小時**

---

## 🔍 監控和驗證

### 即時監控

```bash
# 監控日誌
tail -f logs/fsc_crawler.log

# 監控附件下載
watch -n 10 'find data/attachments/announcements -name "*.pdf" | wc -l'

# 監控磁碟空間
df -h
```

### 驗證下載成功

```bash
# 檢查是否有下載失敗的附件
grep "下載附件失敗" logs/fsc_crawler.log

# 統計下載成功率
total=$(grep "下載附件" logs/fsc_crawler.log | wc -l)
success=$(grep "✓ 下載附件" logs/fsc_crawler.log | wc -l)
echo "成功率: $(($success * 100 / $total))%"
```

---

## ⚠️ 常見問題

### Q1: 附件下載太慢怎麼辦？

**解決方案**：

1. 調整 `config/crawler.yaml` 中的 `request_interval`（風險：可能被封鎖）
2. 使用多執行緒/多程序（需修改程式碼）
3. 分批次下載

```yaml
http:
  request_interval: 0.5  # 從 1.0 秒降到 0.5 秒（謹慎使用）
```

### Q2: 磁碟空間不足怎麼辦？

**解決方案**：

1. 只下載特定類型的附件（如只下載 PDF）
2. 設定檔案大小限制（已預設 50 MB）
3. 只下載包含關鍵字的附件（如「對照表」）

```yaml
attachments:
  max_size_mb: 10  # 降低限制
  types:
    - pdf  # 只下載 PDF
```

### Q3: 有些附件下載失敗怎麼辦？

**原因**：
- 網路問題
- 檔案不存在
- 檔案過大

**解決方案**：
- 檢查日誌中的錯誤訊息
- 已有自動重試機制（3 次）
- 可手動重新爬取失敗的公告

### Q4: 上傳到 Gemini 時附件沒有包含？

**檢查清單**：
1. 確認 `attachments_dir` 路徑正確
2. 確認附件檔案存在
3. 檢查 Gemini API 配額
4. 確認 PDF 檔案沒有損壞

---

## 📝 回滾計劃

如果部署後出現問題，可以回滾：

```bash
# 1. 停止程序
pkill -f "python.*fsc"

# 2. 回滾程式碼
git reset --hard <previous-commit>

# 3. 恢復配置
cp config/crawler.yaml.backup config/crawler.yaml

# 4. 恢復資料（如果有備份）
rm -rf data/announcements
mv data/announcements.backup.YYYYMMDD data/announcements
```

---

## ✅ 部署檢查清單

部署前：
- [ ] 確認當前程序已停止
- [ ] 已備份重要資料
- [ ] 已拉取最新程式碼
- [ ] 已檢查 `config/crawler.yaml` 配置

測試：
- [ ] 執行測試腳本成功
- [ ] 能正確下載附件
- [ ] 附件儲存路徑正確

爬取：
- [ ] 選定爬取策略（A/B/C）
- [ ] 確認磁碟空間足夠（至少 10 GB）
- [ ] 開始爬取
- [ ] 監控日誌無嚴重錯誤

上傳：
- [ ] Markdown 格式化完成
- [ ] 開始上傳到 Gemini
- [ ] 驗證附件已包含在查詢結果中

---

## 📞 聯絡和支援

如遇問題：

1. 檢查日誌：`logs/fsc_crawler.log`
2. 檢查測試腳本輸出
3. 參考 `docs/attachment_handling_strategy.md`
4. 查閱 `CLAUDE.md` 和 `README.md`

---

## 🎯 預期效果

部署完成後，Gemini File Search 查詢應該能夠：

✅ **回答修正類問題**：
```
Q: 年報記載事項第七條改了什麼？
A: 2025-11-07 修正了三個條文：
   - 第七條：新增了 XXX 要求（原本是...，現改為...）
   - 第十條之一：增訂 YYY 規定
   - 第二十三條：修正 ZZZ 部分
   詳細對照請見附件說明
```

✅ **引用附件內容**：
Gemini 會自動從 PDF 對照表中提取新舊條文對比資訊

✅ **時效性查詢**：
最新的修正條文會被優先引用

---

## 📅 建議時程

| 階段 | 預估時間 | 說明 |
|------|---------|------|
| 部署準備 | 30 分鐘 | 備份、更新程式碼、測試 |
| 重新爬取 | 5-7 小時 | 完整爬取 7,500 筆公告 + 附件 |
| Markdown 格式化 | 1 小時 | 轉換為 Gemini 格式 |
| 上傳到 Gemini | 9-10 小時 | 上傳公告 + 附件 |
| **總計** | **15-18 小時** | 建議分兩天執行 |

---

**部署完成！** 🎉

如有任何問題，請參考本文件或查閱相關文檔。
