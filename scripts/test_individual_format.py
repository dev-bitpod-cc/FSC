#!/usr/bin/env python3
"""測試個別檔案格式化 - 每篇公告獨立檔案"""

import sys
from pathlib import Path

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processor.markdown_formatter import BatchMarkdownFormatter
from src.storage.jsonl_handler import JSONLHandler
from src.utils.logger import logger


def main():
    """主程式"""
    logger.info("=" * 60)
    logger.info("測試個別檔案格式化")
    logger.info("=" * 60)

    # 初始化
    handler = JSONLHandler()
    formatter = BatchMarkdownFormatter()
    formatter.handler = handler

    # 格式化為獨立檔案
    result = formatter.format_individual_files(
        data_type='announcements',
        output_dir='data/markdown/individual'
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("格式化完成!")
    logger.info("=" * 60)
    logger.info(f"總項目數: {result['total_items']}")
    logger.info(f"建立檔案數: {result['created_files']}")
    logger.info(f"輸出目錄: {result['output_dir']}")

    # 顯示前 10 個檔案範例
    if result['files']:
        logger.info("")
        logger.info("檔案範例 (前 10 個):")
        for filepath in result['files']:
            filename = Path(filepath).name
            logger.info(f"  - {filename}")

    logger.info("")
    logger.info("=" * 60)
    logger.info("說明")
    logger.info("=" * 60)
    logger.info("現在每篇公告都是獨立的檔案,檔名包含:")
    logger.info("1. 公告 ID (例如: fsc_ann_20251112_0001)")
    logger.info("2. 來源單位 (例如: 銀行局、證券期貨局)")
    logger.info("3. 公告標題 (截取前 50 字元)")
    logger.info("")
    logger.info("這樣在 RAG 查詢時:")
    logger.info("✓ 使用者可以從檔名直接看出是哪篇公告")
    logger.info("✓ 不會有多個檔案包含不同公告的問題")
    logger.info("✓ 每個檔名都是唯一且有意義的")


if __name__ == '__main__':
    main()
