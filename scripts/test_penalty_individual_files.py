"""測試裁罰案件獨立檔案格式化"""

import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processor.penalty_markdown_formatter import BatchPenaltyMarkdownFormatter
from loguru import logger
import json

# 設定日誌
logger.remove()
logger.add(sys.stderr, level="INFO")


def main():
    """主程式"""
    logger.info("=" * 70)
    logger.info("測試裁罰案件獨立檔案格式化")
    logger.info("=" * 70)

    try:
        # 讀取測試資料
        logger.info("\n[1/3] 讀取測試資料")

        test_file = Path('data/penalties_test/test_penalties.jsonl')

        if not test_file.exists():
            logger.error(f"測試資料檔案不存在: {test_file}")
            logger.info("請先執行 python scripts/test_penalty_crawler.py")
            return

        # 讀取 JSONL
        items = []
        with open(test_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    items.append(json.loads(line))

        logger.info(f"✓ 讀取完成: {len(items)} 筆裁罰案件")

        if not items:
            logger.warning("沒有資料可供格式化")
            return

        # 初始化批次格式化器
        logger.info("\n[2/3] 格式化為獨立檔案")
        logger.info("=" * 70)

        formatter = BatchPenaltyMarkdownFormatter()

        # 格式化為獨立檔案
        output_dir = 'data/markdown/penalties_individual'
        result = formatter.format_individual_files(items, output_dir)

        logger.info(f"\n✓ 格式化完成")
        logger.info(f"  總案件數: {result['total_items']}")
        logger.info(f"  成功建立: {result['created_files']} 個檔案")
        logger.info(f"  輸出目錄: {result['output_dir']}")

        # 列出建立的檔案
        logger.info("\n[3/3] 檢視建立的檔案")
        logger.info("=" * 70)

        output_path = Path(result['output_dir'])
        all_files = sorted(output_path.glob('*.md'))

        logger.info(f"\n共 {len(all_files)} 個 Markdown 檔案:\n")
        for i, filepath in enumerate(all_files, 1):
            file_size = filepath.stat().st_size
            logger.info(f"  [{i}] {filepath.name}")
            logger.info(f"      大小: {file_size:,} bytes ({file_size/1024:.1f} KB)")

        # 讀取並預覽第一個檔案
        if all_files:
            logger.info("\n" + "=" * 70)
            logger.info(f"第一個檔案預覽 ({all_files[0].name}):")
            logger.info("=" * 70)

            with open(all_files[0], 'r', encoding='utf-8') as f:
                content = f.read()
                preview = content[:600]
                logger.info(f"\n前 600 字元:\n")
                print(preview)
                logger.info(f"\n... (完整內容共 {len(content)} 字元)")

        logger.info("\n" + "=" * 70)
        logger.info("測試完成!")
        logger.info("=" * 70)

        logger.info("\n✓ 裁罰案件獨立檔案格式化測試完成")
        logger.info(f"\n所有檔案已儲存至: {output_dir}/")

    except Exception as e:
        logger.error(f"測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
