"""完整爬取法令函釋資料"""

import sys
from pathlib import Path

# 加入專案根目錄到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.utils.config_loader import ConfigLoader
from src.crawlers.law_interpretations import LawInterpretationsCrawler
from src.storage.jsonl_handler import JSONLHandler
from src.storage.index_manager import IndexManager
import json


def crawl_law_interpretations_full(
    max_pages: int = None,
    start_page: int = 1,
    enable_attachments: bool = True
):
    """
    完整爬取法令函釋

    Args:
        max_pages: 最大爬取頁數（None = 全部）
        start_page: 起始頁碼
        enable_attachments: 是否下載附件
    """
    logger.info("=" * 70)
    logger.info("完整爬取法令函釋")
    logger.info("=" * 70)

    # 1. 載入配置
    logger.info("\n[1/4] 載入配置")
    config_loader = ConfigLoader()
    config = config_loader.get_crawler_config()

    # 啟用附件下載
    if enable_attachments:
        config.setdefault('attachments', {})['download'] = True
        logger.info("✓ 附件下載已啟用")
    else:
        config.setdefault('attachments', {})['download'] = False
        logger.info("✓ 附件下載已停用")

    # 2. 初始化爬蟲
    logger.info("\n[2/4] 初始化法令函釋爬蟲")
    crawler = LawInterpretationsCrawler(config)
    logger.info("✓ 爬蟲初始化成功")

    # 3. 開始爬取
    logger.info("\n[3/4] 開始爬取")
    logger.info(f"起始頁碼: {start_page}")
    logger.info(f"最大頁數: {max_pages if max_pages else '全部'}")
    logger.info("-" * 70)

    all_items = []
    current_page = start_page
    consecutive_empty = 0
    max_consecutive_empty = 3  # 連續 3 頁空白就停止

    while True:
        # 檢查是否達到最大頁數
        if max_pages and current_page >= start_page + max_pages:
            logger.info(f"\n已達到最大頁數限制: {max_pages}")
            break

        logger.info(f"\n爬取第 {current_page} 頁...")

        try:
            # 爬取單頁
            items = crawler.crawl_page(current_page)

            if not items:
                consecutive_empty += 1
                logger.warning(f"第 {current_page} 頁無資料（連續 {consecutive_empty}/{max_consecutive_empty}）")

                if consecutive_empty >= max_consecutive_empty:
                    logger.info(f"連續 {max_consecutive_empty} 頁無資料，停止爬取")
                    break
            else:
                consecutive_empty = 0
                logger.info(f"✓ 第 {current_page} 頁: {len(items)} 筆")
                all_items.extend(items)

            current_page += 1

        except Exception as e:
            logger.error(f"爬取第 {current_page} 頁失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
            break

    logger.info(f"\n爬取完成！")
    logger.info(f"總頁數: {current_page - start_page}")
    logger.info(f"總筆數: {len(all_items)}")

    # 4. 儲存資料
    logger.info("\n[4/4] 儲存資料")

    if not all_items:
        logger.warning("沒有資料需要儲存")
        return

    # 建立輸出目錄
    output_dir = Path('data/law_interpretations')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 儲存為 JSONL
    output_file = output_dir / 'raw.jsonl'
    handler = JSONLHandler()

    # 檢查是否已有資料
    existing_ids = set()
    if output_file.exists():
        logger.info(f"檢測到現有資料檔案: {output_file}")
        existing_items = handler.read_all('law_interpretations')
        existing_ids = {item.get('id') for item in existing_items}
        logger.info(f"現有資料: {len(existing_ids)} 筆")

    # 過濾重複
    new_items = [item for item in all_items if item.get('id') not in existing_ids]

    if not new_items:
        logger.warning("所有資料都已存在，無新資料")
        return

    logger.info(f"新增資料: {len(new_items)} 筆")

    # 寫入（追加模式）
    with open(output_file, 'a', encoding='utf-8') as f:
        for item in new_items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    logger.info(f"✓ 資料已儲存: {output_file}")

    # 5. 建立索引
    logger.info("\n[5/5] 建立索引")
    index_mgr = IndexManager()

    # 讀取所有資料（包含新舊）
    all_data = handler.read_all('law_interpretations')
    index_mgr.build_index('law_interpretations', all_data)

    logger.info("✓ 索引已建立")

    # 6. 統計資訊
    logger.info("\n" + "=" * 70)
    logger.info("爬取統計")
    logger.info("=" * 70)

    # 統計類型
    categories = {}
    for item in new_items:
        cat = item.get('metadata', {}).get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    logger.info("\n類型分布:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {cat}: {count} 筆")

    # 統計來源
    sources = {}
    for item in new_items:
        src = item.get('metadata', {}).get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1

    logger.info("\n來源分布:")
    for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {src}: {count} 筆")

    # 統計附件
    total_attachments = sum(len(item.get('attachments', [])) for item in new_items)
    downloaded_attachments = sum(
        sum(1 for att in item.get('attachments', []) if att.get('downloaded'))
        for item in new_items
    )

    logger.info(f"\n附件統計:")
    logger.info(f"  總附件數: {total_attachments}")
    logger.info(f"  已下載: {downloaded_attachments}")
    if total_attachments > 0:
        download_rate = downloaded_attachments / total_attachments * 100
        logger.info(f"  下載率: {download_rate:.1f}%")

    # 統計優先級
    priority_mapping = {
        'amendment': 0,
        'enactment': 0,
        'clarification': 0,
        'approval': 1,
        'announcement': 1,
        'repeal': 2,
        'adjustment': 2,
        'notice': 2,
        'other': 3,
        'unknown': 3,
    }

    priority_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for item in new_items:
        cat = item.get('metadata', {}).get('category', 'unknown')
        priority = priority_mapping.get(cat, 3)
        priority_counts[priority] += 1

    logger.info(f"\n優先級分布:")
    logger.info(f"  P0 (核心): {priority_counts[0]} 筆")
    logger.info(f"  P1 (補充): {priority_counts[1]} 筆")
    logger.info(f"  P2 (歷史): {priority_counts[2]} 筆")
    logger.info(f"  P3 (其他): {priority_counts[3]} 筆")

    logger.info("\n✓ 法令函釋爬取完成")


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='完整爬取法令函釋')
    parser.add_argument('--max-pages', type=int, default=None,
                        help='最大爬取頁數（預設：全部）')
    parser.add_argument('--start-page', type=int, default=1,
                        help='起始頁碼（預設：1）')
    parser.add_argument('--no-attachments', action='store_true',
                        help='停用附件下載')

    args = parser.parse_args()

    try:
        crawl_law_interpretations_full(
            max_pages=args.max_pages,
            start_page=args.start_page,
            enable_attachments=not args.no_attachments
        )

        logger.info("\n" + "=" * 70)
        logger.info("完成！")
        logger.info("=" * 70)
        logger.info("\n下一步:")
        logger.info("  1. 檢查 data/law_interpretations/raw.jsonl")
        logger.info("  2. 檢查附件 data/attachments/law_interpretations/")
        logger.info("  3. 測試上傳策略")
        logger.info("  4. 開始上傳到 Gemini")

    except Exception as e:
        logger.error(f"\n爬取過程發生錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
