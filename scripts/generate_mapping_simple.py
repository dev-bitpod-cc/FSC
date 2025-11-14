"""
從原始數據生成臨時映射（暫不使用 file_id）

由於上傳日誌不在 logs/ 目錄中，先從原始數據生成格式映射作為參考
之後可手動或通過 API 列表獲取 file_id
"""

import json
from pathlib import Path

def main():
    print("=" * 70)
    print("從原始數據生成裁罰案件格式映射")
    print("=" * 70)

    raw_data_path = Path('data/penalties/raw.jsonl')
    output_path = Path('data/penalty_format_mapping.json')

    print("\n讀取原始數據...")
    format_mapping = {}

    with open(raw_data_path, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f, 1):
            data = json.loads(line.strip())

            doc_id = data.get('id', '')  # fsc_pen_20250508_0005
            date = data.get('date', '')
            source = data.get('source', '')

            # 提取被處分對象
            metadata = data.get('metadata', {})
            target = metadata.get('target', '').strip()

            if not target:
                # 從標題提取
                title = data.get('title', '')
                # 嘗試提取公司名稱
                for separator in ['辦理', '因', '違反', '核有', '未依']:
                    if separator in title:
                        target = title.split(separator)[0].strip()
                        break
                if not target:
                    target = title[:30].strip()  # 取前30字符

            if date and source and target:
                display_name = f"{date}_{source}_{target}"
                format_mapping[doc_id] = display_name

            if idx % 100 == 0:
                print(f"  已處理 {idx} 筆...")

    print(f"\n✓ 成功生成 {len(format_mapping)} 筆格式映射")

    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(format_mapping, f, ensure_ascii=False, indent=2)

    print(f"✅ 映射已保存: {output_path}")
    print(f"   共 {len(format_mapping)} 筆")

    # 顯示範例
    print("\n範例映射 (doc_id -> 顯示名稱):")
    for i, (doc_id, display_name) in enumerate(list(format_mapping.items())[:10], 1):
        print(f"  {i}. {doc_id}")
        print(f"     -> {display_name}")

    print("\n" + "=" * 70)
    print("注意：這是 doc_id 映射，不是 file_id 映射")
    print("需要從 Gemini API 查詢 file_id 才能用於前端")
    print("=" * 70)

if __name__ == '__main__':
    main()
