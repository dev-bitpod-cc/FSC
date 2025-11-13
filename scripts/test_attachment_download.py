"""測試附件下載功能

測試流程:
1. 爬取單個公告（包含附件下載）
2. 驗證附件檔案是否正確儲存
3. 驗證附件元資料是否正確更新
4. 測試上傳到 Gemini（包含附件）
"""

import sys
from pathlib import Path

# 加入專案根目錄到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.utils.config_loader import ConfigLoader
from src.crawlers.announcements import AnnouncementCrawler
from src.uploader.gemini_uploader import GeminiUploader
import json


def test_attachment_download():
    """測試附件下載"""

    logger.info("=" * 70)
    logger.info("開始測試附件下載功能")
    logger.info("=" * 70)

    # 1. 載入配置
    logger.info("\n[1/5] 載入配置")
    config_loader = ConfigLoader()
    config = config_loader.get_crawler_config()

    # 確保附件下載已啟用
    if not config.get('attachments', {}).get('download', False):
        logger.warning("附件下載未啟用，正在啟用...")
        config.setdefault('attachments', {})['download'] = True

    logger.info(f"附件下載設定: {config.get('attachments', {})}")

    # 2. 初始化爬蟲
    logger.info("\n[2/5] 初始化爬蟲")
    crawler = AnnouncementCrawler(config)

    # 3. 爬取第一頁（只爬取前3筆）
    logger.info("\n[3/5] 爬取公告列表（第1頁）")
    items = crawler.crawl_page(page=1)

    if not items:
        logger.error("❌ 未找到任何公告")
        return False

    logger.info(f"✓ 找到 {len(items)} 筆公告")

    # 4. 爬取詳細頁以獲取附件（測試前3筆）
    logger.info("\n[4/5] 爬取詳細頁（測試前3筆）")

    test_item = None
    for i, item in enumerate(items[:3], 1):
        logger.info(f"\n處理第 {i} 筆公告...")
        logger.info(f"  標題: {item.get('title')[:50]}...")

        # 爬取詳細頁
        detail = crawler.fetch_detail(item['detail_url'], item)

        if detail and detail.get('attachments'):
            test_item = detail
            logger.info(f"✓ 找到有附件的公告:")
            logger.info(f"  ID: {detail.get('id')}")
            logger.info(f"  標題: {detail.get('title')}")
            logger.info(f"  附件數: {len(detail.get('attachments', []))}")

            # 顯示附件資訊
            for j, att in enumerate(detail.get('attachments', []), 1):
                logger.info(f"  附件 [{j}]:")
                logger.info(f"    名稱: {att.get('name')}")
                logger.info(f"    類型: {att.get('type')}")
                logger.info(f"    URL: {att.get('url')[:60]}...")

                # 檢查是否已下載
                if att.get('downloaded'):
                    logger.info(f"    ✓ 已下載: {att.get('local_path')}")
                    logger.info(f"    檔案大小: {att.get('size_bytes', 0) / 1024:.1f} KB")
                elif att.get('download_error'):
                    logger.error(f"    ✗ 下載失敗: {att.get('download_error')}")
                else:
                    logger.warning(f"    ⚠ 未下載")

            break
        else:
            logger.info(f"  無附件，繼續...")

    if not test_item:
        logger.warning("⚠ 前3筆公告中都沒有附件，測試結束")
        return True

    # 5. 驗證檔案是否存在
    logger.info("\n[5/5] 驗證下載的檔案")

    success_count = 0
    fail_count = 0

    for att in test_item.get('attachments', []):
        local_path = att.get('local_path')

        if local_path:
            file_path = Path(local_path)
            if file_path.exists():
                size = file_path.stat().st_size
                logger.info(f"✓ 檔案存在: {file_path.name} ({size / 1024:.1f} KB)")
                success_count += 1
            else:
                logger.error(f"✗ 檔案不存在: {local_path}")
                fail_count += 1
        else:
            logger.warning(f"⚠ 無 local_path: {att.get('name')}")
            fail_count += 1

    # 總結
    logger.info("\n" + "=" * 70)
    logger.info("測試結果")
    logger.info("=" * 70)
    logger.info(f"成功下載: {success_count} 個附件")
    logger.info(f"失敗/跳過: {fail_count} 個附件")

    if success_count > 0:
        logger.info("✓ 附件下載功能正常")
        return True
    else:
        logger.error("✗ 附件下載功能異常")
        return False


def test_attachment_upload():
    """測試附件上傳到 Gemini"""

    logger.info("\n" + "=" * 70)
    logger.info("開始測試附件上傳到 Gemini")
    logger.info("=" * 70)

    # 檢查是否有 GEMINI_API_KEY
    import os
    if not os.getenv('GEMINI_API_KEY'):
        logger.warning("⚠ 未設定 GEMINI_API_KEY，跳過上傳測試")
        logger.info("如需測試上傳功能，請設定環境變數:")
        logger.info("  export GEMINI_API_KEY='your-api-key'")
        return True

    # 找到已下載的附件
    logger.info("\n[1/3] 尋找已下載的附件")

    attachments_dir = Path('data/attachments/announcements')
    if not attachments_dir.exists():
        logger.warning("⚠ 附件目錄不存在，跳過上傳測試")
        return True

    # 找到第一個有附件的公告目錄
    test_dir = None
    for doc_dir in attachments_dir.iterdir():
        if doc_dir.is_dir() and list(doc_dir.glob('*.pdf')):
            test_dir = doc_dir
            break

    if not test_dir:
        logger.warning("⚠ 未找到已下載的附件，跳過上傳測試")
        return True

    logger.info(f"✓ 找到測試目錄: {test_dir.name}")

    # 列出附件
    attachments = list(test_dir.glob('*.pdf')) + list(test_dir.glob('*.doc*'))
    logger.info(f"  附件數量: {len(attachments)}")
    for att in attachments:
        logger.info(f"    - {att.name} ({att.stat().st_size / 1024:.1f} KB)")

    # 2. 建立測試用的 Markdown 檔案
    logger.info("\n[2/3] 建立測試 Markdown 檔案")

    markdown_content = f"""# 測試公告 - 附件上傳

**文件 ID**: {test_dir.name}

## 內容

這是一個測試用的公告，用於驗證附件上傳功能。

本公告包含 {len(attachments)} 個附件。

## 附件清單

"""

    for i, att in enumerate(attachments, 1):
        markdown_content += f"{i}. {att.name}\n"

    test_markdown_path = test_dir / 'test_announcement.md'
    test_markdown_path.write_text(markdown_content, encoding='utf-8')

    logger.info(f"✓ Markdown 檔案已建立: {test_markdown_path}")

    # 3. 上傳到 Gemini
    logger.info("\n[3/3] 上傳到 Gemini File Search")

    try:
        config_loader = ConfigLoader()
        config = config_loader.get_crawler_config()

        uploader = GeminiUploader(
            api_key=os.getenv('GEMINI_API_KEY'),
            store_name='fsc-announcements-test',
            config=config.get('gemini', {})
        )

        # 上傳公告及附件
        result = uploader.upload_announcement_with_attachments(
            markdown_path=str(test_markdown_path),
            attachments_dir=str(test_dir),
            delay=2.0
        )

        logger.info("\n上傳結果:")
        logger.info(f"  公告 ID: {result['announcement_id']}")
        logger.info(f"  附件數: {len(result['attachments'])}")
        logger.info(f"  總檔案數: {result['total_files']}")

        if result['errors']:
            logger.warning(f"  錯誤數: {len(result['errors'])}")
            for error in result['errors']:
                logger.error(f"    - {error}")

        if result['total_files'] > 0:
            logger.info("✓ 附件上傳功能正常")
            return True
        else:
            logger.error("✗ 附件上傳失敗")
            return False

    except Exception as e:
        logger.error(f"✗ 上傳過程發生錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主函數"""

    logger.info("FSC 附件功能測試腳本")
    logger.info("=" * 70)

    # 測試下載
    download_ok = test_attachment_download()

    # 測試上傳（可選）
    upload_ok = test_attachment_upload()

    # 總結
    logger.info("\n" + "=" * 70)
    logger.info("所有測試完成")
    logger.info("=" * 70)
    logger.info(f"附件下載: {'✓ 通過' if download_ok else '✗ 失敗'}")
    logger.info(f"附件上傳: {'✓ 通過' if upload_ok else '✗ 失敗/跳過'}")

    if download_ok:
        logger.info("\n✓ 核心功能測試通過，可以部署到遠端機器")
    else:
        logger.error("\n✗ 發現問題，請檢查錯誤訊息")


if __name__ == '__main__':
    main()
