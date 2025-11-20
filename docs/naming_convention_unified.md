# 法令函釋與重要公告的統一命名規範

**制定日期**: 2025-11-21
**目的**: 避免類型代碼衝突，建立清晰的命名慣例

---

## 一、問題說明

### 1.1 發現的衝突

**法令函釋**（`law_interpretations.py`）使用：
- `announcement` - 發布/公布型（標題開頭：「發布」或「公布」）
- `notice` - 公告型（標題開頭：「公告」）

**重要公告**（計畫使用）：
- `general_announcement` - 一般公告（令）（標題開頭：「有關」）

**潛在問題**：
- `announcement` 在兩個地方有不同意義
- 容易造成 `file_mapping.json` 中的 `category` 欄位混淆

---

## 二、統一命名方案

### 2.1 核心原則

1. **使用資料來源前綴**：`law_` vs `ann_`
2. **描述性優於簡潔性**：`publication` 優於 `announcement`
3. **一致性**：相同概念在不同資料源使用相同基礎詞

### 2.2 法令函釋類型代碼（建議修正）

| 中文名稱 | 舊代碼 | **新代碼** | 標題開頭 | 修正理由 |
|---------|-------|----------|---------|---------|
| 修正型 | `amendment` | `law_amendment` | 修正 | ✅ 加前綴 |
| 訂定型 | `enactment` | `law_enactment` | 訂定 | ✅ 加前綴 |
| 函釋型（有關）| `clarification` | `law_clarification` | 有關 | ✅ 加前綴 |
| 廢止型 | `repeal` | `law_repeal` | 廢止 | ✅ 加前綴 |
| **發布/公布型** | **`announcement`** | **`law_publication`** ⭐ | 發布/公布 | 🔴 **避免衝突** |
| 核准/指定型 | `approval` | `law_approval` | 指定/核准 | ✅ 加前綴 |
| 調整型 | `adjustment` | `law_adjustment` | 調降/調整 | ✅ 加前綴 |
| **公告型（程序性）** | **`notice`** | **`law_notice`** | 公告 | ✅ 加前綴 |

### 2.3 重要公告類型代碼（建議使用）

| 中文名稱 | **代碼** | 標題開頭 | 說明 |
|---------|---------|---------|------|
| 修正類 | `ann_amendment` | 修正 | 修正既有法規 |
| 預告類 | `ann_draft` | 預告 | 草案預告 |
| 訂定類 | `ann_enactment` | 訂定 | 訂定新法規 |
| **一般公告（令）** | **`ann_regulation`** ⭐ | **有關** | 🔴 **核心類型** |
| 指定類 | `ann_designation` | 指定 | 指定機構 |
| 發布類 | `ann_publication` | 發布 | 發布法規 |
| 廢止類 | `ann_repeal` | 廢止 | 廢止舊令 |

### 2.4 命名對照表

#### **相同概念，使用相同基礎詞**：

| 概念 | 法令函釋 | 重要公告 | 基礎詞 |
|------|---------|---------|-------|
| 修正 | `law_amendment` | `ann_amendment` | `amendment` |
| 訂定 | `law_enactment` | `ann_enactment` | `enactment` |
| 廢止 | `law_repeal` | `ann_repeal` | `repeal` |
| 發布/公布 | `law_publication` | `ann_publication` | `publication` |

#### **不同概念，使用不同基礎詞**：

| 中文 | 法令函釋 | 重要公告 | 說明 |
|------|---------|---------|------|
| 有關 | `law_clarification` | `ann_regulation` | 函釋 vs 規定/令 |
| 公告 | `law_notice` | - | 程序性公告（法令函釋特有） |
| 指定 | `law_approval` | `ann_designation` | 核准 vs 指定 |

---

## 三、為什麼選擇 `ann_regulation` 而非 `ann_general_announcement`？

### 3.1 原因分析

**標題格式**：
```
有關證券商管理規則第37條之1第2項當日沖銷交易有價證券之種類及範圍之令
```

**性質分析**：
- 這是一個「令」（regulation/order/decree）
- 不是一般性的「公告」（announcement）
- 內容是對法條的「規定」和「解釋」
- 英文對應：regulatory order, administrative regulation

**與法令函釋「有關」的差異**：
| 特徵 | 法令函釋「有關」 | 重要公告「有關」 |
|------|---------------|---------------|
| 性質 | 函釋（clarification） | 令（regulation/order） |
| 目的 | 澄清法條適用疑義 | 規定適用範圍/標準 |
| 效力 | 解釋性 | 規範性 |
| 英文 | clarification | regulation |

### 3.2 候選詞比較

| 候選詞 | 優點 | 缺點 | 評分 |
|-------|------|------|-----|
| `ann_general_announcement` | 直譯「一般公告」 | 太長、不精準 | ⭐⭐ |
| `ann_order` | 簡潔、準確（令） | 可能與 order（命令）混淆 | ⭐⭐⭐ |
| **`ann_regulation`** | **精準、專業** | **無** | ⭐⭐⭐⭐⭐ |
| `ann_decree` | 準確（法令） | 較少用於行政規定 | ⭐⭐⭐⭐ |

**最終選擇**：`ann_regulation`
- ✅ 精準反映「規定」的性質
- ✅ 與法令函釋的 `clarification` 區分明確
- ✅ 簡潔、易理解
- ✅ 符合國際慣例（regulatory announcement）

---

## 四、實作建議

### 4.1 修正法令函釋爬蟲（向後兼容）

**方案 A：保持舊代碼，只在顯示時轉換**
```python
# law_interpretations.py - 保持不變
def _identify_category(self, title: str) -> str:
    # ... 保持現有代碼 ...
    elif title.startswith('發布') or title.startswith('公布'):
        return 'announcement'  # 保持不變
    elif title.startswith('公告'):
        return 'notice'  # 保持不變

# 在 file_mapping 生成時添加 source_type 前綴
def generate_file_mapping():
    category = item['metadata']['category']
    item['category_full'] = f"law_{category}"  # 添加前綴
```

**方案 B：直接修正代碼（建議）**
```python
# law_interpretations.py - 直接使用新代碼
def _identify_category(self, title: str) -> str:
    if not title:
        return 'unknown'

    if title.startswith('修正'):
        return 'law_amendment'  # 加前綴
    elif title.startswith('訂定'):
        return 'law_enactment'
    elif title.startswith('有關'):
        return 'law_clarification'
    elif title.startswith('廢止'):
        return 'law_repeal'
    elif title.startswith('發布') or title.startswith('公布'):
        return 'law_publication'  # 🔴 修正：避免與 announcement 衝突
    elif title.startswith('指定') or title.startswith('核准'):
        return 'law_approval'
    elif title.startswith('調降') or title.startswith('調整'):
        return 'law_adjustment'
    elif title.startswith('公告'):
        return 'law_notice'
    else:
        return 'law_other'
```

### 4.2 重要公告爬蟲（新實作）

```python
# announcements.py - 新實作
def _identify_category(self, title: str) -> str:
    """
    識別公告類型

    Args:
        title: 標題

    Returns:
        類型代碼（帶 ann_ 前綴）
    """
    if not title:
        return 'ann_unknown'

    if title.startswith('修正'):
        return 'ann_amendment'
    elif title.startswith('預告'):
        return 'ann_draft'
    elif title.startswith('訂定'):
        return 'ann_enactment'
    elif title.startswith('有關'):
        return 'ann_regulation'  # 🔴 關鍵：一般公告（令）
    elif title.startswith('指定'):
        return 'ann_designation'
    elif title.startswith('發布'):
        return 'ann_publication'
    elif title.startswith('廢止'):
        return 'ann_repeal'
    else:
        return 'ann_other'
```

### 4.3 file_mapping.json 結構

**統一的 metadata 結構**：
```json
{
  "fsc_law_20251113_0002": {
    "source_type": "law_interpretation",
    "category": "law_clarification",
    "category_display": "函釋型（有關）",
    "title": "有關證券商管理規則第37條之1...",
    ...
  },
  "fsc_ann_20251113_0002": {
    "source_type": "announcement",
    "category": "ann_regulation",
    "category_display": "一般公告（令）",
    "title": "有關證券商管理規則第37條之1...",
    ...
  }
}
```

---

## 五、遷移計畫

### 5.1 階段 1：修正法令函釋（如果已上傳）

**情況 A：尚未上傳到 Gemini**
- ✅ 直接使用新代碼（方案 B）
- ✅ 重新生成 file_mapping.json

**情況 B：已上傳到 Gemini**
```bash
# 選項 1：重新生成 mapping（推薦）
python scripts/update_law_interpretations_mapping.py --update-categories

# 選項 2：保持舊代碼，添加 source_type 前綴
python scripts/add_source_type_prefix.py --source law_interpretations
```

### 5.2 階段 2：實作重要公告爬蟲

```bash
# 使用新的命名規範
python scripts/crawl_announcements.py --use-new-naming

# 生成 file_mapping 時自動使用 ann_ 前綴
python scripts/generate_announcement_mapping.py
```

---

## 六、顯示名稱對照表

### 6.1 法令函釋

| 代碼 | 顯示名稱（繁中） | 顯示名稱（英文） |
|------|---------------|----------------|
| `law_amendment` | 修正型 | Amendment |
| `law_enactment` | 訂定型 | Enactment |
| `law_clarification` | 函釋型（有關） | Clarification |
| `law_repeal` | 廢止型 | Repeal |
| `law_publication` | 發布/公布型 | Publication |
| `law_approval` | 核准/指定型 | Approval |
| `law_adjustment` | 調整型 | Adjustment |
| `law_notice` | 公告型（程序性） | Notice |

### 6.2 重要公告

| 代碼 | 顯示名稱（繁中） | 顯示名稱（英文） |
|------|---------------|----------------|
| `ann_amendment` | 修正類 | Amendment |
| `ann_draft` | 預告類 | Draft |
| `ann_enactment` | 訂定類 | Enactment |
| `ann_regulation` | 一般公告（令） | Regulation |
| `ann_designation` | 指定類 | Designation |
| `ann_publication` | 發布類 | Publication |
| `ann_repeal` | 廢止類 | Repeal |

---

## 七、總結

### 7.1 關鍵決策

1. ✅ 使用資料來源前綴：`law_` vs `ann_`
2. ✅ 法令函釋「發布/公布型」：`announcement` → `law_publication`
3. ✅ 重要公告「一般公告（令）」：`ann_regulation`（而非 `ann_general_announcement`）

### 7.2 優勢

- ✅ **避免衝突**：不同資料源的類型代碼完全獨立
- ✅ **清晰易懂**：一看代碼就知道來自哪個資料源
- ✅ **易於擴充**：未來新增資料源（如裁罰案件）可用 `pen_` 前綴
- ✅ **專業準確**：`regulation` 比 `general_announcement` 更精準

### 7.3 下一步

1. ⚠️ 決定是否修正法令函釋的類型代碼（如果已上傳）
2. ✅ 實作重要公告爬蟲時使用新的命名規範
3. ✅ 更新分析文檔中的類型代碼

---

**文檔版本**: v1.0
**制定日期**: 2025-11-21
**適用專案**: FSC（金管會爬蟲專案）
