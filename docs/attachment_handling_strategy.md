# 公告附件處理策略

**關鍵發現**: 修正類公告的 PDF 附件包含**新舊條文對照表**，對於理解條文變更極為重要

---

## 🎯 附件的重要性評估

### 範例：修正類公告（dataserno=202511070001）

**公告內容**：修正「公開發行公司年報應行記載事項準則」第七條、第十條之一、第二十三條

**附件內容**：
1. **修正說明及對照表.pdf**
   - 新舊條文並列對照
   - 修正理由說明
   - 這是理解「改了什麼」的關鍵

2. **修正條文.pdf**
   - 完整的修正後條文
   - 獨立閱讀用

### 附件的價值

| 資訊需求 | 僅有公告正文 | 加上附件 |
|---------|-------------|---------|
| 知道「有修正」 | ✅ | ✅ |
| 知道「改了哪幾條」 | ✅ | ✅ |
| 知道「改了什麼內容」 | ❌ | ✅ |
| 知道「為什麼改」 | ❌ | ✅ |
| 看到「新舊對照」 | ❌ | ✅⭐ |

**結論**：對於**修正類**公告，附件是必要的。

---

## 📊 Gemini File Search 的 PDF 支援

### 優勢

✅ **原生支援 PDF**
- 支援 `application/pdf` 格式
- 自動文字提取（OCR）
- 自動 chunking 和索引

✅ **視覺理解能力**
- 可理解表格（對照表！）
- 可理解圖表
- 可理解多欄排版

✅ **大檔案支援**
- 最大 100 MB
- 最長 1,000 頁
- 對於法規文件足夠

### 限制

⚠️ **檔案大小限制**
- 單檔最大 100 MB
- 總儲存依方案而定（免費 1 GB，Tier 3 為 1 TB）

⚠️ **處理時間**
- PDF 需要較長的處理時間（文字提取、OCR）
- 上傳速度較慢

---

## 💡 處理策略

### 策略 A：全部下載並上傳（推薦 ⭐⭐⭐）

**做法**：
```python
# 1. 修改爬蟲：下載附件
def download_attachment(url: str, save_path: str):
    response = requests.get(url, verify=False)
    with open(save_path, 'wb') as f:
        f.write(response.content)

# 2. 組織檔案結構
data/
├── announcements/
│   └── fsc_ann_20251112_0001/
│       ├── announcement.md          # 公告正文
│       ├── attachment_1.pdf         # 對照表
│       └── attachment_2.pdf         # 修正條文

# 3. 上傳到 Gemini
- 公告 Markdown: 1 個
- PDF 附件: N 個
- 都上傳到同一個 store
```

**優點**：
- ✅ 資訊最完整
- ✅ 可回答「改了什麼」「為什麼改」
- ✅ Gemini 自動處理 PDF

**缺點**：
- ❌ 儲存空間增加（估計 2-5 GB）
- ❌ 上傳時間增加（估計 5-7 天）
- ❌ 爬蟲需要修改

**預估**（7,500 筆公告）：
- 假設 40% 有附件 = 3,000 個公告
- 平均每個 2 個附件 = 6,000 個 PDF
- 平均每個 500 KB = 3 GB
- 上傳時間：6,000 個 × 2 秒 = 3.3 小時（PDF）+ 2 天（Markdown）= **約 3 天**

---

### 策略 B：只下載重要類型（折衷）

**做法**：只下載包含特定關鍵字的附件

```python
IMPORTANT_KEYWORDS = [
    '對照',
    '對照表',
    '修正說明',
    '說明',
    '比較',
    '新舊條文'
]

def should_download(attachment_name: str) -> bool:
    """判斷是否應下載"""
    return any(kw in attachment_name for kw in IMPORTANT_KEYWORDS)

# 只下載重要的
for att in attachments:
    if should_download(att['name']):
        download_attachment(att['url'], save_path)
```

**優點**：
- ✅ 減少不必要的附件（如：會議紀錄、申請表格）
- ✅ 保留最關鍵的對照表
- ✅ 節省約 30-50% 空間

**缺點**：
- ⚠️ 可能遺漏部分重要附件
- ⚠️ 需要維護關鍵字清單

---

### 策略 C：附件資訊嵌入 Markdown（最小改動）

**做法**：不下載 PDF，但在 Markdown 中詳細描述附件

```markdown
# 修正「公開發行公司年報應行記載事項準則」...

**發布日期**: 2025-11-07

## 📎 附件資訊

本公告提供以下附件（未包含在此文件中）：

1. **修正說明及對照表.pdf**
   - 包含新舊條文對照表
   - 包含修正理由說明
   - [下載連結](https://...)

2. **修正條文.pdf**
   - 完整的修正後條文
   - [下載連結](https://...)

> ⚠️ 注意：詳細的條文對照內容請參考附件 PDF

## 內容

...
```

**優點**：
- ✅ 不需下載 PDF
- ✅ 使用者可自行下載
- ✅ 最快實作

**缺點**：
- ❌ Gemini 無法查詢 PDF 內容
- ❌ 無法回答「具體改了什麼」
- ❌ 使用體驗較差（需手動下載）

---

## 🎯 推薦方案

### 最佳方案：策略 A（全部下載上傳）

**理由**：

1. **時效性的本質需求**
   - 使用者問「最新規定是什麼」
   - 真正的答案在**對照表**裡（新舊條文並列）
   - 沒有 PDF，Gemini 只能說「有修正」，無法說「改成什麼」

2. **技術上可行**
   - Gemini 原生支援 PDF ✅
   - 自動提取和索引 ✅
   - 100 MB 上限足夠（法規 PDF 通常 < 5 MB）✅

3. **成本可接受**
   - 額外儲存：~3 GB（在 1 TB 限制內）
   - 額外上傳時間：~1 天（總時間從 2-3 天變成 3-4 天）
   - 索引成本：$0.15/million tokens × ~3GB ≈ $5-10

4. **對查詢效果的提升**
   ```
   使用者問：「年報記載事項有什麼新規定？」

   沒有 PDF：
   「2025-11-07 修正了第七條、第十條之一、第二十三條」

   有 PDF：
   「2025-11-07 修正了三個條文：
    - 第七條：新增了 XXX 要求（原本是...，現改為...）
    - 第十條之一：增訂 YYY 規定
    - 第二十三條：修正 ZZZ 部分

   詳細對照請見附件說明」
   ```

---

## 🔧 實作方案

### 修改爬蟲：增加附件下載

```python
# src/crawlers/announcements.py (修改 parse_detail_page)

def parse_detail_page(self, html: str, list_item: Dict[str, Any]) -> Dict[str, Any]:
    """解析詳細頁並下載附件"""

    # ... 現有邏輯 ...

    # 下載附件
    if attachments and self.config.get('download_attachments', False):
        attachment_dir = Path(f'data/attachments/announcements/{detail["id"]}')
        attachment_dir.mkdir(parents=True, exist_ok=True)

        for i, att in enumerate(attachments, 1):
            try:
                # 下載
                response = self.session.get(att['url'], verify=False, timeout=30)

                # 檔名
                filename = f"attachment_{i}.{att['type']}"
                filepath = attachment_dir / filename

                # 儲存
                with open(filepath, 'wb') as f:
                    f.write(response.content)

                # 記錄本地路徑
                att['local_path'] = str(filepath)
                att['size_bytes'] = len(response.content)

                logger.info(f"下載附件: {att['name']} ({len(response.content)} bytes)")

            except Exception as e:
                logger.error(f"下載附件失敗 {att['url']}: {e}")
                att['download_error'] = str(e)

    return detail
```

### 修改上傳器：上傳附件

```python
# src/uploader/gemini_uploader.py (新增方法)

def upload_announcement_with_attachments(
    self,
    announcement_dir: Path
) -> Dict[str, str]:
    """
    上傳公告及其附件

    Returns:
        {'announcement': file_id, 'attachments': [file_id1, file_id2]}
    """

    uploaded = {'announcement': None, 'attachments': []}

    # 1. 上傳公告 Markdown
    md_file = announcement_dir / 'announcement.md'
    if md_file.exists():
        file_id = self.upload_file(str(md_file))
        uploaded['announcement'] = file_id
        self.add_file_to_store(file_id)

    # 2. 上傳附件 PDFs
    for pdf_file in announcement_dir.glob('attachment_*.pdf'):
        file_id = self.upload_file(str(pdf_file))
        uploaded['attachments'].append(file_id)
        self.add_file_to_store(file_id)

        # 上傳間隔（避免 rate limit）
        time.sleep(2)

    return uploaded
```

### 查詢時的關聯

**重要**：公告 Markdown 和附件 PDF 都上傳到**同一個 store**

Gemini 會自動：
- 在語義相關時檢索 PDF 內容
- 合併 Markdown 和 PDF 的資訊
- 回答時引用兩者

範例：
```python
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='年報記載事項第七條改了什麼？',
    config=types.GenerateContentConfig(
        tools=[types.Tool(
            fileSearch=types.FileSearch(
                fileSearchStoreNames=['fsc-announcements']
            )
        )]
    )
)

# Gemini 會同時檢索：
# - announcement.md（找到「修正第七條」）
# - attachment_1.pdf（找到具體的新舊條文對照）
# 然後合併回答
```

---

## 📊 成本效益分析

### 不下載附件

**優點**：
- 快速（2-3 天）
- 簡單

**缺點**：
- ❌ 無法回答「具體改了什麼」
- ❌ 使用者體驗差
- ❌ **無法達成時效性目標**

### 下載附件

**成本**：
- +1 天上傳時間
- +3 GB 儲存
- +$5-10 索引費用
- 修改爬蟲和上傳器

**效益**：
- ✅ 可完整回答條文修改
- ✅ 達成時效性目標
- ✅ 使用者體驗佳
- ✅ 符合「新取代舊」的需求

**ROI**：**極高** 🌟

---

## ❓ 需要您決定

### Q1: 是否下載並上傳附件？

**我的建議**：✅ **是**

理由：
1. 附件（特別是對照表）是理解「改了什麼」的關鍵
2. 技術上可行，成本可接受
3. 對查詢效果提升巨大

### Q2: 是否需要立即實作？

**建議流程**：

1. **先測試現有資料**（無附件）
   - 看 Gemini 的基本效果
   - 驗證 prompt engineering

2. **如果效果不佳**
   - 修改爬蟲支援附件下載
   - 重新爬取（或只爬重要的修正類公告）
   - 重新上傳

3. **如果效果尚可但不理想**
   - 考慮策略 B（只下載對照表類附件）

---

## 📋 實作檢查清單

如果決定下載附件：

- [ ] 修改爬蟲配置（`config/crawler.yaml`）
  ```yaml
  attachments:
    download: true
    types: ['pdf', 'doc', 'docx']
    max_size_mb: 50
  ```

- [ ] 修改 `src/crawlers/announcements.py`
  - 增加 `download_attachment()` 方法
  - 修改 `parse_detail_page()` 下載邏輯

- [ ] 修改 `src/uploader/gemini_uploader.py`
  - 增加 `upload_with_attachments()` 方法
  - 處理 PDF 上傳

- [ ] 測試
  - 測試下載單個公告的附件
  - 測試上傳 Markdown + PDF
  - 測試查詢時是否能檢索 PDF 內容

- [ ] 批次處理
  - 重新爬取（或處理現有 URL）
  - 批次上傳

---

## 🎯 我的最終建議

**立即採取行動**：

1. **等公告上傳完成後測試**（無附件版本）
   - 如果效果已經夠好 → 暫不處理附件
   - 如果效果不佳 → 必須加入附件

2. **我預期需要附件**
   - 因為「時效性」的核心在於「知道改了什麼」
   - 這個資訊主要在對照表 PDF 裡

3. **建議修改計劃**
   - 修改爬蟲支援附件下載
   - 重新爬取（停止當前上傳）
   - 一次做對，包含附件

**要不要現在就修改爬蟲**，加入附件下載功能？我可以立即協助實作。
