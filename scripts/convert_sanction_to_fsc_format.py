"""
將 Sanction 專案的裁罰資料轉換為 FSC 格式的 JSONL

Sanction 格式 → FSC 格式
"""

import json
import re
from pathlib import Path
from datetime import datetime


def parse_penalty_amount(amount_str):
    """解析罰款金額"""
    if not amount_str or amount_str == '(未提供)':
        return None, None

    # 提取數字
    match = re.search(r'(\d+(?:\.\d+)?)', str(amount_str))
    if match:
        amount = float(match.group(1))
        # 欄位名稱本身就是「罰款金額(萬元)」，所以純數字也是萬元
        # 統一轉換為元
        amount_in_yuan = int(amount * 10000)
        return amount_in_yuan, f"新臺幣{amount_in_yuan:,}元"

    return None, amount_str


def convert_sanction_to_fsc(sanction_json_path: str, output_jsonl_path: str):
    """
    轉換 Sanction JSON 到 FSC JSONL 格式

    Args:
        sanction_json_path: Sanction 的 fsc_penalties.json 路徑
        output_jsonl_path: 輸出的 JSONL 路徑
    """
    print(f"讀取 Sanction 資料: {sanction_json_path}")

    with open(sanction_json_path, 'r', encoding='utf-8') as f:
        sanction_data = json.load(f)

    print(f"讀取 {len(sanction_data)} 筆資料")

    # 轉換每筆資料
    fsc_data = []

    for item in sanction_data:
        # 解析罰款金額
        penalty_amount, penalty_amount_text = parse_penalty_amount(
            item.get('罰款金額(萬元)')
        )

        # 解析日期 (格式可能是 YYYY-MM-DD 或 YYYYMMDD)
        date_raw = item.get('裁處書發文日期', '')
        if len(date_raw) == 8 and date_raw.isdigit():
            # YYYYMMDD → YYYY-MM-DD
            date = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
        else:
            date = date_raw

        # 提取機構名稱
        institution = item.get('機構名稱', '未知機構')

        # 生成文件 ID
        doc_id = f"fsc_pen_{date.replace('-', '')}_{item.get('編號', '0000').zfill(4)}"

        # 建立 FSC 格式
        fsc_item = {
            'id': doc_id,
            'data_type': 'penalty',
            'page': 1,
            'list_index': item.get('編號', ''),
            'date': date,
            'source_raw': item.get('資料來源', ''),
            'title': item.get('標題', ''),
            'detail_url': item.get('詳細頁面', ''),
            'content': {
                'text': '',  # 從 txt 檔案讀取
                'html': ''
            },
            'attachments': [],
            'metadata': {
                'doc_number': '',  # 通常在內容中
                'penalized_entity': {
                    'name': institution,
                    'type': '',
                    'tax_id': ''
                },
                'penalty_amount': penalty_amount,
                'penalty_amount_text': penalty_amount_text,
                'violation': {
                    'summary': '',
                    'details': ''
                },
                'legal_basis': [],
                'source': '',  # 需要標準化
                'category': ''
            },
            'crawl_time': item.get('抓取時間', '')
        }

        # 讀取對應的 txt 檔案內容
        txt_file = item.get('檔案路徑', '')
        if txt_file:
            # 路徑是相對於 Sanction 專案根目錄的
            sanction_root = Path(sanction_json_path).parent.parent
            full_path = sanction_root / txt_file

            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    txt_content = f.read()
                    fsc_item['content']['text'] = txt_content
            else:
                print(f"警告: 找不到檔案 {full_path}")

        fsc_data.append(fsc_item)

    # 寫入 JSONL
    print(f"\n寫入 JSONL: {output_jsonl_path}")
    output_path = Path(output_jsonl_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for item in fsc_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"✓ 完成! 共轉換 {len(fsc_data)} 筆資料")
    print(f"✓ 輸出: {output_path}")

    return fsc_data


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='轉換 Sanction 資料到 FSC 格式')
    parser.add_argument(
        '--sanction-json',
        default='/Users/jjshen/Projects/Sanction/data/fsc_penalties.json',
        help='Sanction 的 fsc_penalties.json 路徑'
    )
    parser.add_argument(
        '--output',
        default='data/penalties/raw.jsonl',
        help='輸出的 JSONL 路徑'
    )

    args = parser.parse_args()

    try:
        data = convert_sanction_to_fsc(args.sanction_json, args.output)

        print("\n" + "=" * 80)
        print("轉換完成!")
        print("=" * 80)
        print(f"總筆數: {len(data)}")
        print(f"\n下一步:")
        print(f"  1. 生成優化檔案:")
        print(f"     python scripts/generate_optimized_plaintext.py --source penalties")
        print(f"  2. 上傳到 Gemini:")
        print(f"     python scripts/upload_optimized_to_gemini.py")

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
