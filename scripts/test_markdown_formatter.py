"""
測試 Markdown 格式化器
"""

import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processor.markdown_formatter import MarkdownFormatter, BatchMarkdownFormatter
from src.storage.jsonl_handler import JSONLHandler
from src.utils.logger import setup_logger

# 設定日誌
logger = setup_logger(level="INFO")


def main():
    """主程式"""
    logger.info("=" * 60)
    logger.info("測試 Markdown 格式化器")
    logger.info("=" * 60)

    try:
        # 讀取資料
        logger.info("讀取 JSONL 資料...")
        storage = JSONLHandler()
        items = list(storage.stream_read('announcements'))

        logger.info(f"讀取完成: {len(items)} 筆資料")

        if not items:
            logger.warning("沒有資料可供格式化")
            return

        # 初始化格式化器
        formatter = MarkdownFormatter()

        # 測試 1: 格式化單筆
        logger.info("\n" + "=" * 60)
        logger.info("測試 1: 格式化單筆公告")
        logger.info("=" * 60)

        first_item = items[0]
        single_md = formatter.format_announcement(first_item)

        output_dir = Path('data/markdown')
        output_dir.mkdir(parents=True, exist_ok=True)

        single_file = output_dir / 'sample_single.md'
        formatter.save_to_file(single_md, str(single_file))

        logger.info(f"單筆範例已儲存: {single_file}")
        logger.info(f"檔案大小: {len(single_md)} bytes")

        # 顯示前 500 字元
        logger.info("\n前 500 字元預覽:")
        logger.info("-" * 60)
        print(single_md[:500])
        logger.info("-" * 60)

        # 測試 2: 格式化前 3 筆 (含目錄)
        logger.info("\n" + "=" * 60)
        logger.info("測試 2: 格式化前 3 筆 (含目錄)")
        logger.info("=" * 60)

        batch_md = formatter.format_batch(items[:3], add_toc=True)
        batch_file = output_dir / 'sample_batch_3.md'
        formatter.save_to_file(batch_md, str(batch_file))

        logger.info(f"批次範例 (3筆) 已儲存: {batch_file}")
        logger.info(f"檔案大小: {len(batch_md)} bytes")

        # 測試 3: 格式化全部 (不含目錄)
        logger.info("\n" + "=" * 60)
        logger.info(f"測試 3: 格式化全部 {len(items)} 筆 (不含目錄)")
        logger.info("=" * 60)

        all_md = formatter.format_batch(items, add_toc=False)
        all_file = output_dir / 'all_announcements.md'
        formatter.save_to_file(all_md, str(all_file))

        logger.info(f"完整文檔已儲存: {all_file}")
        logger.info(f"檔案大小: {len(all_md):,} bytes ({len(all_md)/1024:.1f} KB)")

        # 測試 4: 按日期分組
        logger.info("\n" + "=" * 60)
        logger.info("測試 4: 按日期分組格式化")
        logger.info("=" * 60)

        batch_formatter = BatchMarkdownFormatter()
        by_date = batch_formatter.format_by_date(items)

        date_dir = output_dir / 'by_date'
        date_dir.mkdir(parents=True, exist_ok=True)

        for date, md_content in by_date.items():
            date_file = date_dir / f"{date}.md"
            batch_formatter.save_to_file(md_content, str(date_file))

        logger.info(f"按日期分組完成: {len(by_date)} 個檔案")
        logger.info(f"儲存目錄: {date_dir}")

        # 測試 5: 按來源分組
        logger.info("\n" + "=" * 60)
        logger.info("測試 5: 按來源單位分組格式化")
        logger.info("=" * 60)

        by_source = batch_formatter.format_by_source(items)

        source_dir = output_dir / 'by_source'
        source_dir.mkdir(parents=True, exist_ok=True)

        for source, md_content in by_source.items():
            source_file = source_dir / f"{source}.md"
            batch_formatter.save_to_file(md_content, str(source_file))
            logger.info(f"  {source}: {len(md_content):,} bytes")

        logger.info(f"按來源分組完成: {len(by_source)} 個檔案")
        logger.info(f"儲存目錄: {source_dir}")

        # 統計資訊
        logger.info("\n" + "=" * 60)
        logger.info("統計資訊")
        logger.info("=" * 60)
        logger.info(f"總文件數: {len(items)}")
        logger.info(f"總 Markdown 大小: {len(all_md):,} bytes ({len(all_md)/1024:.1f} KB)")
        logger.info(f"平均每筆大小: {len(all_md)//len(items):,} bytes")
        logger.info(f"按日期分檔: {len(by_date)} 個")
        logger.info(f"按來源分檔: {len(by_source)} 個")

        logger.info("\n" + "=" * 60)
        logger.info("測試完成!")
        logger.info("=" * 60)

        logger.info("\n輸出檔案位置:")
        logger.info(f"  單筆範例: {single_file}")
        logger.info(f"  批次範例: {batch_file}")
        logger.info(f"  完整文檔: {all_file}")
        logger.info(f"  按日期: {date_dir}/")
        logger.info(f"  按來源: {source_dir}/")

    except Exception as e:
        logger.error(f"測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
