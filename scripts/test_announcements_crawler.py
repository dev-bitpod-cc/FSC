"""測試重要公告爬蟲（修正後版本）"""

import sys
from pathlib import Path

# 加入專案根目錄到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.utils.config_loader import ConfigLoader
from src.crawlers.announcements import AnnouncementCrawler
import json


def test_announcements_crawler(max_pages: int = 3):
    """
    測試重要公告爬蟲

    Args:
        max_pages: 測試頁數（預設 3 頁，約 45 筆）
    """
    logger.info("=" * 70)
    logger.info("測試重要公告爬蟲（修正後版本）")
    logger.info("=" * 70)

    # 1. 載入配置
    logger.info("\n[1/3] 載入配置")
    config_loader = ConfigLoader()
    config = config_loader.get_crawler_config()

    # 停用附件下載（測試階段）
    config['attachments'] = config.get('attachments', {})
    config['attachments']['download'] = False
    logger.info("✓ 配置載入完成（附件下載已停用）")

    # 2. 初始化爬蟲
    logger.info("\n[2/3] 初始化重要公告爬蟲")
    crawler = AnnouncementCrawler(config)
    logger.info("✓ 爬蟲初始化成功")

    # 3. 爬取測試頁面
    logger.info(f"\n[3/3] 爬取前 {max_pages} 頁")
    logger.info("-" * 70)

    all_items = []
    for page in range(1, max_pages + 1):
        logger.info(f"\n爬取第 {page} 頁...")
        items = crawler.crawl_page(page)

        if items:
            logger.info(f"✓ 第 {page} 頁: {len(items)} 筆")
            all_items.extend(items)
        else:
            logger.warning(f"✗ 第 {page} 頁: 無資料")

    logger.info(f"\n總計: {len(all_items)} 筆")

    # 4. 統計分析
    logger.info("\n" + "=" * 70)
    logger.info("統計分析")
    logger.info("=" * 70)

    # 統計類型分布
    categories = {}
    for item in all_items:
        cat = item.get('metadata', {}).get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    logger.info("\n類型分布:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {cat or 'None'}: {count} 筆")

    # 統計來源分布
    sources = {}
    for item in all_items:
        src = item.get('metadata', {}).get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1

    logger.info("\n來源分布:")
    for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {src}: {count} 筆")

    # 統計附件
    total_attachments = 0
    items_with_attachments = 0
    irrelevant_attachments = 0

    blacklist_keywords = ['失智者', '永續發展', 'SDGs', 'VNR']

    for item in all_items:
        attachments = item.get('attachments', [])
        if attachments:
            items_with_attachments += 1
            total_attachments += len(attachments)

            # 檢查是否有誤抓的附件
            for att in attachments:
                att_name = att.get('name', '')
                if any(keyword in att_name for keyword in blacklist_keywords):
                    irrelevant_attachments += 1
                    logger.warning(f"⚠️ 發現不相關附件: {att_name} (ID: {item['id']})")

    logger.info(f"\n附件統計:")
    logger.info(f"  有附件的公告: {items_with_attachments} / {len(all_items)} ({items_with_attachments/len(all_items)*100:.1f}%)")
    logger.info(f"  總附件數: {total_attachments}")
    logger.info(f"  平均每筆: {total_attachments/len(all_items):.1f} 個")
    logger.info(f"  誤抓附件數: {irrelevant_attachments}")
    logger.info(f"  誤抓率: {irrelevant_attachments/len(all_items)*100:.1f}% (目標: 0%)")

    # 5. 顯示範例資料
    logger.info("\n" + "=" * 70)
    logger.info("範例資料（前 3 筆）")
    logger.info("=" * 70)

    for i, item in enumerate(all_items[:3], 1):
        logger.info(f"\n[{i}] {item['id']}")
        logger.info(f"  日期: {item['date']}")
        logger.info(f"  來源: {item.get('metadata', {}).get('source', 'N/A')}")
        logger.info(f"  標題: {item['title'][:60]}...")
        logger.info(f"  類型: {item.get('metadata', {}).get('category', 'N/A')}")
        logger.info(f"  附件數: {len(item.get('attachments', []))}")

        if item.get('attachments'):
            logger.info(f"  附件清單:")
            for att in item['attachments']:
                logger.info(f"    - {att['name']} ({att['type']})")

    # 6. 儲存測試結果
    logger.info("\n" + "=" * 70)
    logger.info("儲存測試結果")
    logger.info("=" * 70)

    output_dir = Path('data/announcements_test')
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / 'test_results.jsonl'
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in all_items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    logger.info(f"✓ 測試結果已儲存: {output_file}")

    # 7. 驗證結果
    logger.info("\n" + "=" * 70)
    logger.info("驗證結果")
    logger.info("=" * 70)

    success = True

    # 驗證 1: 附件誤抓率應為 0%
    if irrelevant_attachments > 0:
        logger.error(f"✗ 附件誤抓率過高: {irrelevant_attachments/len(all_items)*100:.1f}% (目標: 0%)")
        success = False
    else:
        logger.info(f"✓ 附件誤抓率: 0% (目標達成！)")

    # 驗證 2: 類型識別率
    identified_count = sum(1 for item in all_items if item.get('metadata', {}).get('category'))
    identification_rate = identified_count / len(all_items) * 100

    if identification_rate < 50:
        logger.warning(f"⚠️ 類型識別率較低: {identification_rate:.1f}% (建議: >50%)")
    else:
        logger.info(f"✓ 類型識別率: {identification_rate:.1f}%")

    # 驗證 3: 檢查是否有 ann_regulation（「有關」開頭）
    regulation_count = categories.get('ann_regulation', 0)
    if regulation_count == 0:
        logger.warning(f"⚠️ 未發現 ann_regulation 類型（一般公告（令））")
    else:
        logger.info(f"✓ 發現 ann_regulation: {regulation_count} 筆")

    logger.info("\n" + "=" * 70)
    if success:
        logger.info("✓ 測試通過！")
    else:
        logger.error("✗ 測試失敗，需要修正")
    logger.info("=" * 70)


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='測試重要公告爬蟲')
    parser.add_argument('--pages', type=int, default=3,
                        help='測試頁數（預設：3）')

    args = parser.parse_args()

    try:
        test_announcements_crawler(max_pages=args.pages)
    except Exception as e:
        logger.error(f"\n測試過程發生錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
