#!/usr/bin/env python3
"""
通用 Gemini 上傳腳本 - 支援公告與裁罰案件

功能:
1. 從 JSONL 產生 Markdown 檔案（含時效性標註）
2. 上傳到 Gemini File Search Store
3. 驗證上傳完整性
4. 清理暫存檔案

支援資料類型:
- announcements (公告)
- penalties (裁罰案件)
"""

import sys
import shutil
import argparse
from pathlib import Path
from typing import Optional, Literal

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processor.markdown_formatter import MarkdownFormatter, BatchMarkdownFormatter
from src.processor.penalty_markdown_formatter import PenaltyMarkdownFormatter, BatchPenaltyMarkdownFormatter
from src.processor.version_tracker import VersionTracker
from src.uploader.gemini_uploader import GeminiUploader
from src.storage.jsonl_handler import JSONLHandler
from src.utils.logger import logger
from dotenv import load_dotenv
import os


DataType = Literal['announcements', 'penalties']


def generate_markdown_files(
    data_type: DataType,
    output_dir: Path,
    since_date: Optional[str] = None,
    enable_temporal_annotation: bool = True
) -> int:
    """
    產生 Markdown 檔案

    Args:
        data_type: 資料類型 (announcements/penalties)
        output_dir: 輸出目錄
        since_date: 只處理此日期之後的資料
        enable_temporal_annotation: 啟用時效性標註（僅對公告有效）

    Returns:
        產生的檔案數量
    """
    logger.info(f"產生 {data_type} Markdown 檔案...")
    logger.info(f"  輸出目錄: {output_dir}")
    if since_date:
        logger.info(f"  增量模式: >= {since_date}")
    if data_type == 'announcements' and enable_temporal_annotation:
        logger.info(f"  時效性標註: 啟用")

    # 讀取資料
    handler = JSONLHandler()

    # 決定資料檔案路徑
    if data_type == 'announcements':
        jsonl_path = 'data/announcements/raw.jsonl'
    elif data_type == 'penalties':
        jsonl_path = 'data/penalties/raw.jsonl'
    else:
        raise ValueError(f"不支援的資料類型: {data_type}")

    # 檢查檔案是否存在
    if not Path(jsonl_path).exists():
        logger.error(f"資料檔案不存在: {jsonl_path}")
        return 0

    # 讀取資料
    all_items = handler.read_all(data_type)
    logger.info(f"讀取 {len(all_items)} 筆資料")

    if not all_items:
        logger.warning("沒有資料")
        return 0

    # 篩選日期
    if since_date:
        items = [
            item for item in all_items
            if item.get('date', '') >= since_date
        ]
        logger.info(f"篩選後: {len(items)} 筆")
    else:
        items = all_items

    if not items:
        logger.warning("沒有符合條件的資料")
        return 0

    # 建立輸出目錄
    output_dir.mkdir(parents=True, exist_ok=True)

    # 根據資料類型選擇格式化器
    if data_type == 'announcements':
        # 建立版本追蹤器（用於時效性標註）
        version_tracker = None
        if enable_temporal_annotation:
            logger.info("建立版本追蹤器...")
            version_tracker = VersionTracker()
            stats = version_tracker.build_version_map(items)
            logger.info(f"  修正類公告: {stats['amendment_count']} 筆")
            logger.info(f"  有多版本的法規: {stats['regulation_count']} 個")

        formatter = MarkdownFormatter(version_tracker=version_tracker)

    elif data_type == 'penalties':
        formatter = PenaltyMarkdownFormatter()

    # 產生 Markdown
    created = 0
    failed = 0

    for item in items:
        try:
            # 格式化
            if data_type == 'announcements':
                md_content = formatter.format_announcement(item)
            elif data_type == 'penalties':
                md_content = formatter.format_penalty(item)

            # 建立檔名
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
                'examination_bureau': '檢查局',
                'fsc_main': '金管會',
                'unknown': '未分類'
            }
            source_cn = source_mapping.get(source, source)

            filename = f"{item_id}_{source_cn}_{safe_title}.md"
            filepath = output_dir / filename

            # 寫入檔案
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)

            created += 1

            if created % 100 == 0:
                logger.info(f"  已產生 {created} 個檔案...")

        except Exception as e:
            logger.error(f"產生 Markdown 失敗: {item.get('id')} - {e}")
            failed += 1

    logger.info(f"✓ 產生完成: {created} 個檔案")
    if failed > 0:
        logger.warning(f"  失敗: {failed} 個")

    return created


def upload_to_gemini(
    data_type: DataType,
    api_key: Optional[str] = None,
    store_name: Optional[str] = None,
    since_date: Optional[str] = None,
    auto_cleanup: bool = True,
    skip_markdown: bool = False,
    enable_temporal_annotation: bool = True
) -> bool:
    """
    上傳資料到 Gemini

    Args:
        data_type: 資料類型 (announcements/penalties)
        api_key: Gemini API Key
        store_name: Store 名稱
        since_date: 只上傳此日期之後的資料
        auto_cleanup: 自動清理暫存檔案
        skip_markdown: 跳過 Markdown 產生（使用現有檔案）
        enable_temporal_annotation: 啟用時效性標註

    Returns:
        是否成功
    """
    # 載入環境變數
    load_dotenv()

    # API Key
    api_key = api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("未設定 GEMINI_API_KEY")
        return False

    # Store 名稱（依資料類型使用不同的預設值）
    if not store_name:
        if data_type == 'announcements':
            store_name = os.getenv('ANNOUNCEMENTS_STORE_NAME', 'fsc-announcements')
        elif data_type == 'penalties':
            store_name = os.getenv('PENALTIES_STORE_NAME', 'fsc-penalties')

    # 暫存目錄
    temp_dir = Path(f'data/temp_markdown/{data_type}')

    try:
        logger.info("=" * 70)
        logger.info(f"Gemini 上傳流程 - {data_type}")
        logger.info("=" * 70)
        logger.info(f"Store: {store_name}")
        logger.info(f"資料類型: {data_type}")
        logger.info(f"增量模式: {since_date is not None}")
        if data_type == 'announcements':
            logger.info(f"時效性標註: {'啟用' if enable_temporal_annotation else '停用'}")
        logger.info("")

        # ===== 步驟 1: 產生 Markdown 檔案 =====
        if not skip_markdown:
            logger.info("步驟 1/4: 產生 Markdown 檔案")
            logger.info("-" * 70)

            # 清理舊的暫存目錄
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.info(f"已清理舊的暫存目錄: {temp_dir}")

            # 產生 Markdown
            file_count = generate_markdown_files(
                data_type=data_type,
                output_dir=temp_dir,
                since_date=since_date,
                enable_temporal_annotation=enable_temporal_annotation
            )

            if file_count == 0:
                logger.warning("沒有檔案需要上傳")
                return True

            logger.info("✓ 步驟 1 完成")
            logger.info("")

        else:
            logger.info("步驟 1/4: 使用現有 Markdown 檔案")
            logger.info("-" * 70)

            if not temp_dir.exists():
                logger.error(f"暫存目錄不存在: {temp_dir}")
                return False

            existing_files = list(temp_dir.glob('*.md'))
            logger.info(f"找到 {len(existing_files)} 個現有檔案")
            logger.info("✓ 步驟 1 完成")
            logger.info("")

        # ===== 步驟 2: 上傳到 Gemini =====
        logger.info("步驟 2/4: 上傳到 Gemini")
        logger.info("-" * 70)

        uploader = GeminiUploader(
            api_key=api_key,
            store_name=store_name,
            max_retries=3
        )

        stats = uploader.upload_directory(
            str(temp_dir),
            skip_existing=True
        )

        logger.info(f"上傳完成: {stats['uploaded_files']}/{stats['total_files']}")
        logger.info(f"失敗: {stats['failed_files']}")
        logger.info(f"跳過: {stats['skipped_files']}")
        logger.info("✓ 步驟 2 完成")
        logger.info("")

        # ===== 步驟 3: 驗證完整性 =====
        logger.info("步驟 3/4: 驗證上傳完整性")
        logger.info("-" * 70)

        report = uploader.verify_upload_completeness()

        logger.info(f"總計: {report['total']}")
        logger.info(f"成功: {report['successful']}")
        logger.info(f"失敗: {report['failed']}")

        success = report['failed'] == 0

        if not success:
            logger.warning(f"有 {report['failed']} 個檔案上傳失敗:")
            for item in report['failed_files'][:10]:
                logger.warning(f"  - {item['display_name']}: {item['error']}")
            logger.info("✗ 步驟 3 發現問題")
        else:
            logger.info("✓ 步驟 3 完成 - 所有檔案上傳成功")

        logger.info("")

        # ===== 步驟 4: 清理暫存檔案 =====
        if auto_cleanup:
            logger.info("步驟 4/4: 清理暫存檔案")
            logger.info("-" * 70)

            if temp_dir.exists():
                file_count = len(list(temp_dir.glob('*.md')))
                shutil.rmtree(temp_dir)
                logger.info(f"已刪除 {file_count} 個暫存 Markdown 檔案")
                logger.info(f"已刪除暫存目錄: {temp_dir}")

            logger.info("✓ 步驟 4 完成")
            logger.info("")

        # ===== 完成 =====
        logger.info("=" * 70)
        if success:
            logger.info("✓ 上傳流程完成!")
        else:
            logger.warning("⚠ 上傳流程完成,但有部分失敗")
        logger.info("=" * 70)

        return success

    except Exception as e:
        logger.error(f"上傳流程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='上傳資料到 Gemini File Search Store',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:

  # 上傳所有公告（含時效性標註）
  python scripts/upload_to_gemini.py --type announcements

  # 上傳所有裁罰案件
  python scripts/upload_to_gemini.py --type penalties

  # 增量上傳公告（只上傳 2025-01-01 之後的）
  python scripts/upload_to_gemini.py --type announcements --since 2025-01-01

  # 上傳到指定 Store
  python scripts/upload_to_gemini.py --type announcements --store my-store-name

  # 不清理暫存檔案（用於除錯）
  python scripts/upload_to_gemini.py --type penalties --no-cleanup

  # 只產生 Markdown，不上傳
  python scripts/upload_to_gemini.py --type announcements --markdown-only
        """
    )

    parser.add_argument(
        '--type',
        choices=['announcements', 'penalties'],
        required=True,
        help='資料類型'
    )

    parser.add_argument(
        '--store',
        type=str,
        help='Gemini Store 名稱（預設: fsc-announcements 或 fsc-penalties）'
    )

    parser.add_argument(
        '--since',
        type=str,
        help='只上傳此日期之後的資料（格式: YYYY-MM-DD）'
    )

    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='不清理暫存檔案'
    )

    parser.add_argument(
        '--skip-markdown',
        action='store_true',
        help='跳過 Markdown 產生，使用現有檔案'
    )

    parser.add_argument(
        '--no-temporal',
        action='store_true',
        help='停用時效性標註（僅對公告有效）'
    )

    parser.add_argument(
        '--markdown-only',
        action='store_true',
        help='只產生 Markdown，不上傳'
    )

    args = parser.parse_args()

    # 只產生 Markdown
    if args.markdown_only:
        temp_dir = Path(f'data/temp_markdown/{args.type}')

        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        file_count = generate_markdown_files(
            data_type=args.type,
            output_dir=temp_dir,
            since_date=args.since,
            enable_temporal_annotation=not args.no_temporal
        )

        logger.info(f"\n✓ Markdown 產生完成: {file_count} 個檔案")
        logger.info(f"輸出目錄: {temp_dir}")
        return

    # 完整上傳流程
    success = upload_to_gemini(
        data_type=args.type,
        store_name=args.store,
        since_date=args.since,
        auto_cleanup=not args.no_cleanup,
        skip_markdown=args.skip_markdown,
        enable_temporal_annotation=not args.no_temporal
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
