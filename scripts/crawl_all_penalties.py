"""完整爬取所有裁罰案件（約490筆）"""

import sys
from pathlib import Path

# 加入專案根目錄到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.utils.config_loader import ConfigLoader
from src.crawlers.penalties import PenaltyCrawler
from src.storage.jsonl_handler import JSONLHandler
from src.storage.index_manager import IndexManager
import time


def crawl_all_penalties(max_pages: int = 33):
    """
    完整爬取所有裁罰案件

    Args:
        max_pages: 最大頁數（預設33頁，每頁15筆 = ~495筆）
    """

    logger.info("=" * 80)
    logger.info("完整爬取裁罰案件")
    logger.info("=" * 80)

    # 1. 載入配置
    logger.info("\n[1/5] 載入配置")
    config_loader = ConfigLoader()
    config = config_loader.get_crawler_config()

    # 確保附件下載已啟用
    if not config.get('attachments', {}).get('download', False):
        logger.info("啟用附件下載")
        config.setdefault('attachments', {})['download'] = True

    logger.info(f"✓ 配置載入完成")

    # 2. 初始化爬蟲
    logger.info("\n[2/5] 初始化裁罰案件爬蟲")
    crawler = PenaltyCrawler(config)
    logger.info("✓ 爬蟲初始化成功")

    # 3. 完整爬取
    logger.info(f"\n[3/5] 開始爬取（預計 {max_pages} 頁）")
    logger.info("提示：完整爬取約需 20-30 分鐘")

    start_time = time.time()
    all_items = []

    for page in range(1, max_pages + 1):
        try:
            logger.info(f"\n處理第 {page}/{max_pages} 頁...")

            # 爬取列表頁
            items = crawler.crawl_page(page=page)

            if not items:
                logger.warning(f"第 {page} 頁無資料，停止爬取")
                break

            logger.info(f"  ✓ 列表頁: {len(items)} 筆")

            # 爬取每筆詳細頁
            detailed_count = 0
            for i, item in enumerate(items, 1):
                try:
                    # 爬取詳細頁
                    detail = crawler.fetch_detail(item['detail_url'], item)

                    if detail:
                        # 生成 ID（使用全局計數）
                        total_count = len(all_items) + 1
                        detail['id'] = f"fsc_pen_{detail['date'].replace('-', '')}_{total_count:04d}"
                        detail['data_type'] = 'penalty'

                        all_items.append(detail)
                        detailed_count += 1

                        # 每10筆顯示進度
                        if detailed_count % 10 == 0:
                            logger.info(f"  進度: {detailed_count}/{len(items)}")

                    # 避免請求過快
                    time.sleep(config.get('http', {}).get('request_interval', 1.0))

                except Exception as e:
                    logger.error(f"  處理第 {i} 筆失敗: {e}")
                    continue

            logger.info(f"  ✓ 詳細頁: {detailed_count}/{len(items)} 筆成功")
            logger.info(f"  累計: {len(all_items)} 筆")

            # 每5頁休息一下
            if page % 5 == 0:
                logger.info("  休息 3 秒...")
                time.sleep(3)

        except Exception as e:
            logger.error(f"處理第 {page} 頁失敗: {e}")
            continue

    elapsed = time.time() - start_time
    logger.info(f"\n✓ 爬取完成！")
    logger.info(f"  總筆數: {len(all_items)}")
    logger.info(f"  耗時: {elapsed/60:.1f} 分鐘")

    # 4. 儲存資料
    logger.info("\n[4/5] 儲存資料")

    storage = JSONLHandler()
    storage.write_items('penalties', all_items, mode='w')

    logger.info(f"✓ 資料已儲存: data/penalties/raw.jsonl")

    # 5. 建立索引
    logger.info("\n[5/5] 建立索引")

    index_mgr = IndexManager()
    index_mgr.build_index('penalties', all_items)

    logger.info(f"✓ 索引已建立")

    # 統計資訊
    logger.info("\n" + "=" * 80)
    logger.info("統計資訊")
    logger.info("=" * 80)

    # 統計來源單位
    sources = {}
    for item in all_items:
        src = item.get('metadata', {}).get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1

    logger.info("\n來源單位分布:")
    for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        percentage = count / len(all_items) * 100
        logger.info(f"  {src}: {count} 筆 ({percentage:.1f}%)")

    # 統計違規類型
    categories = {}
    for item in all_items:
        cat = item.get('metadata', {}).get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    logger.info("\n違規類型分布:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        percentage = count / len(all_items) * 100
        logger.info(f"  {cat}: {count} 筆 ({percentage:.1f}%)")

    # 統計附件
    total_attachments = sum(len(item.get('attachments', [])) for item in all_items)
    downloaded_attachments = sum(
        sum(1 for att in item.get('attachments', []) if att.get('downloaded'))
        for item in all_items
    )

    logger.info(f"\n附件統計:")
    logger.info(f"  總附件數: {total_attachments}")
    logger.info(f"  已下載: {downloaded_attachments}")
    if total_attachments > 0:
        download_rate = downloaded_attachments / total_attachments * 100
        logger.info(f"  下載率: {download_rate:.1f}%")

    # 日期範圍
    dates = [item.get('date') for item in all_items if item.get('date')]
    if dates:
        logger.info(f"\n日期範圍:")
        logger.info(f"  最早: {min(dates)}")
        logger.info(f"  最新: {max(dates)}")

    logger.info("\n" + "=" * 80)
    logger.info("✓ 完整爬取流程完成！")
    logger.info("=" * 80)
    logger.info("\n下一步:")
    logger.info("  1. 檢查 data/penalties/raw.jsonl")
    logger.info("  2. 檢查 data/penalties/index.json 和 metadata.json")
    logger.info("  3. 檢查附件下載 data/attachments/penalties/")
    logger.info("  4. 執行 Markdown 格式化: python scripts/test_penalty_markdown_formatter.py")

    return all_items


def main():
    """主函數"""
    import argparse

    # 解析命令列參數
    parser = argparse.ArgumentParser(description='完整爬取裁罰案件（約 490 筆）')
    parser.add_argument('--no-confirm', action='store_true',
                        help='跳過確認提示，直接開始爬取')
    parser.add_argument('--max-pages', type=int, default=33,
                        help='最大頁數（預設33頁）')
    args = parser.parse_args()

    try:
        # 詢問確認（除非使用 --no-confirm）
        if not args.no_confirm:
            print("=" * 80)
            print("準備完整爬取裁罰案件（約 490 筆）")
            print("=" * 80)
            print("\n預計耗時: 20-30 分鐘")
            print("注意事項:")
            print("  - 會下載所有附件（可能數 GB）")
            print("  - 請確保網路連線穩定")
            print("  - 建議使用背景執行或 tmux/screen")
            print("\n")

            response = input("確定要開始嗎？(yes/no): ").strip().lower()

            if response != 'yes':
                print("已取消")
                return
        else:
            logger.info("=" * 80)
            logger.info("開始完整爬取裁罰案件（跳過確認）")
            logger.info("=" * 80)

        # 開始爬取
        all_items = crawl_all_penalties(max_pages=args.max_pages)

        if all_items:
            logger.info(f"\n✅ 成功爬取 {len(all_items)} 筆裁罰案件")
        else:
            logger.error("\n❌ 爬取失敗")

    except KeyboardInterrupt:
        logger.warning("\n⚠️  使用者中斷")
        logger.info("提示：已爬取的資料會保存在 data/penalties/raw.jsonl")

    except Exception as e:
        logger.error(f"\n❌ 錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
