#!/usr/bin/env python3
"""測試完整上傳流程 (小規模測試)"""

import sys
import shutil
from pathlib import Path

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processor.markdown_formatter import BatchMarkdownFormatter
from src.uploader.gemini_uploader import GeminiUploader
from src.storage.jsonl_handler import JSONLHandler
from src.utils.logger import logger
from dotenv import load_dotenv
import os
import re


def test_upload_workflow():
    """測試完整上傳流程"""

    # 載入環境變數
    load_dotenv()

    api_key = os.getenv('GEMINI_API_KEY')
    store_name = 'fsc-test-upload'  # 使用測試 Store

    if not api_key:
        logger.error("未設定 GEMINI_API_KEY")
        return False

    # 測試目錄
    test_dir = Path('data/test_upload_markdown')

    try:
        logger.info("=" * 60)
        logger.info("完整上傳流程測試 (5 筆公告)")
        logger.info("=" * 60)

        # ===== 步驟 1: 產生 Markdown 檔案 =====
        logger.info("\n步驟 1/4: 產生 Markdown 檔案")
        logger.info("-" * 60)

        # 清理舊的測試目錄
        if test_dir.exists():
            shutil.rmtree(test_dir)
            logger.info(f"已清理舊的測試目錄: {test_dir}")

        test_dir.mkdir(parents=True, exist_ok=True)

        # 讀取前 5 筆公告
        handler = JSONLHandler()
        all_items = handler.read_all('announcements')
        test_items = all_items[:5]

        logger.info(f"測試資料: {len(test_items)} 筆公告")

        # 產生 Markdown
        formatter = BatchMarkdownFormatter()
        formatter.handler = handler

        source_mapping = {
            'bank_bureau': '銀行局',
            'securities_bureau': '證券期貨局',
            'insurance_bureau': '保險局',
            'inspection_bureau': '檢查局',
            'unknown': '未分類'
        }

        for item in test_items:
            md_content = formatter.format_announcement(item)

            item_id = item.get('id', 'unknown')
            title = item.get('title', '無標題')
            source = item.get('metadata', {}).get('source', 'unknown')
            source_cn = source_mapping.get(source, source)

            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
            filename = f"{item_id}_{source_cn}_{safe_title}.md"

            filepath = test_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)

            logger.debug(f"✓ {filename}")

        logger.info(f"產生 {len(test_items)} 個 Markdown 檔案")
        logger.info("✓ 步驟 1 完成\n")

        # ===== 步驟 2: 上傳到 Gemini =====
        logger.info("步驟 2/4: 上傳到 Gemini")
        logger.info("-" * 60)

        uploader = GeminiUploader(
            api_key=api_key,
            store_name=store_name,
            max_retries=3
        )

        stats = uploader.upload_directory(
            str(test_dir),
            skip_existing=True
        )

        logger.info(f"上傳完成: {stats['uploaded_files']}/{stats['total_files']}")
        logger.info(f"失敗: {stats['failed_files']}")
        logger.info(f"跳過: {stats['skipped_files']}")
        logger.info("✓ 步驟 2 完成\n")

        # ===== 步驟 3: 驗證完整性 =====
        logger.info("步驟 3/4: 驗證上傳完整性")
        logger.info("-" * 60)

        report = uploader.verify_upload_completeness()

        logger.info(f"總計: {report['total']}")
        logger.info(f"成功: {report['successful']}")
        logger.info(f"失敗: {report['failed']}")

        if report['failed'] > 0:
            logger.warning(f"有 {report['failed']} 個檔案上傳失敗:")
            for item in report['failed_files']:
                logger.warning(f"  - {item['display_name']}: {item['error']}")

            logger.info("✗ 步驟 3 發現問題\n")
            success = False
        else:
            logger.info("✓ 步驟 3 完成 - 所有檔案上傳成功\n")
            success = True

        # ===== 步驟 4: 清理暫存檔案 =====
        logger.info("步驟 4/4: 清理暫存檔案")
        logger.info("-" * 60)

        if test_dir.exists():
            file_count = len(list(test_dir.glob('*.md')))
            shutil.rmtree(test_dir)
            logger.info(f"已刪除 {file_count} 個暫存 Markdown 檔案")
            logger.info(f"已刪除暫存目錄: {test_dir}")

        logger.info("✓ 步驟 4 完成\n")

        # ===== 完成 =====
        logger.info("=" * 60)
        if success:
            logger.info("✓ 上傳流程測試完成!")
        else:
            logger.warning("⚠ 上傳流程完成,但有部分失敗")
        logger.info("=" * 60)

        # 顯示 Store 資訊
        logger.info(f"\nStore 名稱: {store_name}")
        logger.info(f"Store ID: {uploader.store_id}")

        return success

    except Exception as e:
        logger.error(f"測試流程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_upload_workflow()
    sys.exit(0 if success else 1)
