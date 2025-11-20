"""測試法令函釋上傳策略（不實際上傳）"""

import sys
from pathlib import Path

# 加入專案根目錄到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.storage.jsonl_handler import JSONLHandler
import json


def test_upload_strategy():
    """測試上傳策略"""

    logger.info("=" * 70)
    logger.info("測試法令函釋上傳策略")
    logger.info("=" * 70)

    # 讀取測試資料
    test_file = Path('data/law_interpretations_test/test_law_interpretations.jsonl')

    if not test_file.exists():
        logger.error(f"測試資料不存在: {test_file}")
        return

    items = []
    with open(test_file, 'r', encoding='utf-8') as f:
        for line in f:
            items.append(json.loads(line))

    logger.info(f"讀取 {len(items)} 筆測試資料\n")

    # 優先級定義（使用 law_ 前綴）
    priority_mapping = {
        'law_amendment': 0,
        'law_enactment': 0,
        'law_clarification': 0,
        'law_interpretation_decree': 0,
        'law_approval': 1,
        'law_publication': 1,  # 發布/公布型（原 announcement）
        'law_repeal': 2,
        'law_adjustment': 2,
        'law_notice': 2,
        'law_other': 3,
        'law_unknown': 3,
    }

    # 統計
    stats = {
        'pdf': 0,
        'markdown': 0,
        'skip': 0,
    }

    strategy_by_category = {}

    # 測試每個項目
    for i, item in enumerate(items, 1):
        item_id = item.get('id', 'unknown')
        title = item.get('title', '無標題')
        category = item.get('metadata', {}).get('category', 'unknown')
        attachments = item.get('attachments', [])
        priority = priority_mapping.get(category, 3)

        logger.info(f"[{i}] {item_id}")
        logger.info(f"  標題: {title[:60]}...")
        logger.info(f"  類型: {category} (P{priority})")
        logger.info(f"  附件數: {len(attachments)}")

        # 決定策略
        upload_type = None
        file_path = None

        # 修正型：只上傳對照表
        if category == 'law_amendment':
            comparison_table = None
            for att in attachments:
                if att.get('classification') == 'comparison_table':
                    comparison_table = att
                    break

            if comparison_table:
                logger.info(f"  → 策略: 上傳對照表 PDF")
                logger.info(f"     檔案: {comparison_table.get('name')}")
                upload_type = 'pdf'
                stats['pdf'] += 1
            else:
                logger.info(f"  → 策略: 跳過（無對照表）")
                upload_type = 'skip'
                stats['skip'] += 1

        # 訂定型 / 函釋型
        elif category in ['law_enactment', 'law_clarification', 'law_interpretation_decree']:
            if attachments:
                pdf_att = None
                for att in attachments:
                    if att.get('type') == 'pdf':
                        pdf_att = att
                        break

                if pdf_att:
                    logger.info(f"  → 策略: 上傳 PDF 附件")
                    logger.info(f"     檔案: {pdf_att.get('name')}")
                    upload_type = 'pdf'
                    stats['pdf'] += 1
                else:
                    logger.info(f"  → 策略: 生成並上傳 Markdown（無 PDF 附件）")
                    upload_type = 'markdown'
                    stats['markdown'] += 1
            else:
                logger.info(f"  → 策略: 生成並上傳 Markdown（無附件）")
                upload_type = 'markdown'
                stats['markdown'] += 1

        # 其他類型
        else:
            if attachments:
                pdf_att = None
                for att in attachments:
                    if att.get('type') == 'pdf':
                        pdf_att = att
                        break

                if pdf_att:
                    logger.info(f"  → 策略: 上傳 PDF 附件")
                    logger.info(f"     檔案: {pdf_att.get('name')}")
                    upload_type = 'pdf'
                    stats['pdf'] += 1
                else:
                    logger.info(f"  → 策略: 生成並上傳 Markdown（無 PDF 附件）")
                    upload_type = 'markdown'
                    stats['markdown'] += 1
            else:
                logger.info(f"  → 策略: 生成並上傳 Markdown（無附件）")
                upload_type = 'markdown'
                stats['markdown'] += 1

        # 記錄統計
        if category not in strategy_by_category:
            strategy_by_category[category] = {'pdf': 0, 'markdown': 0, 'skip': 0}

        strategy_by_category[category][upload_type] += 1

        logger.info("")

    # 顯示統計
    logger.info("=" * 70)
    logger.info("上傳策略統計")
    logger.info("=" * 70)

    logger.info(f"\n總計:")
    logger.info(f"  PDF: {stats['pdf']} 筆")
    logger.info(f"  Markdown: {stats['markdown']} 筆")
    logger.info(f"  跳過: {stats['skip']} 筆")

    logger.info(f"\n各類型策略:")
    for cat, cat_stats in sorted(strategy_by_category.items()):
        logger.info(f"  {cat}:")
        logger.info(f"    PDF: {cat_stats['pdf']}")
        logger.info(f"    Markdown: {cat_stats['markdown']}")
        logger.info(f"    跳過: {cat_stats['skip']}")

    logger.info("\n✓ 測試完成")


def main():
    """主函數"""
    try:
        test_upload_strategy()
    except Exception as e:
        logger.error(f"測試失敗: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
