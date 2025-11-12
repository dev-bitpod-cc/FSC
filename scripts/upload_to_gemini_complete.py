#!/usr/bin/env python3
"""
完整的 Gemini 上傳流程

功能:
1. 從 JSONL 產生暫存 Markdown 檔案
2. 上傳到 Gemini File Search Store
3. 驗證上傳完整性
4. 清理暫存檔案

特點:
- 支援增量上傳 (只上傳新增的公告)
- 支援重建整個 Store (切換 API Key)
- 自動清理暫存檔案
"""

import sys
import shutil
from pathlib import Path
from typing import Optional

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processor.markdown_formatter import BatchMarkdownFormatter
from src.uploader.gemini_uploader import GeminiUploader
from src.storage.jsonl_handler import JSONLHandler
from src.utils.logger import logger
from dotenv import load_dotenv
import os


def upload_to_gemini(
    api_key: Optional[str] = None,
    store_name: Optional[str] = None,
    force_regenerate: bool = False,
    since_date: Optional[str] = None,
    auto_cleanup: bool = True
) -> bool:
    """
    完整的上傳流程

    Args:
        api_key: Gemini API Key (預設從環境變數讀取)
        store_name: Store 名稱 (預設從環境變數讀取)
        force_regenerate: 強制重新產生 Markdown (預設 False)
        since_date: 只上傳此日期之後的公告 (格式: YYYY-MM-DD, None=全部)
        auto_cleanup: 自動清理暫存檔案 (預設 True)

    Returns:
        是否成功
    """
    # 載入環境變數
    load_dotenv()

    # API Key 和 Store 名稱
    api_key = api_key or os.getenv('GEMINI_API_KEY')
    store_name = store_name or os.getenv('FILE_SEARCH_STORE_NAME', 'fsc-announcements')

    if not api_key:
        logger.error("未設定 GEMINI_API_KEY")
        return False

    temp_dir = Path('data/temp_markdown')

    try:
        logger.info("=" * 60)
        logger.info("Gemini 上傳流程")
        logger.info("=" * 60)
        logger.info(f"Store: {store_name}")
        logger.info(f"增量模式: {since_date is not None}")
        logger.info("")

        # ===== 步驟 1: 產生 Markdown 檔案 =====
        logger.info("步驟 1/4: 產生 Markdown 檔案")
        logger.info("-" * 60)

        if force_regenerate or not temp_dir.exists():
            # 清理舊的暫存目錄
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.info(f"已清理舊的暫存目錄: {temp_dir}")

            # 產生新的 Markdown
            logger.info("從 JSONL 產生 Markdown 檔案...")

            # 如果是增量模式,只產生新公告的 Markdown
            if since_date:
                handler = JSONLHandler()
                all_items = handler.read_all('announcements')

                new_items = [
                    item for item in all_items
                    if item.get('date', '') >= since_date
                ]

                logger.info(f"找到 {len(new_items)} 筆新公告 (>= {since_date})")

                if not new_items:
                    logger.warning("沒有新公告需要上傳")
                    return True

                # 建立暫存目錄
                temp_dir.mkdir(parents=True, exist_ok=True)

                # 產生 Markdown
                formatter = BatchMarkdownFormatter()
                formatter.handler = handler

                created = 0
                for item in new_items:
                    try:
                        md_content = formatter.format_announcement(item)

                        # 檔名: ID_來源_標題
                        item_id = item.get('id', 'unknown')
                        title = item.get('title', '無標題')[:50]
                        source = item.get('metadata', {}).get('source', 'unknown')

                        # 清理檔名
                        import re
                        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)

                        source_mapping = {
                            'bank_bureau': '銀行局',
                            'securities_bureau': '證券期貨局',
                            'insurance_bureau': '保險局',
                            'inspection_bureau': '檢查局',
                            'unknown': '未分類'
                        }
                        source_cn = source_mapping.get(source, source)

                        filename = f"{item_id}_{source_cn}_{safe_title}.md"
                        filepath = temp_dir / filename

                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(md_content)

                        created += 1

                    except Exception as e:
                        logger.error(f"產生 Markdown 失敗: {item.get('id')} - {e}")

                logger.info(f"產生 {created} 個 Markdown 檔案")

            else:
                # 產生全部公告的 Markdown
                formatter = BatchMarkdownFormatter()
                handler = JSONLHandler()
                formatter.handler = handler

                result = formatter.format_individual_files(
                    data_type='announcements',
                    output_dir=str(temp_dir)
                )

                logger.info(f"產生 {result['created_files']} 個 Markdown 檔案")

        else:
            # 使用現有的暫存檔案
            existing_files = list(temp_dir.glob('*.md'))
            logger.info(f"使用現有的暫存目錄: {len(existing_files)} 個檔案")

        logger.info("✓ 步驟 1 完成")
        logger.info("")

        # ===== 步驟 2: 上傳到 Gemini =====
        logger.info("步驟 2/4: 上傳到 Gemini")
        logger.info("-" * 60)

        uploader = GeminiUploader(
            api_key=api_key,
            store_name=store_name,
            max_retries=3
        )

        stats = uploader.upload_directory(
            str(temp_dir),
            skip_existing=True  # 跳過已上傳的檔案
        )

        logger.info(f"上傳完成: {stats['uploaded_files']}/{stats['total_files']}")
        logger.info(f"失敗: {stats['failed_files']}")
        logger.info(f"跳過: {stats['skipped_files']}")
        logger.info("✓ 步驟 2 完成")
        logger.info("")

        # ===== 步驟 3: 驗證完整性 =====
        logger.info("步驟 3/4: 驗證上傳完整性")
        logger.info("-" * 60)

        report = uploader.verify_upload_completeness()

        logger.info(f"總計: {report['total']}")
        logger.info(f"成功: {report['successful']}")
        logger.info(f"失敗: {report['failed']}")

        if report['failed'] > 0:
            logger.warning(f"有 {report['failed']} 個檔案上傳失敗:")
            for item in report['failed_files'][:10]:  # 只顯示前 10 個
                logger.warning(f"  - {item['display_name']}: {item['error']}")

            logger.info("✗ 步驟 3 發現問題")
            success = False
        else:
            logger.info("✓ 步驟 3 完成 - 所有檔案上傳成功")
            success = True

        logger.info("")

        # ===== 步驟 4: 清理暫存檔案 =====
        if auto_cleanup:
            logger.info("步驟 4/4: 清理暫存檔案")
            logger.info("-" * 60)

            if temp_dir.exists():
                file_count = len(list(temp_dir.glob('*.md')))
                shutil.rmtree(temp_dir)
                logger.info(f"已刪除 {file_count} 個暫存 Markdown 檔案")
                logger.info(f"已刪除暫存目錄: {temp_dir}")

            logger.info("✓ 步驟 4 完成")
            logger.info("")

        # ===== 完成 =====
        logger.info("=" * 60)
        if success:
            logger.info("✓ 上傳流程完成!")
        else:
            logger.warning("⚠ 上傳流程完成,但有部分失敗")
        logger.info("=" * 60)

        return success

    except Exception as e:
        logger.error(f"上傳流程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


def rebuild_store(
    api_key: Optional[str] = None,
    store_name: Optional[str] = None,
    delete_old_store: bool = False
) -> bool:
    """
    從 JSONL 重建整個 Gemini Store

    Args:
        api_key: 新的 API Key
        store_name: 新的 Store 名稱
        delete_old_store: 是否刪除舊的 Store

    Returns:
        是否成功
    """
    logger.info("=" * 60)
    logger.info("重建 Gemini Store")
    logger.info("=" * 60)

    # 載入環境變數
    load_dotenv()

    api_key = api_key or os.getenv('GEMINI_API_KEY')
    store_name = store_name or os.getenv('FILE_SEARCH_STORE_NAME', 'fsc-announcements')

    uploader = GeminiUploader(
        api_key=api_key,
        store_name=store_name
    )

    # 刪除舊 Store (選擇性)
    if delete_old_store:
        logger.warning(f"即將刪除 Store: {store_name}")
        response = input("確定要刪除嗎? (yes/no): ")
        if response.lower() == 'yes':
            try:
                uploader.delete_store()
                logger.info("已刪除舊 Store")
            except Exception as e:
                logger.error(f"刪除 Store 失敗: {e}")
        else:
            logger.info("取消刪除")

    # 重建 (force_regenerate=True, skip_existing=False)
    success = upload_to_gemini(
        api_key=api_key,
        store_name=store_name,
        force_regenerate=True,
        since_date=None,  # 全部重建
        auto_cleanup=True
    )

    # 上傳時 skip_existing=True,所以要特別處理
    # TODO: 需要修改 upload_to_gemini 支援 skip_existing 參數

    return success


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description='上傳公告到 Gemini File Search')
    parser.add_argument('--mode', choices=['upload', 'rebuild', 'incremental'],
                        default='upload', help='模式: upload(完整上傳) / rebuild(重建Store) / incremental(增量上傳)')
    parser.add_argument('--api-key', help='Gemini API Key (預設從環境變數讀取)')
    parser.add_argument('--store-name', help='Store 名稱 (預設從環境變數讀取)')
    parser.add_argument('--since-date', help='增量模式: 只上傳此日期之後的公告 (YYYY-MM-DD)')
    parser.add_argument('--force', action='store_true', help='強制重新產生 Markdown')
    parser.add_argument('--no-cleanup', action='store_true', help='不清理暫存檔案')
    parser.add_argument('--delete-old', action='store_true', help='重建模式: 刪除舊 Store')

    args = parser.parse_args()

    if args.mode == 'rebuild':
        success = rebuild_store(
            api_key=args.api_key,
            store_name=args.store_name,
            delete_old_store=args.delete_old
        )
    elif args.mode == 'incremental':
        if not args.since_date:
            logger.error("增量模式需要指定 --since-date")
            return 1

        success = upload_to_gemini(
            api_key=args.api_key,
            store_name=args.store_name,
            force_regenerate=args.force,
            since_date=args.since_date,
            auto_cleanup=not args.no_cleanup
        )
    else:  # upload
        success = upload_to_gemini(
            api_key=args.api_key,
            store_name=args.store_name,
            force_regenerate=args.force,
            since_date=args.since_date,
            auto_cleanup=not args.no_cleanup
        )

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
