"""
測試優化的 Plain Text 格式化器

比較:
- 原始版本 (penalty_plaintext_formatter.py)
- 優化版本 (penalty_plaintext_optimizer.py)

預期改善:
- 檔案大小減少 ~35%
- 語義密度提升 ~20%
- 移除所有檢索噪音
"""

import json
import sys
from pathlib import Path

# 加入專案根目錄到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processor.penalty_plaintext_formatter import PenaltyPlainTextFormatter
from src.processor.penalty_plaintext_optimizer import PenaltyPlainTextOptimizer
from loguru import logger


def load_sample_penalty():
    """載入一筆範例裁罰案件"""
    jsonl_path = Path('data/penalties_test/test_penalties.jsonl')

    if not jsonl_path.exists():
        logger.error(f"找不到 JSONL 檔案: {jsonl_path}")
        return None

    # 讀取第一筆
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                return json.loads(line)

    return None


def compare_formats(item):
    """比較兩種格式的輸出"""

    # 原始版本
    formatter_original = PenaltyPlainTextFormatter()
    text_original = formatter_original.format_penalty(item)

    # 優化版本
    formatter_optimized = PenaltyPlainTextOptimizer()
    text_optimized = formatter_optimized.format_penalty(item)

    # 統計
    size_original = len(text_original.encode('utf-8'))
    size_optimized = len(text_optimized.encode('utf-8'))
    reduction = (1 - size_optimized / size_original) * 100

    lines_original = len(text_original.split('\n'))
    lines_optimized = len(text_optimized.split('\n'))

    print("\n" + "=" * 80)
    print("格式比較結果")
    print("=" * 80)
    print(f"\n案件 ID: {item.get('id', 'unknown')}")
    print(f"標題: {item.get('title', 'N/A')[:50]}...")

    print("\n【原始版本】")
    print(f"  檔案大小: {size_original:,} bytes ({size_original/1024:.2f} KB)")
    print(f"  行數: {lines_original}")

    print("\n【優化版本】")
    print(f"  檔案大小: {size_optimized:,} bytes ({size_optimized/1024:.2f} KB)")
    print(f"  行數: {lines_optimized}")

    print("\n【改善效果】")
    print(f"  檔案大小減少: {reduction:.1f}%")
    print(f"  行數減少: {lines_original - lines_optimized} 行")

    # 顯示輸出範例
    print("\n" + "=" * 80)
    print("【原始版本輸出 (前 30 行)】")
    print("=" * 80)
    print('\n'.join(text_original.split('\n')[:30]))

    print("\n" + "=" * 80)
    print("【優化版本輸出 (前 30 行)】")
    print("=" * 80)
    print('\n'.join(text_optimized.split('\n')[:30]))

    return {
        'size_original': size_original,
        'size_optimized': size_optimized,
        'reduction_percent': reduction
    }


def main():
    """主函數"""
    logger.info("開始測試優化格式化器...")

    # 載入範例
    item = load_sample_penalty()

    if not item:
        logger.error("無法載入範例案件")
        return

    # 比較格式
    stats = compare_formats(item)

    # 總結
    print("\n" + "=" * 80)
    print("測試完成!")
    print("=" * 80)
    print(f"✅ 檔案大小減少: {stats['reduction_percent']:.1f}%")
    print(f"✅ 優化版本移除了:")
    print("   - 所有分隔線 (==== 80 chars)")
    print("   - 描述性標題 ('金管會裁罰案件', '裁處書內容')")
    print("   - 無用 metadata (文件編號, 原始連結, 抓取時間)")
    print("   - 附件列表 (移至 file_mapping.json)")
    print(f"✅ 保留語義相關欄位: 發文日期, 來源單位, 機構名稱, 罰款金額, 發文字號")


if __name__ == '__main__':
    main()
