#!/usr/bin/env python3
"""
將 FSC-Penalties-Deploy 的法規資訊合併到當前的 file_mapping.json

比對策略：
1. 優先用 original_url（最可靠）
2. 若無 URL，用 date + institution（次可靠）
3. 記錄比對結果和未比對到的案件
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# 加入專案根目錄
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


def normalize_institution(name: str) -> str:
    """標準化機構名稱（移除常見後綴）"""
    if not name:
        return ''

    # 移除常見後綴
    suffixes = ['股份有限公司', '有限公司', '銀行', '保險', '證券', '投信', '投顧']
    normalized = name
    for suffix in suffixes:
        normalized = normalized.replace(suffix, '')

    return normalized.strip()


def match_by_url(current_item: Dict, deploy_mapping: Dict) -> Tuple[str, Dict]:
    """用 original_url 比對"""
    current_url = current_item.get('original_url', '')

    if not current_url:
        return None, {}

    for doc_id, deploy_item in deploy_mapping.items():
        deploy_url = deploy_item.get('original_url', '')
        if current_url == deploy_url:
            return doc_id, deploy_item

    return None, {}


def match_by_date_institution(current_item: Dict, deploy_mapping: Dict) -> Tuple[str, Dict]:
    """用 date + institution 比對"""
    current_date = current_item.get('date', '')
    current_inst = normalize_institution(current_item.get('institution', ''))

    if not current_date or not current_inst:
        return None, {}

    matches = []

    for doc_id, deploy_item in deploy_mapping.items():
        deploy_date = deploy_item.get('date', '')
        deploy_inst = normalize_institution(deploy_item.get('institution', ''))

        if current_date == deploy_date and current_inst == deploy_inst:
            matches.append((doc_id, deploy_item))

    # 如果只有一個匹配，返回
    if len(matches) == 1:
        return matches[0]

    # 多個匹配或無匹配
    return None, {}


def merge_law_info(
    current_mapping: Dict,
    deploy_mapping: Dict,
    output_path: str = 'data/penalties/file_mapping.json'
) -> Dict[str, Any]:
    """
    合併法規資訊

    Args:
        current_mapping: 當前的 file_mapping（490 筆，無法規）
        deploy_mapping: Deploy 的 file_mapping（495 筆，有法規）
        output_path: 輸出路徑

    Returns:
        統計資訊
    """
    logger.info("=" * 80)
    logger.info("合併法規資訊")
    logger.info("=" * 80)
    logger.info(f"\n當前資料: {len(current_mapping)} 筆")
    logger.info(f"Deploy 資料: {len(deploy_mapping)} 筆")

    stats = {
        'matched_by_url': 0,
        'matched_by_date_inst': 0,
        'not_matched': 0,
        'laws_copied': 0,
        'unmatched_items': []
    }

    # 逐一比對
    for current_id, current_item in current_mapping.items():
        # 策略1: 用 URL 比對
        matched_id, matched_item = match_by_url(current_item, deploy_mapping)

        if matched_item:
            stats['matched_by_url'] += 1
        else:
            # 策略2: 用 date + institution 比對
            matched_id, matched_item = match_by_date_institution(current_item, deploy_mapping)

            if matched_item:
                stats['matched_by_date_inst'] += 1

        # 如果有匹配，複製法規資訊
        if matched_item:
            applicable_laws = matched_item.get('applicable_laws', [])
            law_links = matched_item.get('law_links', {})

            if applicable_laws:
                current_item['applicable_laws'] = applicable_laws
                current_item['law_links'] = law_links
                stats['laws_copied'] += 1

                logger.debug(f"✓ {current_id} 匹配到 {matched_id}，複製 {len(applicable_laws)} 個法規")
        else:
            stats['not_matched'] += 1
            stats['unmatched_items'].append({
                'id': current_id,
                'date': current_item.get('date'),
                'institution': current_item.get('institution'),
                'title': current_item.get('title', '')[:50]
            })
            logger.warning(f"✗ {current_id} 無法匹配: {current_item.get('date')} {current_item.get('institution')}")

    # 儲存合併後的 mapping
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(current_mapping, f, ensure_ascii=False, indent=2)

    # 輸出統計
    logger.info("\n" + "=" * 80)
    logger.info("合併完成")
    logger.info("=" * 80)
    logger.info(f"\n比對統計:")
    logger.info(f"  透過 URL 匹配: {stats['matched_by_url']}")
    logger.info(f"  透過 日期+機構 匹配: {stats['matched_by_date_inst']}")
    logger.info(f"  無法匹配: {stats['not_matched']}")
    logger.info(f"\n法規複製:")
    logger.info(f"  成功複製法規: {stats['laws_copied']} 筆")

    if stats['unmatched_items']:
        logger.info(f"\n未匹配的案件 ({len(stats['unmatched_items'])} 筆):")
        for item in stats['unmatched_items'][:10]:
            logger.info(f"  - {item['date']} {item['institution']}: {item['title']}")

        if len(stats['unmatched_items']) > 10:
            logger.info(f"  ... 還有 {len(stats['unmatched_items']) - 10} 筆")

    logger.info(f"\n✅ 已儲存: {output_path}")

    return stats


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='合併 Deploy 的法規資訊到當前 file_mapping')
    parser.add_argument(
        '--current',
        default='data/penalties/file_mapping.json',
        help='當前的 file_mapping.json 路徑'
    )
    parser.add_argument(
        '--deploy',
        default='/Users/jjshen/Projects/FSC-Penalties-Deploy/data/penalties/file_mapping.json',
        help='Deploy 的 file_mapping.json 路徑'
    )
    parser.add_argument(
        '--output',
        default='data/penalties/file_mapping.json',
        help='輸出的 file_mapping.json 路徑'
    )

    args = parser.parse_args()

    try:
        # 讀取兩個 file_mapping
        logger.info(f"讀取當前 file_mapping: {args.current}")
        with open(args.current, 'r', encoding='utf-8') as f:
            current_mapping = json.load(f)

        logger.info(f"讀取 Deploy file_mapping: {args.deploy}")
        with open(args.deploy, 'r', encoding='utf-8') as f:
            deploy_mapping = json.load(f)

        # 合併
        stats = merge_law_info(current_mapping, deploy_mapping, args.output)

        # 驗證結果
        logger.info("\n" + "=" * 80)
        logger.info("驗證結果")
        logger.info("=" * 80)

        with open(args.output, 'r', encoding='utf-8') as f:
            result_mapping = json.load(f)

        with_laws = sum(1 for item in result_mapping.values() if item.get('applicable_laws'))
        logger.info(f"包含法規的案件: {with_laws}/{len(result_mapping)} ({with_laws/len(result_mapping)*100:.1f}%)")

    except Exception as e:
        logger.error(f"\n❌ 錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    # 設定日誌
    logger.add(
        "logs/merge_laws_from_deploy.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG"
    )

    main()
