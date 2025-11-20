"""測試法令函釋爬蟲"""

import sys
from pathlib import Path

# 加入專案根目錄到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.utils.config_loader import ConfigLoader
from src.crawlers.law_interpretations import LawInterpretationsCrawler
from src.processor.law_interpretation_markdown_formatter import LawInterpretationMarkdownFormatter
import json


def test_law_interpretations_crawler():
    """測試法令函釋爬蟲"""

    logger.info("=" * 70)
    logger.info("測試法令函釋爬蟲")
    logger.info("=" * 70)

    # 1. 載入配置
    logger.info("\n[1/6] 載入配置")
    config_loader = ConfigLoader()
    config = config_loader.get_crawler_config()

    # 確保附件下載已啟用
    if not config.get('attachments', {}).get('download', False):
        logger.info("啟用附件下載")
        config.setdefault('attachments', {})['download'] = True

    logger.info(f"配置載入完成")

    # 2. 初始化爬蟲
    logger.info("\n[2/6] 初始化法令函釋爬蟲")
    crawler = LawInterpretationsCrawler(config)
    logger.info("✓ 爬蟲初始化成功")

    # 3. 爬取第一頁列表
    logger.info("\n[3/6] 爬取列表頁（第 1 頁）")
    items = crawler.crawl_page(page=1)

    if not items:
        logger.error("❌ 未找到任何法令函釋")
        return False

    logger.info(f"✓ 找到 {len(items)} 筆法令函釋")

    # 顯示前 5 筆
    logger.info("\n前 5 筆法令函釋:")
    for i, item in enumerate(items[:5], 1):
        logger.info(f"\n  [{i}]")
        logger.info(f"  日期: {item.get('date')}")
        logger.info(f"  來源: {item.get('source_raw')}")
        logger.info(f"  標題: {item.get('title')[:80]}...")

    # 4. 爬取詳細頁（測試前 10 筆）
    logger.info("\n[4/6] 爬取詳細頁（測試前 10 筆）")

    detailed_items = []

    for i, item in enumerate(items[:10], 1):
        logger.info(f"\n處理第 {i} 筆...")
        logger.info(f"  標題: {item.get('title')[:60]}...")

        # 爬取詳細頁
        detail = crawler.fetch_detail(item['detail_url'], item)

        if detail:
            # 生成 ID
            detail['id'] = f"fsc_law_{detail['date'].replace('-', '')}_{i:04d}"
            detail['data_type'] = 'law_interpretation'

            detailed_items.append(detail)

            # 顯示 metadata
            metadata = detail.get('metadata', {})

            logger.info(f"  ✓ 爬取成功")
            logger.info(f"  類型: {metadata.get('category', 'N/A')}")
            logger.info(f"  發文字號: {metadata.get('document_number', 'N/A')}")
            logger.info(f"  法律名稱: {metadata.get('law_name', 'N/A')}")
            logger.info(f"  修正/訂定條文: {metadata.get('amended_articles', 'N/A')}")

            attachments = detail.get('attachments', [])
            logger.info(f"  附件數: {len(attachments)}")
            for j, att in enumerate(attachments, 1):
                classification = att.get('classification', 'other')
                logger.info(f"    {j}. {att.get('name')[:40]}... ({att.get('type')}) - {classification}")
                if att.get('downloaded'):
                    logger.info(f"       ✓ 已下載: {att.get('size_bytes', 0) / 1024:.1f} KB")

        else:
            logger.error(f"  ✗ 爬取失敗")

    # 5. 生成 Markdown 測試（選擇幾個不同類型）
    logger.info("\n[5/6] 生成 Markdown 測試")

    # 建立測試資料目錄
    test_data_dir = Path('data/law_interpretations_test')
    test_data_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir = test_data_dir / 'markdown'
    markdown_dir.mkdir(parents=True, exist_ok=True)

    formatter = LawInterpretationMarkdownFormatter()

    # 統計各類型
    category_counts = {}
    for item in detailed_items:
        cat = item.get('metadata', {}).get('category', 'unknown')
        category_counts[cat] = category_counts.get(cat, 0) + 1

    logger.info(f"\n本批次類型分布:")
    for cat, count in category_counts.items():
        logger.info(f"  {cat}: {count} 筆")

    # 為每種類型生成一個 Markdown 範例
    markdown_samples = {}
    for item in detailed_items:
        cat = item.get('metadata', {}).get('category', 'unknown')
        if cat not in markdown_samples:
            markdown_samples[cat] = item
            # 生成 Markdown
            md_content = formatter.format_interpretation(item)
            md_file = markdown_dir / f"sample_{cat}_{item['id']}.md"
            formatter.save_to_file(md_content, str(md_file))
            logger.info(f"✓ 生成 Markdown 範例: {cat} -> {md_file.name}")

    # 6. 儲存測試結果
    logger.info("\n[6/6] 儲存測試結果")

    # 儲存為 JSONL
    output_file = test_data_dir / 'test_law_interpretations.jsonl'
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in detailed_items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    logger.info(f"✓ 測試結果已儲存: {output_file}")
    logger.info(f"  共 {len(detailed_items)} 筆法令函釋")

    # 7. 統計資訊
    logger.info("\n" + "=" * 70)
    logger.info("測試統計")
    logger.info("=" * 70)

    # 統計函釋類型
    categories = {}
    for item in detailed_items:
        cat = item.get('metadata', {}).get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    logger.info("\n函釋類型分布:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {cat}: {count} 筆")

    # 統計來源單位
    sources = {}
    for item in detailed_items:
        src = item.get('metadata', {}).get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1

    logger.info("\n來源單位分布:")
    for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {src}: {count} 筆")

    # 統計附件
    total_attachments = sum(len(item.get('attachments', [])) for item in detailed_items)
    downloaded_attachments = sum(
        sum(1 for att in item.get('attachments', []) if att.get('downloaded'))
        for item in detailed_items
    )

    # 統計附件分類
    attachment_classifications = {}
    for item in detailed_items:
        for att in item.get('attachments', []):
            classification = att.get('classification', 'other')
            attachment_classifications[classification] = attachment_classifications.get(classification, 0) + 1

    logger.info(f"\n附件統計:")
    logger.info(f"  總附件數: {total_attachments}")
    logger.info(f"  已下載: {downloaded_attachments}")
    logger.info(f"\n附件分類分布:")
    for classification, count in sorted(attachment_classifications.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {classification}: {count} 個")

    # 統計法律名稱 (Top 5)
    law_names = {}
    for item in detailed_items:
        law = item.get('metadata', {}).get('law_name')
        if law:
            law_names[law] = law_names.get(law, 0) + 1

    logger.info(f"\n相關法律 (Top 5):")
    for law, count in sorted(law_names.items(), key=lambda x: x[1], reverse=True)[:5]:
        logger.info(f"  {law}: {count} 筆")

    logger.info("\n✓ 法令函釋爬蟲測試完成")

    return True


def main():
    """主函數"""

    try:
        success = test_law_interpretations_crawler()

        if success:
            logger.info("\n" + "=" * 70)
            logger.info("測試結果: ✓ 成功")
            logger.info("=" * 70)
            logger.info("\n下一步:")
            logger.info("  1. 檢查 data/law_interpretations_test/test_law_interpretations.jsonl")
            logger.info("  2. 檢查 Markdown 範例 data/law_interpretations_test/markdown/")
            logger.info("  3. 檢查附件下載 data/attachments/law_interpretations/")
            logger.info("  4. 如果測試成功，可以進行完整爬取")
        else:
            logger.error("\n測試結果: ✗ 失敗")

    except Exception as e:
        logger.error(f"\n測試過程發生錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
