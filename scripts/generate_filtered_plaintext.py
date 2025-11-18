"""
生成 2012+ 篩選資料的優化 Plain Text 檔案

此腳本將:
1. 讀取 data/penalties/filtered_2012.jsonl (490 筆)
2. 使用 PenaltyPlainTextOptimizer 生成優化的 plain text 檔案
3. 輸出到 data/plaintext_optimized/penalties_individual/
"""

import sys
import json
from pathlib import Path

# 加入專案根目錄到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processor.penalty_plaintext_optimizer import PenaltyPlainTextOptimizer
from loguru import logger


def main():
    """主函數"""
    logger.info("=" * 80)
    logger.info("生成 2012+ 篩選資料的優化 Plain Text 檔案")
    logger.info("=" * 80)

    # 讀取 filtered_2012.jsonl
    input_file = Path("data/penalties/filtered_2012.jsonl")
    logger.info(f"\n[1/2] 讀取資料: {input_file}")

    items = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            items.append(json.loads(line))

    logger.info(f"✓ 讀取成功: {len(items)} 筆")

    # 生成優化檔案
    output_dir = "data/plaintext_optimized/penalties_individual"
    logger.info(f"\n[2/2] 生成優化 Plain Text 檔案")
    logger.info(f"輸出目錄: {output_dir}")

    formatter = PenaltyPlainTextOptimizer()
    stats = formatter.format_batch(items, output_dir)

    # 詳細統計
    logger.info("\n" + "=" * 80)
    logger.info("統計資訊")
    logger.info("=" * 80)
    logger.info(f"\n總案件數: {stats['total_items']}")
    logger.info(f"成功建立: {stats['created_files']} 個檔案")
    logger.info(f"輸出目錄: {stats['output_dir']}")
    logger.info(f"總大小: {stats['total_size_kb']:.2f} KB ({stats['total_size_kb']/1024:.2f} MB)")
    logger.info(f"平均大小: {stats['avg_size_kb']:.2f} KB")

    logger.info("\n" + "=" * 80)
    logger.info("✓ 完成!")
    logger.info("=" * 80)
    logger.info("\n下一步: 檢查 .env 設定，然後上傳到 Gemini")
    logger.info("  指令: python scripts/upload_optimized_to_gemini.py")


if __name__ == '__main__':
    # 設定日誌
    logger.add(
        "logs/generate_filtered_plaintext.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG"
    )

    main()
