"""
上傳優化後的 Plain Text 檔案到 Gemini File Search Store

此腳本將:
1. 建立新的 Gemini File Search Store (fsc-penalties-optimized)
2. 批次上傳所有優化的 plain text 檔案
3. 更新 file_mapping.json,填入 gemini_id 和 gemini_uri
4. 產生上傳報告

使用方式:
    python scripts/upload_optimized_to_gemini.py --source penalties
    python scripts/upload_optimized_to_gemini.py --plaintext-dir data/plaintext_optimized/penalties_individual
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

# 加入專案根目錄到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.uploader.gemini_uploader import GeminiUploader
from loguru import logger


def update_file_mapping_with_gemini_info(
    mapping_file: str,
    upload_manifest: Dict[str, Any],
    plaintext_dir: str
) -> Dict[str, Any]:
    """
    更新 file_mapping.json,填入 Gemini file ID 和 URI

    Args:
        mapping_file: file_mapping.json 路徑
        upload_manifest: 上傳器的 manifest (包含 filepath -> file_id 映射)
        plaintext_dir: plain text 檔案目錄

    Returns:
        更新後的 mapping
    """
    logger.info("更新 file_mapping.json...")

    # 讀取 file_mapping.json
    mapping_path = Path(mapping_file)
    if not mapping_path.exists():
        logger.error(f"file_mapping.json 不存在: {mapping_file}")
        return {}

    with open(mapping_path, 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    # 統計
    updated_count = 0
    failed_count = 0

    # 建立 filepath -> file_id 的映射
    filepath_to_gemini = {}
    for filepath, info in upload_manifest.get('uploaded', {}).items():
        if info['status'] == 'success' and info.get('file_id'):
            filepath_to_gemini[filepath] = {
                'file_id': info['file_id'],
                'display_name': info.get('display_name', '')
            }

    # 更新 mapping
    plaintext_path = Path(plaintext_dir)

    for doc_id, doc_info in mapping.items():
        # 推導檔案路徑
        expected_filepath = plaintext_path / f"{doc_id}.txt"
        expected_filepath_str = str(expected_filepath)

        # 檢查是否上傳成功
        if expected_filepath_str in filepath_to_gemini:
            gemini_info = filepath_to_gemini[expected_filepath_str]

            # 更新 gemini_id 和 gemini_uri
            doc_info['gemini_id'] = gemini_info['file_id']
            # URI 格式: https://generativelanguage.googleapis.com/v1beta/files/{file_id}
            doc_info['gemini_uri'] = f"https://generativelanguage.googleapis.com/v1beta/{gemini_info['file_id']}"

            updated_count += 1
            logger.debug(f"更新 {doc_id}: gemini_id={gemini_info['file_id'][:20]}...")

        else:
            logger.warning(f"未找到上傳記錄: {doc_id} (檔案: {expected_filepath_str})")
            failed_count += 1

    # 儲存更新後的 mapping
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    logger.info(f"file_mapping.json 更新完成")
    logger.info(f"  已更新: {updated_count} 筆")
    logger.info(f"  未找到: {failed_count} 筆")

    return mapping


def upload_optimized_plaintext(
    plaintext_dir: str = 'data/plaintext_optimized/penalties_individual',
    mapping_file: str = 'data/penalties/file_mapping.json',
    store_name: str = 'fsc-penalties-optimized',
    delay: float = 1.5,
    skip_existing: bool = True,
    update_mapping: bool = True
) -> Dict[str, Any]:
    """
    上傳優化後的 Plain Text 檔案到 Gemini

    Args:
        plaintext_dir: 優化檔案目錄
        mapping_file: file_mapping.json 路徑
        store_name: Gemini Store 名稱
        delay: 上傳間隔秒數
        skip_existing: 是否跳過已上傳的檔案
        update_mapping: 是否更新 file_mapping.json

    Returns:
        上傳統計資訊
    """
    logger.info("=" * 80)
    logger.info("上傳優化 Plain Text 檔案到 Gemini File Search")
    logger.info("=" * 80)
    logger.info(f"\n檔案目錄: {plaintext_dir}")
    logger.info(f"Store 名稱: {store_name}")
    logger.info(f"上傳間隔: {delay} 秒")

    # 檢查目錄
    plaintext_path = Path(plaintext_dir)
    if not plaintext_path.exists():
        logger.error(f"目錄不存在: {plaintext_dir}")
        return {}

    # 初始化上傳器
    logger.info("\n初始化 Gemini Uploader...")
    uploader = GeminiUploader(
        store_name=store_name,
        max_retries=3,
        retry_delay=2.0
    )

    # 建立或取得 Store
    logger.info("\n建立/取得 File Search Store...")
    store_id = uploader.get_or_create_store()
    logger.info(f"Store ID: {store_id}")

    # 上傳所有 .txt 檔案
    logger.info("\n開始上傳檔案...")
    stats = uploader.upload_directory(
        directory=plaintext_dir,
        pattern="*.txt",
        delay=delay,
        skip_existing=skip_existing
    )

    # 更新 file_mapping.json
    if update_mapping:
        logger.info("\n更新 file_mapping.json...")
        mapping = update_file_mapping_with_gemini_info(
            mapping_file=mapping_file,
            upload_manifest=uploader.manifest,
            plaintext_dir=plaintext_dir
        )

    # 最終報告
    logger.info("\n" + "=" * 80)
    logger.info("上傳完成!")
    logger.info("=" * 80)
    logger.info(f"\n總檔案數: {stats['total_files']}")
    logger.info(f"成功上傳: {stats['uploaded_files']}")
    logger.info(f"跳過(已上傳): {stats['skipped_files']}")
    logger.info(f"上傳失敗: {stats['failed_files']}")
    logger.info(f"總大小: {stats['total_bytes'] / 1024:.2f} KB ({stats['total_bytes'] / 1024 / 1024:.2f} MB)")

    if stats['failed_files'] > 0:
        logger.warning(f"\n⚠️ 有 {stats['failed_files']} 個檔案上傳失敗")
        failed_uploads = uploader.get_failed_uploads()
        logger.warning("失敗的檔案:")
        for failed in failed_uploads:
            logger.warning(f"  - {failed['display_name']}: {failed.get('error', 'Unknown error')}")

    # Store 資訊
    logger.info(f"\n✅ Gemini File Search Store:")
    logger.info(f"   Store ID: {store_id}")
    logger.info(f"   Store 名稱: {store_name}")

    if update_mapping:
        logger.info(f"\n✅ file_mapping.json 已更新:")
        logger.info(f"   位置: {mapping_file}")
        logger.info(f"   包含 gemini_id 和 gemini_uri")

    logger.info("\n下一步: 整合到 FSC-Penalties-Deploy 前端")
    logger.info(f"  1. 更新前端的 Store ID 為: {store_id}")
    logger.info(f"  2. 複製更新後的 file_mapping.json 到前端專案")

    return stats


def retry_failed_uploads(
    plaintext_dir: str = 'data/plaintext_optimized/penalties_individual',
    store_name: str = 'fsc-penalties-optimized',
    delay: float = 2.0
):
    """
    重試上傳失敗的檔案

    Args:
        plaintext_dir: 優化檔案目錄
        store_name: Gemini Store 名稱
        delay: 上傳間隔秒數
    """
    logger.info("=" * 80)
    logger.info("重試失敗的上傳")
    logger.info("=" * 80)

    # 初始化上傳器
    uploader = GeminiUploader(
        store_name=store_name,
        max_retries=3,
        retry_delay=2.0
    )

    # 取得失敗的檔案
    failed_uploads = uploader.get_failed_uploads()

    if not failed_uploads:
        logger.info("沒有失敗的上傳需要重試")
        return

    logger.info(f"找到 {len(failed_uploads)} 個失敗的上傳")

    # 取得 Store
    uploader.get_or_create_store()

    # 逐一重試
    success_count = 0
    still_failed_count = 0

    for i, failed in enumerate(failed_uploads, 1):
        filepath = failed['filepath']
        display_name = failed['display_name']

        logger.info(f"\n重試 [{i}/{len(failed_uploads)}]: {display_name}")
        logger.info(f"  原因: {failed.get('error', 'Unknown error')}")

        # 重試上傳
        success = uploader.upload_and_add(filepath, display_name, delay)

        if success:
            success_count += 1
            logger.info(f"  ✓ 重試成功")
        else:
            still_failed_count += 1
            logger.warning(f"  ✗ 重試仍失敗")

    # 報告
    logger.info("\n" + "=" * 80)
    logger.info("重試完成")
    logger.info("=" * 80)
    logger.info(f"成功: {success_count}")
    logger.info(f"仍失敗: {still_failed_count}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='上傳優化 Plain Text 檔案到 Gemini')
    parser.add_argument('--plaintext-dir', default='data/plaintext_optimized/penalties_individual', help='優化檔案目錄')
    parser.add_argument('--mapping-file', default='data/penalties/file_mapping.json', help='file_mapping.json 路徑')
    parser.add_argument('--store-name', default='fsc-penalties-optimized', help='Gemini Store 名稱')
    parser.add_argument('--delay', type=float, default=1.5, help='上傳間隔秒數 (預設 1.5)')
    parser.add_argument('--no-skip-existing', action='store_true', help='不跳過已上傳的檔案')
    parser.add_argument('--no-update-mapping', action='store_true', help='不更新 file_mapping.json')
    parser.add_argument('--retry-failed', action='store_true', help='只重試失敗的上傳')

    args = parser.parse_args()

    try:
        if args.retry_failed:
            # 重試模式
            retry_failed_uploads(
                plaintext_dir=args.plaintext_dir,
                store_name=args.store_name,
                delay=args.delay
            )
        else:
            # 正常上傳模式
            stats = upload_optimized_plaintext(
                plaintext_dir=args.plaintext_dir,
                mapping_file=args.mapping_file,
                store_name=args.store_name,
                delay=args.delay,
                skip_existing=not args.no_skip_existing,
                update_mapping=not args.no_update_mapping
            )

            # 如果有失敗的檔案,提示可以重試
            if stats.get('failed_files', 0) > 0:
                logger.info("\n提示: 可使用 --retry-failed 重試失敗的上傳")

    except Exception as e:
        logger.error(f"\n❌ 錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    # 設定日誌
    logger.add(
        "logs/upload_optimized_to_gemini.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG"
    )

    main()
