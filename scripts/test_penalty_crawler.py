"""測試裁罰案件爬蟲"""

import sys
from pathlib import Path

# 加入專案根目錄到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.utils.config_loader import ConfigLoader
from src.crawlers.penalties import PenaltyCrawler
from src.storage.jsonl_handler import JSONLHandler
import json


def test_penalty_crawler():
    """測試裁罰案件爬蟲"""

    logger.info("=" * 70)
    logger.info("測試裁罰案件爬蟲")
    logger.info("=" * 70)

    # 1. 載入配置
    logger.info("\n[1/5] 載入配置")
    config_loader = ConfigLoader()
    config = config_loader.get_crawler_config()

    # 確保附件下載已啟用
    if not config.get('attachments', {}).get('download', False):
        logger.info("啟用附件下載")
        config.setdefault('attachments', {})['download'] = True

    logger.info(f"配置載入完成")

    # 2. 初始化爬蟲
    logger.info("\n[2/5] 初始化裁罰案件爬蟲")
    crawler = PenaltyCrawler(config)
    logger.info("✓ 爬蟲初始化成功")

    # 3. 爬取第一頁列表
    logger.info("\n[3/5] 爬取列表頁（第 1 頁）")
    items = crawler.crawl_page(page=1)

    if not items:
        logger.error("❌ 未找到任何裁罰案件")
        return False

    logger.info(f"✓ 找到 {len(items)} 筆裁罰案件")

    # 顯示前 3 筆
    logger.info("\n前 3 筆裁罰案件:")
    for i, item in enumerate(items[:3], 1):
        logger.info(f"\n  [{i}]")
        logger.info(f"  日期: {item.get('date')}")
        logger.info(f"  來源: {item.get('source_raw')}")
        logger.info(f"  標題: {item.get('title')[:60]}...")

    # 4. 爬取詳細頁（測試前 2 筆）
    logger.info("\n[4/5] 爬取詳細頁（測試前 2 筆）")

    detailed_items = []

    for i, item in enumerate(items[:2], 1):
        logger.info(f"\n處理第 {i} 筆...")
        logger.info(f"  標題: {item.get('title')[:50]}...")

        # 爬取詳細頁
        detail = crawler.fetch_detail(item['detail_url'], item)

        if detail:
            # 生成 ID
            detail['id'] = f"fsc_pen_{detail['date'].replace('-', '')}_{i:04d}"
            detail['data_type'] = 'penalty'

            detailed_items.append(detail)

            # 顯示 metadata
            metadata = detail.get('metadata', {})

            logger.info(f"  ✓ 爬取成功")
            logger.info(f"  發文字號: {metadata.get('doc_number', 'N/A')}")
            logger.info(f"  處分金額: {metadata.get('penalty_amount_text', 'N/A')}")

            penalized = metadata.get('penalized_entity', {})
            logger.info(f"  被處分人: {penalized.get('name', 'N/A')}")
            logger.info(f"  業別: {penalized.get('type', 'N/A')}")

            logger.info(f"  違規類型: {metadata.get('category', 'N/A')}")
            logger.info(f"  檢查報告: {metadata.get('inspection_report', 'N/A')}")

            legal_basis = metadata.get('legal_basis', [])
            logger.info(f"  法條依據: {len(legal_basis)} 條")
            for j, law in enumerate(legal_basis[:3], 1):
                logger.info(f"    {j}. {law[:60]}...")

            attachments = detail.get('attachments', [])
            logger.info(f"  附件數: {len(attachments)}")
            for j, att in enumerate(attachments, 1):
                logger.info(f"    {j}. {att.get('name')[:40]}... ({att.get('type')})")
                if att.get('downloaded'):
                    logger.info(f"       ✓ 已下載: {att.get('size_bytes', 0) / 1024:.1f} KB")

        else:
            logger.error(f"  ✗ 爬取失敗")

    # 5. 儲存測試結果
    logger.info("\n[5/5] 儲存測試結果")

    # 建立測試資料目錄
    test_data_dir = Path('data/penalties_test')
    test_data_dir.mkdir(parents=True, exist_ok=True)

    # 儲存為 JSONL
    output_file = test_data_dir / 'test_penalties.jsonl'
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in detailed_items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    logger.info(f"✓ 測試結果已儲存: {output_file}")
    logger.info(f"  共 {len(detailed_items)} 筆裁罰案件")

    # 6. 統計資訊
    logger.info("\n" + "=" * 70)
    logger.info("測試統計")
    logger.info("=" * 70)

    # 統計違規類型
    categories = {}
    for item in detailed_items:
        cat = item.get('metadata', {}).get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    logger.info("\n違規類型分布:")
    for cat, count in categories.items():
        logger.info(f"  {cat}: {count} 筆")

    # 統計來源單位
    sources = {}
    for item in detailed_items:
        src = item.get('metadata', {}).get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1

    logger.info("\n來源單位分布:")
    for src, count in sources.items():
        logger.info(f"  {src}: {count} 筆")

    # 統計附件
    total_attachments = sum(len(item.get('attachments', [])) for item in detailed_items)
    downloaded_attachments = sum(
        sum(1 for att in item.get('attachments', []) if att.get('downloaded'))
        for item in detailed_items
    )

    logger.info(f"\n附件統計:")
    logger.info(f"  總附件數: {total_attachments}")
    logger.info(f"  已下載: {downloaded_attachments}")

    logger.info("\n✓ 裁罰案件爬蟲測試完成")

    return True


def main():
    """主函數"""

    try:
        success = test_penalty_crawler()

        if success:
            logger.info("\n" + "=" * 70)
            logger.info("測試結果: ✓ 成功")
            logger.info("=" * 70)
            logger.info("\n下一步:")
            logger.info("  1. 檢查 data/penalties_test/test_penalties.jsonl")
            logger.info("  2. 檢查附件下載 data/attachments/penalties/")
            logger.info("  3. 如果測試成功，可以進行完整爬取")
        else:
            logger.error("\n測試結果: ✗ 失敗")

    except Exception as e:
        logger.error(f"\n測試過程發生錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
