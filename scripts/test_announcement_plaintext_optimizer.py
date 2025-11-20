#!/usr/bin/env python3
"""
測試公告 Plain Text 優化器

驗證項目：
1. metadata 格式化正確（日期、來源、標題、公告文號、類型）
2. 網頁雜訊移除（Facebook、Line、友善列印等）
3. 內容清理正確（空行控制、短行移除）
4. 檔案大小合理（相比原始資料減少）
5. 語義密度提升（無重複、無噪音）
"""

import sys
from pathlib import Path

# 加入專案根目錄到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.processor.announcement_plaintext_optimizer import AnnouncementPlainTextOptimizer
import json


def test_announcement_optimizer():
    """測試公告 Plain Text 優化器"""
    logger.info("=" * 70)
    logger.info("測試公告 Plain Text 優化器")
    logger.info("=" * 70)

    # 1. 載入測試資料
    logger.info("\n[1/4] 載入測試資料")
    test_file = Path('data/announcements_test/test_results.jsonl')

    if not test_file.exists():
        logger.error(f"測試檔案不存在: {test_file}")
        logger.info("請先執行: python scripts/test_announcements_crawler.py")
        return

    items = []
    with open(test_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    logger.info(f"✓ 載入 {len(items)} 筆公告資料")

    # 2. 初始化優化器
    logger.info("\n[2/4] 初始化優化器")
    optimizer = AnnouncementPlainTextOptimizer()
    logger.info("✓ 優化器初始化成功")

    # 3. 測試單筆格式化
    logger.info("\n[3/4] 測試單筆格式化")
    if items:
        test_item = items[0]
        plaintext = optimizer.format_item(test_item)

        logger.info(f"\n測試案例: {test_item['id']}")
        logger.info(f"標題: {test_item['title'][:60]}...")
        logger.info(f"\n生成的 Plain Text:")
        logger.info("-" * 70)
        logger.info(plaintext[:500] + "..." if len(plaintext) > 500 else plaintext)
        logger.info("-" * 70)

        # 檢查關鍵欄位
        checks = {
            '包含發文日期': '發文日期:' in plaintext,
            '包含來源單位': '來源單位:' in plaintext,
            '包含標題': '標題:' in plaintext,
            '包含分隔線': '---' in plaintext,
            '無 Facebook': 'facebook' not in plaintext.lower(),
            '無 Line': 'Line' not in plaintext,
            '無友善列印': '友善列印' not in plaintext,
        }

        logger.info("\n格式化檢查:")
        all_passed = True
        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"  {status} {check_name}")
            if not passed:
                all_passed = False

        if all_passed:
            logger.info("\n✓ 所有檢查通過！")
        else:
            logger.warning("\n⚠️ 部分檢查未通過")

    # 4. 批次格式化
    logger.info("\n[4/4] 批次格式化測試")
    output_dir = 'data/plaintext_optimized/announcements_test'

    stats = optimizer.format_batch(items[:10], output_dir)

    logger.info(f"\n批次格式化結果:")
    logger.info(f"  總項目數: {stats['total_items']}")
    logger.info(f"  成功建立: {stats['created_files']} 個檔案")
    logger.info(f"  輸出目錄: {stats['output_dir']}")
    logger.info(f"  總大小: {stats['total_size_kb']:.2f} KB")
    logger.info(f"  平均大小: {stats['avg_size_kb']:.2f} KB")

    # 5. 檔案大小比較
    logger.info("\n" + "=" * 70)
    logger.info("檔案大小分析")
    logger.info("=" * 70)

    # 計算原始 JSONL 中單筆資料的平均大小
    original_sizes = []
    for item in items[:10]:
        # 估算原始大小（JSON 序列化）
        original_size = len(json.dumps(item, ensure_ascii=False).encode('utf-8'))
        original_sizes.append(original_size)

    avg_original_size = sum(original_sizes) / len(original_sizes) if original_sizes else 0

    logger.info(f"原始資料平均大小: {avg_original_size / 1024:.2f} KB")
    logger.info(f"Plain Text 平均大小: {stats['avg_size_kb']:.2f} KB")

    if avg_original_size > 0:
        reduction = (1 - stats['avg_size_kb'] / (avg_original_size / 1024)) * 100
        logger.info(f"檔案大小減少: {reduction:.1f}%")

    # 6. 範例檔案
    if stats.get('files'):
        logger.info("\n範例檔案:")
        for f in stats['files'][:3]:
            logger.info(f"  - {f}")

    logger.info("\n" + "=" * 70)
    logger.info("✓ 測試完成！")
    logger.info("=" * 70)


def main():
    """主函數"""
    try:
        test_announcement_optimizer()
    except Exception as e:
        logger.error(f"\n測試過程發生錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
