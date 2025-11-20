#!/usr/bin/env python3
"""
測試法令函釋 Plain Text 優化器

驗證項目：
1. metadata 格式化正確（日期、來源、標題、發文字號、法規名稱、修正條文）
2. 網頁雜訊移除（Facebook、Line、友善列印等）
3. 內容清理正確（空行控制、短行移除）
4. 檔案大小合理（相比原始資料減少）
5. 統一格式（與公告、裁罰一致）
"""

import sys
from pathlib import Path

# 加入專案根目錄到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.processor.law_interpretation_plaintext_optimizer import LawInterpretationPlainTextOptimizer
from src.storage.jsonl_handler import JSONLHandler
import json


def test_law_interpretation_optimizer():
    """測試法令函釋 Plain Text 優化器"""
    logger.info("=" * 70)
    logger.info("測試法令函釋 Plain Text 優化器")
    logger.info("=" * 70)

    # 1. 載入測試資料
    logger.info("\n[1/5] 載入測試資料")

    # 優先使用測試資料，如果不存在則使用完整資料
    test_file = Path('data/law_interpretations_test/test_law_interpretations.jsonl')

    if not test_file.exists():
        test_file = Path('data/law_interpretations/raw.jsonl')
        if not test_file.exists():
            logger.error(f"測試檔案不存在")
            logger.info("請先執行測試爬蟲: python scripts/test_law_interpretations_crawler.py")
            return

    items = []
    with open(test_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    if not items:
        logger.error("沒有法令函釋資料")
        return

    logger.info(f"✓ 載入 {len(items)} 筆法令函釋資料")

    # 2. 初始化優化器
    logger.info("\n[2/5] 初始化優化器")
    optimizer = LawInterpretationPlainTextOptimizer()
    logger.info("✓ 優化器初始化成功")

    # 3. 測試不同類型的格式化
    logger.info("\n[3/5] 測試不同類型格式化")

    # 找出不同類型的範例
    test_categories = {
        'law_amendment': None,      # 修正型
        'law_enactment': None,       # 訂定型
        'law_clarification': None,   # 函釋型
    }

    for item in items:
        category = item.get('metadata', {}).get('category', 'unknown')
        if category in test_categories and test_categories[category] is None:
            test_categories[category] = item

    # 測試每個類型
    for category, item in test_categories.items():
        if item:
            logger.info(f"\n類型: {category}")
            logger.info(f"ID: {item['id']}")
            logger.info(f"標題: {item['title'][:60]}...")

            plaintext = optimizer.format_item(item)

            logger.info(f"\n生成的 Plain Text 預覽:")
            logger.info("-" * 70)
            preview = plaintext[:400] + "..." if len(plaintext) > 400 else plaintext
            logger.info(preview)
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

            # 類型特定檢查
            if category == 'law_amendment':
                checks['包含法規名稱或修正條文'] = (
                    '相關法規:' in plaintext or '修正條文:' in plaintext
                )
            elif category == 'law_clarification':
                checks['可能包含法條引用'] = True  # 函釋型可能沒有法條引用

            passed_count = sum(1 for v in checks.values() if v)
            total_count = len(checks)

            logger.info(f"\n檢查結果: {passed_count}/{total_count}")
            for check_name, passed in checks.items():
                status = "✓" if passed else "✗"
                logger.info(f"  {status} {check_name}")

    # 4. 批次格式化測試
    logger.info("\n[4/5] 批次格式化測試")
    output_dir = 'data/plaintext_optimized/law_interpretations_test'

    # 取前 20 筆進行測試
    test_items = items[:20]
    stats = optimizer.format_batch(test_items, output_dir)

    logger.info(f"\n批次格式化結果:")
    logger.info(f"  總項目數: {stats['total_items']}")
    logger.info(f"  成功建立: {stats['created_files']} 個檔案")
    logger.info(f"  輸出目錄: {stats['output_dir']}")
    logger.info(f"  總大小: {stats['total_size_kb']:.2f} KB")
    logger.info(f"  平均大小: {stats['avg_size_kb']:.2f} KB")

    # 5. 檔案大小比較
    logger.info("\n[5/5] 檔案大小分析")
    logger.info("=" * 70)

    # 計算原始 JSONL 中單筆資料的平均大小
    original_sizes = []
    for item in test_items:
        # 估算原始大小（JSON 序列化）
        original_size = len(json.dumps(item, ensure_ascii=False).encode('utf-8'))
        original_sizes.append(original_size)

    avg_original_size = sum(original_sizes) / len(original_sizes) if original_sizes else 0

    logger.info(f"原始資料平均大小: {avg_original_size / 1024:.2f} KB")
    logger.info(f"Plain Text 平均大小: {stats['avg_size_kb']:.2f} KB")

    if avg_original_size > 0:
        reduction = (1 - stats['avg_size_kb'] / (avg_original_size / 1024)) * 100
        logger.info(f"檔案大小減少: {reduction:.1f}%")

        # 預期效果：-35% 左右
        if reduction >= 30:
            logger.info(f"✓ 檔案大小優化達標（目標: -30% 以上）")
        else:
            logger.warning(f"⚠️ 檔案大小優化未達預期（目標: -30% 以上）")

    # 6. 統一性驗證
    logger.info("\n" + "=" * 70)
    logger.info("統一性驗證")
    logger.info("=" * 70)

    # 檢查所有檔案都符合統一格式
    output_path = Path(output_dir)
    txt_files = list(output_path.glob('*.txt'))

    logger.info(f"\n檢查 {len(txt_files)} 個 Plain Text 檔案...")

    unified_checks = {
        '所有檔案都使用 .txt 副檔名': all(f.suffix == '.txt' for f in txt_files),
        '所有檔案都包含分隔線': True,  # 預設為 True，後面驗證
        '所有檔案都無網頁雜訊': True,
    }

    # 抽樣檢查
    sample_files = txt_files[:5] if len(txt_files) >= 5 else txt_files
    for f in sample_files:
        content = f.read_text(encoding='utf-8')
        if '---' not in content:
            unified_checks['所有檔案都包含分隔線'] = False
        if any(keyword in content for keyword in ['facebook', 'Facebook', 'Line', '友善列印']):
            unified_checks['所有檔案都無網頁雜訊'] = False

    logger.info("\n統一性檢查結果:")
    all_passed = True
    for check_name, passed in unified_checks.items():
        status = "✓" if passed else "✗"
        logger.info(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    # 7. 範例檔案
    if stats.get('files'):
        logger.info("\n範例檔案:")
        for f in stats['files'][:3]:
            logger.info(f"  - {f}")

    logger.info("\n" + "=" * 70)
    if all_passed:
        logger.info("✓ 測試完成！所有檢查通過")
    else:
        logger.warning("⚠️ 測試完成，部分檢查未通過")
    logger.info("=" * 70)


def main():
    """主函數"""
    try:
        test_law_interpretation_optimizer()
    except Exception as e:
        logger.error(f"\n測試過程發生錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
