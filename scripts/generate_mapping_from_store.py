"""
從 Gemini Store 查詢所有文件並生成 file_id -> 顯示名稱映射
"""

import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()

def extract_info_from_filename(filename: str) -> dict:
    """從文件名提取資訊

    文件名格式: fsc_pen_20250508_0005_銀行局_台新國際商業銀行...md
    """
    # 移除 .md 後綴
    name = filename.replace('.md', '')

    # 正則提取: fsc_pen_YYYYMMDD_NNNN_來源_標題
    pattern = r'fsc_pen_(\d{8})_(\d{4})_(.+?)_(.+)'
    match = re.match(pattern, name)

    if match:
        date_str = match.group(1)  # 20250508
        seq = match.group(2)        # 0005
        source = match.group(3)     # 銀行局
        target = match.group(4)     # 台新國際商業銀行...

        # 格式化日期
        date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        # 清理被處分對象名稱（移除過長的後綴）
        target = target.split('辦理')[0].split('因')[0].split('違反')[0].strip()

        return {
            'date': date,
            'source': source,
            'target': target,
            'display_name': f"{date}_{source}_{target}"
        }

    return None

def main():
    print("=" * 70)
    print("從 Gemini Store 生成 File ID 映射")
    print("=" * 70)

    # 初始化
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ 找不到 GEMINI_API_KEY")
        return

    client = genai.Client(api_key=api_key)
    store_id = 'fileSearchStores/fscpenalties-ma1326u8ck77'

    print(f"\n查詢 Store: {store_id}")
    print("這可能需要一些時間...")

    try:
        # 列出 Store 中的所有文檔
        documents = []
        for doc in client.file_search_stores.documents.list(parent=store_id):
            documents.append(doc)

            if len(documents) % 50 == 0:
                print(f"  已獲取 {len(documents)} 個文件...")

        print(f"\n✓ 共獲取 {len(documents)} 個文件")

        # 生成映射
        print("\n生成映射...")
        file_to_display = {}
        no_match_count = 0

        for doc in documents:
            # 從 document name 提取資訊
            # document.name 格式: fileSearchStores/.../documents/xxxxx
            doc_id = doc.name.split('/')[-1]  # 提取最後的 ID

            # 從 display_name 提取文件名
            filename = doc.display_name if hasattr(doc, 'display_name') and doc.display_name else None

            if not filename:
                print(f"⚠️  無法獲取文件名: {doc.name}")
                continue

            # 從文件名提取資訊
            info = extract_info_from_filename(filename)

            if info:
                file_to_display[doc_id] = info['display_name']
            else:
                no_match_count += 1
                print(f"⚠️  無法解析文件名: {filename}")

        print(f"✓ 成功建立 {len(file_to_display)} 筆映射")
        if no_match_count > 0:
            print(f"⚠️  {no_match_count} 筆無法解析")

        # 保存
        output_path = Path('data/file_id_mapping.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(file_to_display, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 映射已保存: {output_path}")
        print(f"   共 {len(file_to_display)} 筆")

        # 顯示範例
        print("\n範例映射:")
        for i, (file_id, display_name) in enumerate(list(file_to_display.items())[:10], 1):
            print(f"  {i}. {file_id}")
            print(f"     -> {display_name}")

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("完成！")
    print("=" * 70)

if __name__ == '__main__':
    main()
