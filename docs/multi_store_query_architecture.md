# 多 Store 查詢架構與時效性處理

## 📋 需求回顧

根據用戶要求，系統必須能夠：

1. **指定查詢範圍**：
   - 只查公告
   - 只查裁罰案件
   - 同時查詢公告和裁罰

2. **控制參考文件數量**：
   - 可指定使用 N 個文件
   - 或使用全部相關文件（有多少用多少）

3. **時效性保證**：
   - 查詢回答必須符合文件在時間線上的效力
   - **公告**：新的取代舊的（2025 年規定優於 2023 年）
   - **裁罰案件**：獨立案件，無取代關係

---

## 🏗️ 架構設計

### Store 配置

#### 方案：獨立 Store（已採用）

```python
# Store 1: 公告
store_announcements = {
    'name': 'fsc-announcements',
    'file_count': ~7,500,
    'content_type': 'regulatory_announcements',
    'temporal_nature': 'replaceable',  # 有時效性，新取代舊
    'avg_file_size': '5 KB',
    'total_size': '~40 MB'
}

# Store 2: 裁罰案件
store_penalties = {
    'name': 'fsc-penalties',
    'file_count': ~630,
    'content_type': 'penalty_cases',
    'temporal_nature': 'independent',  # 獨立案件，無取代關係
    'avg_file_size': '3 KB',
    'total_size': '~2 MB'
}
```

**優點**：
- ✅ 可單獨查詢或組合查詢
- ✅ 清晰的語義分離
- ✅ 不同的時效性處理策略
- ✅ 易於維護和更新

---

## 🔍 查詢場景實作

### 場景 1：只查公告

**使用場景**：查詢法規規定、條文修正

```python
from google import genai
from google.genai import types

client = genai.Client(api_key='YOUR_API_KEY')

# 配置：只查公告 Store
config = types.GenerateContentConfig(
    tools=[
        types.Tool(
            file_search=types.FileSearch(
                file_search_store_names=['fsc-announcements']
            )
        )
    ],
    system_instruction="""
你是金融監督管理委員會的法規查詢助手。

【重要】時效性規則：
- 當有多個相關公告時，優先使用**最新日期**的公告
- 如果舊公告已被新公告修正或廢止，明確說明
- 引用時註明發布日期

回答格式：
1. 直接回答問題
2. 引用具體法條或公告內容
3. 註明發布日期和文號
4. 如有修正，說明修正歷程
""",
    temperature=0.2
)

# 查詢
response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='年報記載事項有什麼新規定？',
    config=config
)

print(response.text)
```

**預期輸出範例**：
```
根據金融監督管理委員會最新公告（2025-11-07，金管證發字第1140385140號），
「公開發行公司年報應行記載事項準則」修正了第七條、第十條之一、第二十三條。

主要修正內容：
1. 第七條：新增永續資訊揭露要求...
2. 第十條之一：增訂董事會運作資訊...
3. 第二十三條：修正財務資訊揭露格式...

本次修正自發布日施行，取代之前的版本。
```

---

### 場景 2：只查裁罰案件

**使用場景**：查詢違規案例、處分先例

```python
config = types.GenerateContentConfig(
    tools=[
        types.Tool(
            file_search=types.FileSearch(
                file_search_store_names=['fsc-penalties']
            )
        )
    ],
    system_instruction="""
你是金融監督管理委員會的裁罰案件查詢助手。

回答格式：
1. 列出相關裁罰案件
2. 包含：被處分人、處分金額、違規事實、法條依據
3. 按日期或相關性排序
4. 如有多個案件，分別說明

注意：
- 每個裁罰案件獨立，不互相取代
- 可引用多個案件作為參考
""",
    temperature=0.2
)

response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='全球人壽最近有被罰嗎？為什麼？',
    config=config
)
```

**預期輸出範例**：
```
是的，全球人壽保險股份有限公司在 2025 年 9 月 25 日被處分。

【裁罰資訊】
- 發文字號：金管保壽字第11404937382號
- 處分金額：新臺幣 300 萬元
- 違規事實：未建立董事出差事前申請核准之內控程序
- 法條依據：保險法第171條之1第4項
- 檢查報告：112I018

【詳細說明】
該公司雖訂有「董事差旅費申報作業辦法」，但未就董事出差訂定事先申請及
核准之相關內控程序，導致無法確認參訪的必要性、合理性及與業務的關聯性...
```

---

### 場景 3：同時查詢公告和裁罰

**使用場景**：全面了解特定主題（規定 + 違規案例）

```python
config = types.GenerateContentConfig(
    tools=[
        types.Tool(
            file_search=types.FileSearch(
                file_search_store_names=['fsc-announcements', 'fsc-penalties']
            )
        )
    ],
    system_instruction="""
你是金融監督管理委員會的綜合查詢助手。

你可以存取兩種資料：
1. **公告** (fsc-announcements)：法規修正、政策宣導
   - 時效性：新的取代舊的
   - 優先使用最新日期的公告

2. **裁罰案件** (fsc-penalties)：違規處分、案例
   - 獨立案件，可引用多個
   - 按相關性排序

回答格式：
1. 先說明相關規定（來自公告）
2. 再說明違規案例（來自裁罰）
3. 清楚標示資訊來源
""",
    temperature=0.2
)

response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents='內控程序有哪些規定？有哪些公司違反？',
    config=config
)
```

**預期輸出範例**：
```
【相關規定】（來源：公告）
根據保險法第148條之3及「保險業內部控制及稽核制度實施辦法」第5條規定，
保險業應建立完善的內部控制制度，包括：
1. 會計、總務、資源、人事管理之控制作業
2. 業務管理與風險控制
3. 資訊系統管理
...

【違規案例】（來源：裁罰案件）
以下公司曾因內控缺失被處分：

1. 全球人壽（2025-09-25）
   - 處分金額：300 萬元
   - 違規事實：未建立董事出差申請核准內控程序

2. 國泰世華銀行（2025-08-11）
   - 處分金額：1,200 萬元
   - 違規事實：客服專員盜刷信用卡，內控失靈

...
```

---

## 📊 參考文件數量控制

### Gemini File Search API 參數

目前 Gemini File Search **不直接支援**指定返回文件數量的參數。

#### 實際行為

```python
# API 會自動：
# 1. 檢索最相關的文件（通常 5-10 個）
# 2. 合併內容生成回答
# 3. 在回答中引用來源
```

### 解決方案

#### 方案 A：Prompt Engineering（推薦）

通過 prompt 控制引用數量：

```python
# 範例 1：要求使用多個文件
system_instruction = """
查詢時請參考**所有相關文件**，包括不同時期的公告。
列出至少 3-5 個相關案例。
"""

# 範例 2：只要求最新/最相關
system_instruction = """
只使用**最新**或**最相關**的文件回答。
避免列舉過多資訊。
"""

# 範例 3：明確指定數量
system_instruction = """
列出前 3 個最相關的裁罰案件。
"""
```

#### 方案 B：後處理過濾

如果需要更精確控制：

```python
def query_with_limit(question: str, max_results: int = 3):
    """
    查詢並限制結果數量

    Args:
        question: 查詢問題
        max_results: 最多返回幾個案例/文件
    """

    # 在 prompt 中明確指定
    enhanced_question = f"""
    {question}

    請只列出前 {max_results} 個最相關的結果。
    """

    response = client.models.generate_content(
        model='gemini-2.0-flash-001',
        contents=enhanced_question,
        config=config
    )

    return response.text
```

#### 方案 C：使用 Metadata 過濾（未來）

如果 Gemini API 支援 metadata 過濾：

```python
# 未來可能的 API
config = types.GenerateContentConfig(
    tools=[
        types.Tool(
            file_search=types.FileSearch(
                file_search_store_names=['fsc-announcements'],
                max_results=5,  # 最多檢索 5 個文件
                metadata_filter={
                    'date_range': {
                        'start': '2024-01-01',
                        'end': '2025-12-31'
                    }
                }
            )
        )
    ]
)
```

---

## ⏰ 時效性處理機制

### 問題分析

**核心挑戰**：Gemini File Search 使用**語義相關性**排序，不支援按日期排序。

**影響**：
- ❌ 舊公告可能因語義更匹配而排在前面
- ❌ 使用者可能得到過時的規定

### 解決方案

#### 策略 1：Markdown 標註（已在公告實作）

**公告 Markdown 格式**（包含時效性標記）：

```markdown
# 修正「公開發行公司年報應行記載事項準則」

⭐ **最新版本**（2025-11-07）

**資料類型**: 公告
**發文日期**: 2025-11-07
**發文字號**: 金管證發字第1140385140號

---

## 修正內容

本次修正第七條、第十條之一、第二十三條...

---

## 修正歷程

- 2025-11-07：最新修正（本文件）
- 2023-05-15：前次修正（已由本次取代）
- 2020-03-01：前次修正（已廢止）

---

*本文件為最新有效版本，取代所有先前版本。*
```

**舊版公告標註**（如有）：

```markdown
# 修正「公開發行公司年報應行記載事項準則」

⚠️ **已過時**：本文件已被 2025-11-07 公告取代

**資料類型**: 公告（已廢止）
**發文日期**: 2023-05-15

---

⚠️ 注意：本規定已於 2025-11-07 修正，請參閱最新版本。

---
```

#### 策略 2：System Instruction 強調時效性

```python
system_instruction = """
你是金融監督管理委員會的法規查詢助手。

【重要】時效性規則：

1. **公告類文件**：
   - 優先使用標註「⭐ 最新版本」的文件
   - 忽略標註「⚠️ 已過時」的文件
   - 如果檢索到多個相關公告，比較發文日期，使用最新的
   - 明確告知使用者你引用的是哪個日期的規定

2. **裁罰案件**：
   - 每個案件獨立，無時效性問題
   - 可引用多個案件

3. **衝突處理**：
   - 如果發現新舊規定衝突，明確說明：「舊規定（YYYY-MM-DD）已被新規定（YYYY-MM-DD）取代」
   - 只提供最新規定的內容

4. **引用格式**：
   - 始終註明發布日期和文號
   - 如：「根據 2025-11-07 發布的公告（金管證發字第1140385140號）...」
"""
```

#### 策略 3：使用者查詢範例引導

提供查詢範例，教育使用者如何獲得最新資訊：

```python
# 好的查詢方式
"最新的年報記載事項規定是什麼？"  # 明確要求最新
"2025 年有哪些年報相關修正？"  # 指定時間範圍

# 需要改進的查詢
"年報記載事項有哪些規定？"  # 可能返回舊規定
```

---

## 📝 實作檢查清單

### 公告 Store

- [x] 設計 Markdown 格式（包含時效性標記）
- [ ] 建立公告修正歷程追蹤機制
- [ ] 實作 Markdown 格式化器（添加時效性標記）
- [ ] 測試多版本公告的查詢效果
- [ ] 撰寫 System Instruction

### 裁罰 Store

- [x] 設計 JSONL 資料結構
- [x] 實作 PenaltyCrawler
- [x] 測試爬蟲功能
- [ ] 實作 Markdown 格式化器（裁罰專用）
- [ ] 測試查詢效果
- [ ] 撰寫 System Instruction

### 多 Store 查詢

- [ ] 測試單一 Store 查詢（公告 only, 裁罰 only）
- [ ] 測試多 Store 查詢（公告 + 裁罰）
- [ ] 驗證時效性處理是否有效
- [ ] 建立查詢範例庫
- [ ] 撰寫使用者文檔

---

## 🧪 測試場景

### 測試 1：時效性驗證（公告）

**準備**：
- 同一法規的 3 個版本：2020, 2023, 2025

**測試**：
```python
query = "年報記載事項有哪些規定？"
```

**預期**：
- ✅ 回答使用 2025 年版本
- ✅ 明確註明「2025-11-07」日期
- ✅ 如提到舊版本，說明已被取代

---

### 測試 2：獨立性驗證（裁罰）

**準備**：
- 同一公司的多次裁罰案件

**測試**：
```python
query = "全球人壽有哪些裁罰紀錄？"
```

**預期**：
- ✅ 列出所有相關裁罰案件
- ✅ 每個案件獨立說明
- ✅ 按日期排序

---

### 測試 3：跨 Store 查詢

**測試**：
```python
query = "內控程序的規定是什麼？有哪些違規案例？"
```

**預期**：
- ✅ 分別從公告和裁罰 Store 檢索
- ✅ 公告使用最新版本
- ✅ 裁罰列出相關案例
- ✅ 清楚標示資訊來源

---

## 🎯 最佳實踐

### 1. Prompt 設計

**明確指定查詢範圍**：
```python
# 只要公告
"根據金管會公告，年報記載事項有哪些規定？"

# 只要裁罰
"有哪些公司因內控問題被處分？"

# 要兩者
"內控的規定是什麼？有違規案例嗎？"
```

### 2. 結果驗證

在回答中要求 Gemini 提供：
- 文件類型（公告 / 裁罰）
- 發布日期
- 文號
- 來源 Store

### 3. 持續優化

- 收集實際查詢案例
- 分析時效性問題
- 調整 System Instruction
- 優化 Markdown 標註

---

## 📊 效能考量

### 查詢延遲

| 配置 | 預估延遲 |
|------|---------|
| 單一 Store（公告） | 2-3 秒 |
| 單一 Store（裁罰） | 1-2 秒 |
| 雙 Store 查詢 | 3-5 秒 |

### 成本估算

| 項目 | 成本 |
|------|------|
| 查詢 (File Search) | 免費（包含在 API 調用中）|
| 回答生成 | $0.15 / million tokens |
| 每次查詢平均 | ~$0.001 |

---

## ✅ 總結

### 架構決策

1. **獨立 Store**：公告和裁罰使用不同 Store ✅
2. **時效性處理**：Markdown 標註 + System Instruction ✅
3. **參考數量**：Prompt Engineering 控制 ✅
4. **查詢靈活性**：支援單一或多 Store 查詢 ✅

### 核心優勢

- ✅ 滿足所有需求（指定範圍、控制數量、時效性）
- ✅ 實作簡單，不需複雜後處理
- ✅ 可擴展（未來可加入法規 Store）
- ✅ 易於維護和調整

### 下一步

1. 完成 Markdown 格式化器（公告和裁罰）
2. 建立時效性標註機制
3. 撰寫詳細的 System Instructions
4. 進行端到端測試
5. 部署到生產環境

---

**準備就緒！** 🎉

架構設計完成，可以開始實作和測試。
