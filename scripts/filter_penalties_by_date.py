#!/usr/bin/env python3
"""
篩選 2012-01-01 之後的裁罰案件資料

目的：從 630 筆完整資料中篩選出 2012-01-01 之後的案件，
      以便與 Sanction 的 490 筆資料進行比較。
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 加入專案根目錄
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


def filter_penalties_by_date(
    input_jsonl: str = 'data/penalties/raw.jsonl',
    output_jsonl: str = 'data/penalties/penalties_2012plus.jsonl',
    cutoff_date: str = '2012-01-01'
) -> Dict[str, Any]:
    """
    篩選指定日期之後的裁罰案件

    Args:
        input_jsonl: 輸入的 JSONL 路徑（630 筆完整資料）
        output_jsonl: 輸出的 JSONL 路徑（2012+ 資料）
        cutoff_date: 截止日期（包含此日期）

    Returns:
        統計資訊
    """
    logger.info("=" * 80)
    logger.info("篩選裁罰案件資料")
    logger.info("=" * 80)
    logger.info(f"\n輸入檔案: {input_jsonl}")
    logger.info(f"輸出檔案: {output_jsonl}")
    logger.info(f"截止日期: >= {cutoff_date}")

    # 解析截止日期
    cutoff = datetime.strptime(cutoff_date, '%Y-%m-%d')

    # 讀取所有資料
    input_path = Path(input_jsonl)
    if not input_path.exists():
        logger.error(f"找不到輸入檔案: {input_path}")
        sys.exit(1)

    all_items = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                try:
                    item = json.loads(line)
                    all_items.append(item)
                except json.JSONDecodeError as e:
                    logger.warning(f"第 {line_no} 行 JSON 解析失敗: {e}")
                    continue

    logger.info(f"\n讀取 {len(all_items)} 筆資料")

    # 篩選
    filtered_items = []
    skipped_items = []
    invalid_dates = []

    for item in all_items:
        item_date_str = item.get('date', '')

        if not item_date_str:
            invalid_dates.append(item.get('id', 'unknown'))
            continue

        try:
            item_date = datetime.strptime(item_date_str, '%Y-%m-%d')

            if item_date >= cutoff:
                filtered_items.append(item)
            else:
                skipped_items.append({
                    'id': item.get('id'),
                    'date': item_date_str,
                    'title': item.get('title', '')[:50]
                })

        except ValueError as e:
            logger.warning(f"日期格式錯誤: {item_date_str} - {e}")
            invalid_dates.append(item.get('id', 'unknown'))
            continue

    # 按日期排序（新到舊）
    filtered_items.sort(key=lambda x: x.get('date', ''), reverse=True)

    # 寫入篩選後的資料
    output_path = Path(output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for item in filtered_items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    # 統計
    logger.info("\n" + "=" * 80)
    logger.info("篩選完成")
    logger.info("=" * 80)
    logger.info(f"\n總筆數: {len(all_items)}")
    logger.info(f"符合條件 (>= {cutoff_date}): {len(filtered_items)}")
    logger.info(f"早於截止日期: {len(skipped_items)}")
    logger.info(f"日期無效: {len(invalid_dates)}")

    # 日期範圍
    if filtered_items:
        dates = [item.get('date') for item in filtered_items if item.get('date')]
        logger.info(f"\n篩選後的日期範圍:")
        logger.info(f"  最早: {min(dates)}")
        logger.info(f"  最新: {max(dates)}")

    # 來源分布
    source_dist = {}
    for item in filtered_items:
        source = item.get('metadata', {}).get('source', 'unknown')
        source_dist[source] = source_dist.get(source, 0) + 1

    logger.info(f"\n來源分布:")
    for source, count in sorted(source_dist.items(), key=lambda x: x[1], reverse=True):
        pct = count / len(filtered_items) * 100
        logger.info(f"  {source}: {count} ({pct:.1f}%)")

    # 顯示被跳過的前 10 筆
    if skipped_items:
        logger.info(f"\n跳過的案件（前 10 筆）:")
        for item in skipped_items[:10]:
            logger.info(f"  {item['date']} - {item['id']}: {item['title']}")

        if len(skipped_items) > 10:
            logger.info(f"  ... 還有 {len(skipped_items) - 10} 筆")

    logger.info(f"\n✅ 已儲存: {output_path}")

    return {
        'total': len(all_items),
        'filtered': len(filtered_items),
        'skipped': len(skipped_items),
        'invalid_dates': len(invalid_dates),
        'output_file': str(output_path),
        'date_range': {
            'min': min(dates) if filtered_items else None,
            'max': max(dates) if filtered_items else None
        },
        'source_distribution': source_dist
    }


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='篩選 2012-01-01 之後的裁罰案件')
    parser.add_argument(
        '--input',
        default='data/penalties/raw.jsonl',
        help='輸入的 JSONL 路徑'
    )
    parser.add_argument(
        '--output',
        default='data/penalties/penalties_2012plus.jsonl',
        help='輸出的 JSONL 路徑'
    )
    parser.add_argument(
        '--cutoff-date',
        default='2012-01-01',
        help='截止日期 (格式: YYYY-MM-DD)'
    )

    args = parser.parse_args()

    try:
        stats = filter_penalties_by_date(
            args.input,
            args.output,
            args.cutoff_date
        )

        # 驗證結果
        logger.info("\n" + "=" * 80)
        logger.info("驗證結果")
        logger.info("=" * 80)

        # 與 Sanction 的 490 筆比較
        sanction_count = 490
        diff = stats['filtered'] - sanction_count

        logger.info(f"\nSanction 資料: {sanction_count} 筆")
        logger.info(f"FSC 篩選後: {stats['filtered']} 筆")
        logger.info(f"差異: {diff:+d} 筆")

        if abs(diff) <= 10:
            logger.info("✅ 數量接近，符合預期")
        else:
            logger.warning(f"⚠️  差異較大 ({diff} 筆)，可能需要進一步調查")

    except Exception as e:
        logger.error(f"\n❌ 錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    # 設定日誌
    logger.add(
        "logs/filter_penalties_by_date.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG"
    )

    main()
