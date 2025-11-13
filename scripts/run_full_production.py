#!/usr/bin/env python3
"""
全量生產環境爬取與上傳腳本

功能:
1. 爬取所有公告（約 7500 筆，500 頁）
2. 增量儲存到 JSONL（自動去重）
3. 產生 Markdown 檔案到暫存目錄
4. 上傳到 Gemini File Search Store
5. 驗證上傳完整性
6. 清理暫存檔案

特點:
- 詳細的進度 log（檔案: logs/fsc_crawler.log）
- 斷點續傳（已上傳的檔案會跳過）
- 錯誤重試機制
- 完整性驗證
"""

import sys
import shutil
import time
from pathlib import Path
from datetime import datetime

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.announcements import AnnouncementCrawler
from src.storage.jsonl_handler import JSONLHandler
from src.storage.index_manager import IndexManager
from src.processor.markdown_formatter import BatchMarkdownFormatter
from src.uploader.gemini_uploader import GeminiUploader
from src.utils.logger import setup_logger
from src.utils.config_loader import ConfigLoader
from dotenv import load_dotenv
import os
import re


def main():
    """主程式"""

    # ===== 初始化 =====
    print("=" * 80)
    print("金管會公告全量爬取與上傳 - 生產環境")
    print("=" * 80)
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"預計爬取: ~7,500 筆公告 (500 頁)")
    print(f"Log 檔案: logs/fsc_crawler.log")
    print("=" * 80)
    print()

    # 設定日誌
    logger = setup_logger(log_dir="logs", level="INFO")

    # 載入環境變數
    load_dotenv()

    # 載入配置
    config_loader = ConfigLoader()
    config = config_loader.load_yaml('crawler.yaml')

    # 參數
    api_key = os.getenv('GEMINI_API_KEY')
    store_name = os.getenv('FILE_SEARCH_STORE_NAME', 'fsc-announcements')
    temp_dir = Path('data/temp_markdown_full')

    if not api_key:
        logger.error("未設定 GEMINI_API_KEY")
        return 1

    try:
        # ===== 階段 1: 爬取公告 =====
        logger.info("=" * 80)
        logger.info("階段 1/5: 爬取公告資料")
        logger.info("=" * 80)

        crawler = AnnouncementCrawler(config)
        handler = JSONLHandler()
        index_mgr = IndexManager()

        # 檢查現有資料
        existing_count = handler.count_items('announcements')
        logger.info(f"現有資料: {existing_count} 筆")

        # 爬取所有頁面（1-500 頁，每頁 15 筆）
        logger.info("開始爬取... (預計約 30-60 分鐘)")
        logger.info("提示: 使用 'tail -f logs/fsc_crawler.log' 觀察進度")

        start_page = 1
        end_page = 500  # 全量爬取

        all_items = crawler.crawl_all(
            start_page=start_page,
            end_page=end_page
        )

        logger.info(f"爬取完成! 共取得 {len(all_items)} 筆公告")

        # 增量儲存（自動去重）
        logger.info("儲存資料並去重...")
        stats = handler.append_items(
            source='announcements',
            items=all_items,
            check_duplicates=True,
            update_index=True
        )

        logger.info(f"儲存完成: 新增 {stats['added']} 筆, 重複 {stats['duplicates']} 筆")
        logger.info(f"總計: {handler.count_items('announcements')} 筆公告")
        logger.info("✓ 階段 1 完成")
        logger.info("")

        # ===== 階段 2: 產生 Markdown 檔案 =====
        logger.info("=" * 80)
        logger.info("階段 2/5: 產生 Markdown 檔案")
        logger.info("=" * 80)

        # 清理舊的暫存目錄
        if temp_dir.exists():
            logger.info(f"清理舊的暫存目錄: {temp_dir}")
            shutil.rmtree(temp_dir)

        temp_dir.mkdir(parents=True, exist_ok=True)

        # 產生獨立 Markdown 檔案
        logger.info("產生獨立 Markdown 檔案... (預計約 5-10 分鐘)")
        formatter = BatchMarkdownFormatter()
        formatter.handler = handler

        result = formatter.format_individual_files(
            data_type='announcements',
            output_dir=str(temp_dir)
        )

        logger.info(f"產生完成: {result['created_files']} 個 Markdown 檔案")
        logger.info(f"輸出目錄: {result['output_dir']}")
        logger.info("✓ 階段 2 完成")
        logger.info("")

        # ===== 階段 3: 上傳到 Gemini =====
        logger.info("=" * 80)
        logger.info("階段 3/5: 上傳到 Gemini File Search")
        logger.info("=" * 80)
        logger.info(f"Store 名稱: {store_name}")
        logger.info("上傳中... (預計約 2-4 小時)")
        logger.info("提示: 已實作斷點續傳，可隨時中斷並重新執行")
        logger.info("")

        uploader = GeminiUploader(
            api_key=api_key,
            store_name=store_name,
            max_retries=3,
            retry_delay=2.0
        )

        upload_stats = uploader.upload_directory(
            directory=str(temp_dir),
            pattern="*.md",
            delay=1.0,  # 每個檔案間隔 1 秒
            skip_existing=True  # 跳過已上傳的檔案（斷點續傳）
        )

        logger.info("上傳完成!")
        logger.info(f"總檔案: {upload_stats['total_files']}")
        logger.info(f"已上傳: {upload_stats['uploaded_files']}")
        logger.info(f"跳過: {upload_stats['skipped_files']}")
        logger.info(f"失敗: {upload_stats['failed_files']}")
        logger.info("✓ 階段 3 完成")
        logger.info("")

        # ===== 階段 4: 驗證完整性 =====
        logger.info("=" * 80)
        logger.info("階段 4/5: 驗證上傳完整性")
        logger.info("=" * 80)

        report = uploader.verify_upload_completeness()

        logger.info(f"驗證結果:")
        logger.info(f"  總計: {report['total']}")
        logger.info(f"  成功: {report['successful']}")
        logger.info(f"  失敗: {report['failed']}")

        if report['failed'] > 0:
            logger.warning(f"有 {report['failed']} 個檔案上傳失敗:")
            for item in report['failed_files'][:20]:  # 顯示前 20 個
                logger.warning(f"  - {item['display_name']}: {item['error']}")

            logger.warning("請檢查錯誤並重新執行腳本（會自動跳過已上傳的檔案）")
            success = False
        else:
            logger.info("✓ 所有檔案上傳成功!")
            success = True

        logger.info("✓ 階段 4 完成")
        logger.info("")

        # ===== 階段 5: 清理暫存檔案 =====
        logger.info("=" * 80)
        logger.info("階段 5/5: 清理暫存檔案")
        logger.info("=" * 80)

        if temp_dir.exists():
            file_count = len(list(temp_dir.glob('*.md')))
            shutil.rmtree(temp_dir)
            logger.info(f"已刪除 {file_count} 個暫存 Markdown 檔案")
            logger.info(f"已刪除暫存目錄: {temp_dir}")

        logger.info("✓ 階段 5 完成")
        logger.info("")

        # ===== 完成 =====
        logger.info("=" * 80)
        if success:
            logger.info("✓ 全量爬取與上傳完成!")
        else:
            logger.warning("⚠ 流程完成，但有部分檔案上傳失敗")
            logger.warning("請重新執行腳本處理失敗的檔案")
        logger.info("=" * 80)

        # 顯示摘要
        logger.info("")
        logger.info("摘要:")
        logger.info(f"  爬取公告: {len(all_items)} 筆")
        logger.info(f"  新增資料: {stats['added']} 筆")
        logger.info(f"  重複資料: {stats['duplicates']} 筆")
        logger.info(f"  總計資料: {handler.count_items('announcements')} 筆")
        logger.info(f"  Markdown 檔案: {result['created_files']} 個")
        logger.info(f"  上傳成功: {upload_stats['uploaded_files']} 個")
        logger.info(f"  上傳失敗: {upload_stats['failed_files']} 個")
        logger.info(f"  Store 名稱: {store_name}")
        logger.info(f"  Store ID: {uploader.store_id}")

        end_time = datetime.now()
        logger.info(f"  完成時間: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        print()
        print("=" * 80)
        print("流程執行完畢，詳細記錄請查看: logs/fsc_crawler.log")
        print("=" * 80)

        return 0 if success else 1

    except KeyboardInterrupt:
        logger.warning("使用者中斷執行")
        logger.info("提示: 可重新執行腳本，已上傳的檔案會被跳過（斷點續傳）")
        return 130

    except Exception as e:
        logger.error(f"執行過程發生錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == '__main__':
    sys.exit(main())
