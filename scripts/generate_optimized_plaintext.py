"""
批次生成優化的 Plain Text 檔案和擴充的 file_mapping.json

此腳本將:
1. 從 raw.jsonl 讀取所有裁罰案件
2. 使用 PenaltyPlainTextOptimizer 生成優化的 plain text 檔案
3. 使用更新後的 generate_file_mapping 生成擴充的 file_mapping.json
4. 輸出詳細的統計資訊

優化效果:
- 檔案大小減少 ~15-35%
- 移除所有檢索噪音
- 分離檢索層(乾淨檔案)和顯示層(file_mapping.json)
"""

import sys
import json
from pathlib import Path

# 加入專案根目錄到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processor.penalty_plaintext_optimizer import PenaltyPlainTextOptimizer
from src.storage.jsonl_handler import JSONLHandler
from loguru import logger


def generate_optimized_plaintext_batch(
    source: str = 'penalties',
    output_dir: str = 'data/plaintext_optimized/penalties_individual'
):
    """
    批次生成優化的 Plain Text 檔案

    Args:
        source: 資料源名稱 (預設: penalties)
        output_dir: 輸出目錄

    Returns:
        統計資訊字典
    """
    logger.info("=" * 80)
    logger.info("批次生成優化 Plain Text 檔案")
    logger.info("=" * 80)

    # 讀取資料
    logger.info(f"\n[1/2] 讀取資料: data/{source}/raw.jsonl")
    storage = JSONLHandler()
    items = storage.read_all(source)
    logger.info(f"✓ 讀取成功: {len(items)} 筆")

    # 生成優化檔案
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

    return stats


def generate_file_mapping_wrapper(source: str = 'penalties', use_llm: bool = False):
    """
    呼叫 generate_file_mapping 生成擴充的檔案映射

    Args:
        source: 資料源名稱
        use_llm: 是否使用 LLM 提取法條

    Returns:
        映射字典
    """
    # 導入 generate_file_mapping 模組
    from scripts.generate_file_mapping import generate_file_mapping

    logger.info("\n" + "=" * 80)
    logger.info("生成擴充的 file_mapping.json")
    logger.info("=" * 80)

    mapping = generate_file_mapping(source, use_llm=use_llm)

    return mapping


def compare_with_baseline(
    baseline_dir: str = 'data/plaintext/penalties_individual',
    optimized_dir: str = 'data/plaintext_optimized/penalties_individual'
):
    """
    比較優化版本與基礎版本的檔案大小

    Args:
        baseline_dir: 基礎版本目錄
        optimized_dir: 優化版本目錄

    Returns:
        比較統計資訊
    """
    baseline_path = Path(baseline_dir)
    optimized_path = Path(optimized_dir)

    if not baseline_path.exists() or not optimized_path.exists():
        logger.warning("無法進行比較 (目錄不存在)")
        return None

    # 計算基礎版本總大小
    baseline_files = list(baseline_path.glob('*.txt'))
    baseline_total = sum(f.stat().st_size for f in baseline_files)
    baseline_avg = baseline_total / len(baseline_files) if baseline_files else 0

    # 計算優化版本總大小
    optimized_files = list(optimized_path.glob('*.txt'))
    optimized_total = sum(f.stat().st_size for f in optimized_files)
    optimized_avg = optimized_total / len(optimized_files) if optimized_files else 0

    # 計算減少百分比
    reduction = (1 - optimized_total / baseline_total) * 100 if baseline_total > 0 else 0

    logger.info("\n" + "=" * 80)
    logger.info("與基礎版本比較")
    logger.info("=" * 80)
    logger.info(f"\n【基礎版本】 {baseline_dir}")
    logger.info(f"  檔案數量: {len(baseline_files)}")
    logger.info(f"  總大小: {baseline_total/1024:.2f} KB ({baseline_total/1024/1024:.2f} MB)")
    logger.info(f"  平均大小: {baseline_avg/1024:.2f} KB")

    logger.info(f"\n【優化版本】 {optimized_dir}")
    logger.info(f"  檔案數量: {len(optimized_files)}")
    logger.info(f"  總大小: {optimized_total/1024:.2f} KB ({optimized_total/1024/1024:.2f} MB)")
    logger.info(f"  平均大小: {optimized_avg/1024:.2f} KB")

    logger.info(f"\n【改善效果】")
    logger.info(f"  檔案大小減少: {reduction:.1f}%")
    logger.info(f"  節省空間: {(baseline_total - optimized_total)/1024:.2f} KB")

    return {
        'baseline_files': len(baseline_files),
        'optimized_files': len(optimized_files),
        'baseline_total_kb': baseline_total / 1024,
        'optimized_total_kb': optimized_total / 1024,
        'reduction_percent': reduction
    }


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='批次生成優化 Plain Text 檔案和 file_mapping.json')
    parser.add_argument('--source', default='penalties', help='資料源名稱 (預設: penalties)')
    parser.add_argument('--output', default='data/plaintext_optimized/penalties_individual', help='輸出目錄')
    parser.add_argument('--use-llm', action='store_true', help='使用 LLM 提取法條 (需要 GEMINI_API_KEY)')
    parser.add_argument('--compare', action='store_true', help='與基礎版本比較')
    parser.add_argument('--skip-plaintext', action='store_true', help='跳過 plain text 生成 (只生成 file_mapping)')
    parser.add_argument('--skip-mapping', action='store_true', help='跳過 file_mapping 生成 (只生成 plain text)')

    args = parser.parse_args()

    try:
        # Step 1: 生成優化 Plain Text 檔案
        if not args.skip_plaintext:
            plaintext_stats = generate_optimized_plaintext_batch(
                source=args.source,
                output_dir=args.output
            )

        # Step 2: 生成擴充的 file_mapping.json
        if not args.skip_mapping:
            mapping_stats = generate_file_mapping_wrapper(
                source=args.source,
                use_llm=args.use_llm
            )

        # Step 3: 比較 (可選)
        if args.compare:
            compare_stats = compare_with_baseline(
                baseline_dir='data/plaintext/penalties_individual',
                optimized_dir=args.output
            )

        # 總結
        logger.info("\n" + "=" * 80)
        logger.info("✅ 批次生成完成!")
        logger.info("=" * 80)

        if not args.skip_plaintext:
            logger.info(f"\n優化 Plain Text 檔案:")
            logger.info(f"  位置: {args.output}")
            logger.info(f"  檔案數: {plaintext_stats['created_files']}")
            logger.info(f"  平均大小: {plaintext_stats['avg_size_kb']:.2f} KB")

        if not args.skip_mapping:
            logger.info(f"\n擴充 file_mapping.json:")
            logger.info(f"  位置: data/{args.source}/file_mapping.json")
            logger.info(f"  包含完整 metadata (顯示用)")

        logger.info("\n下一步: 上傳到 Gemini File Search Store")
        logger.info("  指令: python scripts/upload_optimized_to_gemini.py")

    except Exception as e:
        logger.error(f"\n❌ 錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    # 設定日誌
    logger.add(
        "logs/generate_optimized_plaintext.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG"
    )

    main()
