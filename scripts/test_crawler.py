"""
測試爬蟲 - 爬取前 3 頁 (約 45 筆)
"""

import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawlers.announcements import AnnouncementCrawler
from src.storage.jsonl_handler import JSONLHandler
from src.storage.index_manager import IndexManager
from src.utils.logger import setup_logger
from src.utils.config_loader import ConfigLoader

# 設定日誌
logger = setup_logger(level="INFO")


def main():
    """主程式"""
    logger.info("=" * 60)
    logger.info("開始測試爬蟲 - 爬取前 3 頁")
    logger.info("=" * 60)

    try:
        # 載入配置
        config_loader = ConfigLoader()
        crawler_config = config_loader.get_crawler_config()

        # 初始化爬蟲
        logger.info("初始化 AnnouncementCrawler...")
        crawler = AnnouncementCrawler(crawler_config)

        # 爬取前 3 頁
        logger.info("開始爬取前 3 頁...")
        items = crawler.crawl_all(
            start_page=1,
            end_page=3,
            fetch_detail=True
        )

        logger.info(f"爬取完成! 共取得 {len(items)} 筆資料")

        if items:
            # 儲存到 JSONL
            logger.info("儲存資料到 JSONL...")
            storage = JSONLHandler()
            storage.write_items('announcements', items, mode='w')  # 覆寫模式

            # 建立索引
            logger.info("建立索引...")
            index_mgr = IndexManager()
            index_mgr.build_index('announcements', items)

            # 顯示統計
            metadata = index_mgr.load_metadata('announcements')
            logger.info(f"統計資訊:")
            logger.info(f"  總筆數: {metadata['total_count']}")
            logger.info(f"  日期範圍: {metadata['date_range']}")

            # 顯示前 3 筆
            logger.info("\n前 3 筆資料:")
            for i, item in enumerate(items[:3], 1):
                logger.info(f"\n第 {i} 筆:")
                logger.info(f"  ID: {item.get('id')}")
                logger.info(f"  日期: {item.get('date')}")
                logger.info(f"  來源: {item.get('source_raw')}")
                logger.info(f"  標題: {item.get('title', '')[:60]}...")
                logger.info(f"  附件數: {len(item.get('attachments', []))}")

        else:
            logger.warning("未取得任何資料")

        logger.info("\n" + "=" * 60)
        logger.info("測試完成!")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("使用者中斷")

    except Exception as e:
        logger.error(f"測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
