# 下次繼續任務清單

## 📊 當前狀態 (2025-11-14 上午 1:25)

### ✅ 已完成
1. Phase 1-2: 爬取 495 筆裁罰案件並生成 Markdown
2. Phase 4: 建立並部署 FSC-Penalties-Deploy 專案到 Streamlit Cloud
3. Phase 5-6: UI/UX 優化（模型選擇、篩選、System Instruction）
4. 創建檔名映射腳本 `scripts/generate_file_mapping.py`

### 🔄 進行中
- **Phase 3: 上傳到 Gemini File Search Store** (背景執行中)
  - 進度：約 333/495 (67%)
  - 預計還需 30-60 分鐘完成
  - 背景任務 ID: `da2c28`

### ⏳ 待辦

#### 優先級 1：檔名映射整合
1. **等待上傳完成**
   - 檢查背景任務：`python -c "from pathlib import Path; print(Path('logs/fsc_crawler.log').exists())"`
   - 確認上傳完成標記

2. **生成檔名映射文件**
   ```bash
   cd /Users/jjshen/Projects/FSC
   source venv/bin/activate
   python scripts/generate_file_mapping.py
   ```

   輸出文件：`data/file_id_mapping.json`

   格式：
   ```json
   {
     "file_id": "日期_來源_被處分對象",
     "7qqsm5gq18n7": "2025-05-08_銀行局_台新國際商業銀行"
   }
   ```

3. **整合到 FSC-Penalties-Deploy 前端**

   a. 複製映射文件：
   ```bash
   cp /Users/jjshen/Projects/FSC/data/file_id_mapping.json \
      /Users/jjshen/Projects/FSC-Penalties-Deploy/
   ```

   b. 修改 `app.py`：
   ```python
   # 在 init_gemini() 函數中載入映射
   @st.cache_resource
   def load_file_mapping():
       mapping_path = Path(__file__).parent / 'file_id_mapping.json'
       if mapping_path.exists():
           with open(mapping_path, 'r', encoding='utf-8') as f:
               return json.load(f)
       return {}

   # 在主函數中
   file_mapping = load_file_mapping()

   # 在顯示參考文件時
   for i, source in enumerate(result['sources'], 1):
       file_id = source.get('filename', '')
       display_name = file_mapping.get(file_id, f"來源 {i}")

       with st.expander(f"📄 {display_name}", expanded=False):
           ...
   ```

   c. 提交並推送：
   ```bash
   cd /Users/jjshen/Projects/FSC-Penalties-Deploy
   git add file_id_mapping.json app.py
   git commit -m "feat: 添加檔名映射，顯示格式為「日期_來源_對象」"
   git push
   ```

#### 優先級 2：測試與驗證
1. 等待 Streamlit Cloud 自動部署（2-5 分鐘）
2. 測試查詢功能：
   - 選擇不同模型（Flash vs Pro）
   - 測試日期篩選
   - 驗證檔名顯示格式
3. 確認參考文件顯示正確

#### 優先級 3：文檔更新
1. 更新 `README.md`（FSC 專案）
   - 記錄檔名映射功能
   - 更新架構圖
2. 更新 `README.md`（FSC-Penalties-Deploy）
   - 說明檔名顯示格式
   - 添加映射文件說明

---

## 📝 重要提示

### 背景任務管理
- 上傳任務在 tmux/background 運行
- 檢查進度：`tail -f logs/fsc_crawler.log | grep "✓ 成功"`
- 完成標記：`批次上傳完成`

### 映射腳本參數
如需調整檔名格式，編輯 `scripts/generate_file_mapping.py`:
```python
# 當前格式：日期_來源_對象
display_name = f"{date}_{source}_{target}"

# 可選格式：
# 1. 只顯示日期和對象
display_name = f"{date}_{target}"

# 2. 縮短公司名稱
target_short = target.replace("股份有限公司", "").replace("台灣分公司", "")
display_name = f"{date}_{source}_{target_short}"
```

### 檔案位置
- 上傳日誌：`logs/fsc_crawler.log`
- Markdown 源：`data/temp_markdown/penalties/*.md`
- 映射輸出：`data/file_id_mapping.json`
- 部署專案：`/Users/jjshen/Projects/FSC-Penalties-Deploy`

---

## 🎯 最終目標

完成後，Streamlit 應用程式會顯示：

```
📚 參考文件 (3 筆)
點擊展開可查看引用的原文內容

📄 2025-09-25_保險局_全球人壽保險股份有限公司
  **引用內容：**
  裁罰案件內容...

📄 2024-04-23_銀行局_新光金融控股股份有限公司
  **引用內容：**
  裁罰案件內容...
```

---

最後更新：2025-11-14 01:25
