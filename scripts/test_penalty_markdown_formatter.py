"""測試裁罰案件 Markdown 格式化器"""

import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processor.penalty_markdown_formatter import PenaltyMarkdownFormatter, BatchPenaltyMarkdownFormatter
from src.storage.jsonl_handler import JSONLHandler
from loguru import logger

# 設定日誌
logger.remove()
logger.add(sys.stderr, level="INFO")


def main():
    """主程式"""
    logger.info("=" * 70)
    logger.info("測試裁罰案件 Markdown 格式化器")
    logger.info("=" * 70)

    try:
        # 讀取測試資料
        logger.info("\n[1/6] 讀取測試資料")

        test_file = Path('data/penalties_test/test_penalties.jsonl')

        if not test_file.exists():
            logger.error(f"測試資料檔案不存在: {test_file}")
            logger.info("請先執行 python scripts/test_penalty_crawler.py")
            return

        # 讀取 JSONL
        items = []
        with open(test_file, 'r', encoding='utf-8') as f:
            import json
            for line in f:
                if line.strip():
                    items.append(json.loads(line))

        logger.info(f"✓ 讀取完成: {len(items)} 筆裁罰案件")

        if not items:
            logger.warning("沒有資料可供格式化")
            return

        # 初始化格式化器
        formatter = PenaltyMarkdownFormatter()

        # 測試 1: 格式化單筆
        logger.info("\n[2/6] 測試單筆案件格式化")
        logger.info("=" * 70)

        first_item = items[0]
        single_md = formatter.format_penalty(first_item)

        output_dir = Path('data/markdown/penalties_test')
        output_dir.mkdir(parents=True, exist_ok=True)

        single_file = output_dir / 'sample_single_penalty.md'
        formatter.save_to_file(single_md, str(single_file))

        logger.info(f"✓ 單筆範例已儲存: {single_file}")
        logger.info(f"  檔案大小: {len(single_md)} bytes")

        # 顯示前 800 字元
        logger.info("\n前 800 字元預覽:")
        logger.info("-" * 70)
        print(single_md[:800])
        logger.info("-" * 70)

        # 測試 2: 格式化全部 (含目錄)
        logger.info("\n[3/6] 測試批次格式化 (含目錄)")
        logger.info("=" * 70)

        batch_md = formatter.format_batch(items, add_toc=True)
        batch_file = output_dir / 'test_penalties_batch.md'
        formatter.save_to_file(batch_md, str(batch_file))

        logger.info(f"✓ 批次文檔已儲存: {batch_file}")
        logger.info(f"  檔案大小: {len(batch_md):,} bytes ({len(batch_md)/1024:.1f} KB)")

        # 測試 3: 按日期分組
        logger.info("\n[4/6] 測試按日期分組")
        logger.info("=" * 70)

        batch_formatter = BatchPenaltyMarkdownFormatter()
        by_date = batch_formatter.format_by_date(items)

        date_dir = output_dir / 'by_date'
        date_dir.mkdir(parents=True, exist_ok=True)

        for date, md_content in by_date.items():
            date_file = date_dir / f"{date}.md"
            batch_formatter.save_to_file(md_content, str(date_file))
            logger.info(f"  {date}: {len(md_content):,} bytes")

        logger.info(f"✓ 按日期分組完成: {len(by_date)} 個檔案")

        # 測試 4: 按來源分組
        logger.info("\n[5/6] 測試按來源單位分組")
        logger.info("=" * 70)

        by_source = batch_formatter.format_by_source(items)

        source_dir = output_dir / 'by_source'
        source_dir.mkdir(parents=True, exist_ok=True)

        for source, md_content in by_source.items():
            source_file = source_dir / f"{source}.md"
            batch_formatter.save_to_file(md_content, str(source_file))
            logger.info(f"  {source}: {len(md_content):,} bytes")

        logger.info(f"✓ 按來源分組完成: {len(by_source)} 個檔案")

        # 測試 5: 按違規類型分組
        logger.info("\n[6/6] 測試按違規類型分組")
        logger.info("=" * 70)

        by_category = batch_formatter.format_by_category(items)

        category_dir = output_dir / 'by_category'
        category_dir.mkdir(parents=True, exist_ok=True)

        for category, md_content in by_category.items():
            category_file = category_dir / f"{category}.md"
            batch_formatter.save_to_file(md_content, str(category_file))

            # 顯示中文名稱
            category_name = formatter.category_names.get(category, category)
            logger.info(f"  {category_name} ({category}): {len(md_content):,} bytes")

        logger.info(f"✓ 按違規類型分組完成: {len(by_category)} 個檔案")

        # 統計資訊
        logger.info("\n" + "=" * 70)
        logger.info("統計資訊")
        logger.info("=" * 70)
        logger.info(f"總案件數: {len(items)}")
        logger.info(f"總 Markdown 大小: {len(batch_md):,} bytes ({len(batch_md)/1024:.1f} KB)")
        logger.info(f"平均每筆大小: {len(batch_md)//len(items):,} bytes")
        logger.info(f"按日期分檔: {len(by_date)} 個")
        logger.info(f"按來源分檔: {len(by_source)} 個")
        logger.info(f"按違規類型分檔: {len(by_category)} 個")

        # 分析 metadata 完整性
        logger.info("\n" + "=" * 70)
        logger.info("Metadata 完整性分析")
        logger.info("=" * 70)

        has_doc_number = sum(1 for item in items if item.get('metadata', {}).get('doc_number'))
        has_penalty_amount = sum(1 for item in items if item.get('metadata', {}).get('penalty_amount'))
        has_legal_basis = sum(1 for item in items if item.get('metadata', {}).get('legal_basis'))
        has_penalized_entity = sum(1 for item in items if item.get('metadata', {}).get('penalized_entity', {}).get('name'))
        has_category = sum(1 for item in items if item.get('metadata', {}).get('category'))

        logger.info(f"發文字號: {has_doc_number}/{len(items)} ({has_doc_number/len(items)*100:.1f}%)")
        logger.info(f"處分金額: {has_penalty_amount}/{len(items)} ({has_penalty_amount/len(items)*100:.1f}%)")
        logger.info(f"法條依據: {has_legal_basis}/{len(items)} ({has_legal_basis/len(items)*100:.1f}%)")
        logger.info(f"被處分人: {has_penalized_entity}/{len(items)} ({has_penalized_entity/len(items)*100:.1f}%)")
        logger.info(f"違規類型: {has_category}/{len(items)} ({has_category/len(items)*100:.1f}%)")

        logger.info("\n" + "=" * 70)
        logger.info("測試完成!")
        logger.info("=" * 70)

        logger.info("\n輸出檔案位置:")
        logger.info(f"  單筆範例: {single_file}")
        logger.info(f"  批次文檔: {batch_file}")
        logger.info(f"  按日期: {date_dir}/")
        logger.info(f"  按來源: {source_dir}/")
        logger.info(f"  按違規類型: {category_dir}/")

        logger.info("\n✓ 裁罰案件 Markdown 格式化器測試完成")

    except Exception as e:
        logger.error(f"測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
