#!/usr/bin/env python3
"""測試智慧上傳器 (自動分割、重試、驗證、清理)"""

import sys
from pathlib import Path

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.uploader.gemini_uploader import GeminiUploader
from src.utils.logger import logger
from dotenv import load_dotenv
import os


def main():
    """主程式"""
    # 載入環境變數
    load_dotenv()

    # 檢查 API Key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("未設定 GEMINI_API_KEY,請在 .env 檔案中設定")
        return

    logger.info("=" * 60)
    logger.info("測試智慧上傳器 (自動分割、重試、驗證、清理)")
    logger.info("=" * 60)

    # 初始化上傳器
    uploader = GeminiUploader(
        api_key=api_key,
        store_name='fsc-announcements',
        max_file_size_kb=100,  # 100 KB 以上自動分割
        max_items_per_split=22,  # 每個分割檔案 22 個項目
        max_retries=3,  # 最多重試 3 次
        retry_delay=2.0  # 初始重試延遲 2 秒
    )

    logger.info("")
    logger.info("配置:")
    logger.info(f"- Store 名稱: fsc-announcements")
    logger.info(f"- 檔案大小上限: 100 KB")
    logger.info(f"- 每分割項目數: 22")
    logger.info(f"- 最大重試次數: 3")
    logger.info(f"- 重試延遲基數: 2.0 秒")
    logger.info("")

    # 測試上傳目錄
    markdown_dir = project_root / 'data' / 'markdown' / 'by_source'

    if not markdown_dir.exists():
        logger.error(f"目錄不存在: {markdown_dir}")
        return

    logger.info(f"上傳目錄: {markdown_dir}")
    logger.info("")

    # 執行上傳 (自動分割、重試、驗證、清理)
    try:
        stats = uploader.upload_directory(
            directory=str(markdown_dir),
            pattern='*.md',
            delay=1.0,  # 每次上傳間隔 1 秒
            skip_existing=True,  # 跳過已上傳的檔案
            auto_split=True,  # 自動分割大檔案
            auto_cleanup=True  # 完成後清理分割檔案
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("上傳完成!")
        logger.info("=" * 60)
        logger.info(f"總檔案數: {stats['total_files']}")
        logger.info(f"成功上傳: {stats['uploaded_files']}")
        logger.info(f"失敗: {stats['failed_files']}")
        logger.info(f"跳過 (已上傳): {stats['skipped_files']}")
        logger.info(f"分割檔案數: {stats['split_files']}")
        logger.info(f"總位元組數: {stats['total_bytes']:,} bytes")

        # 驗證完整性
        logger.info("")
        logger.info("=" * 60)
        logger.info("驗證上傳完整性")
        logger.info("=" * 60)

        report = uploader.verify_upload_completeness()
        logger.info(f"總計: {report['total']}")
        logger.info(f"成功: {report['successful']}")
        logger.info(f"失敗: {report['failed']}")

        # 顯示成功上傳的檔案
        if report['successful_files']:
            logger.info("")
            logger.info("成功上傳的檔案:")
            for item in report['successful_files']:
                logger.info(f"  ✓ {item['display_name']}")

        # 顯示失敗的檔案
        if report['failed_files']:
            logger.info("")
            logger.warning("失敗的檔案:")
            for item in report['failed_files']:
                logger.warning(f"  ✗ {item['display_name']}: {item['error']}")

        # 取得失敗的上傳
        failed_uploads = uploader.get_failed_uploads()
        if failed_uploads:
            logger.info("")
            logger.info("=" * 60)
            logger.info("需要手動處理的失敗檔案")
            logger.info("=" * 60)
            for item in failed_uploads:
                logger.info(f"檔案: {item['filepath']}")
                logger.info(f"  錯誤: {item['error']}")
                logger.info("")

    except Exception as e:
        logger.error(f"上傳過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
