#!/usr/bin/env python3
"""
驗證 Gemini File Search Store 上傳完整性

檢查：
1. 本地檔案總數
2. Store 中實際檔案數
3. 列出缺失的檔案
4. 提供重新上傳失敗檔案的命令
"""

import sys
from pathlib import Path
from typing import Set, List, Dict, Any

# 加入專案根目錄
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.uploader.gemini_uploader import GeminiUploader


def get_local_files(directory: str, pattern: str = "*.txt") -> Set[str]:
    """
    取得本地檔案列表

    Args:
        directory: 目錄路徑
        pattern: 檔案模式

    Returns:
        檔案名稱集合（不含路徑）
    """
    dir_path = Path(directory)
    files = set()

    for filepath in dir_path.glob(pattern):
        files.add(filepath.name)

    return files


def get_store_files(store_id: str, api_key: str) -> Set[str]:
    """
    取得 Store 中的檔案列表

    Args:
        store_id: Store ID
        api_key: Gemini API Key

    Returns:
        檔案名稱集合
    """
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    client = genai.Client()

    files = set()

    try:
        # 列出 Store 中的所有檔案
        store = client.file_search_stores.get(name=store_id)

        # 使用 list_files 取得檔案列表
        # 注意：這個 API 可能需要分頁處理
        response = client.file_search_stores.list_files(
            file_search_store_name=store_id
        )

        for file in response:
            # 從 display_name 取得檔案名稱
            display_name = file.display_name
            files.add(display_name)

        logger.info(f"Store 中共有 {len(files)} 個檔案")

    except Exception as e:
        logger.error(f"無法取得 Store 檔案列表: {e}")
        # 嘗試替代方法：從 manifest 讀取
        logger.info("嘗試從上傳記錄讀取...")

    return files


def verify_upload(
    local_dir: str,
    store_id: str,
    api_key: str,
    pattern: str = "*.txt"
) -> Dict[str, Any]:
    """
    驗證上傳完整性

    Args:
        local_dir: 本地目錄
        store_id: Store ID
        api_key: API Key
        pattern: 檔案模式

    Returns:
        驗證結果
    """
    logger.info("=" * 80)
    logger.info("驗證 Gemini File Search Store 上傳完整性")
    logger.info("=" * 80)

    # 1. 取得本地檔案
    logger.info(f"\n[1/3] 掃描本地檔案: {local_dir}")
    local_files = get_local_files(local_dir, pattern)
    logger.info(f"✓ 本地檔案: {len(local_files)} 個")

    # 2. 取得 Store 中的檔案
    logger.info(f"\n[2/3] 查詢 Store 檔案: {store_id}")
    store_files = get_store_files(store_id, api_key)
    logger.info(f"✓ Store 檔案: {len(store_files)} 個")

    # 3. 比對差異
    logger.info(f"\n[3/3] 比對差異")
    missing_files = local_files - store_files
    extra_files = store_files - local_files

    # 統計
    result = {
        'local_count': len(local_files),
        'store_count': len(store_files),
        'missing_count': len(missing_files),
        'extra_count': len(extra_files),
        'missing_files': sorted(list(missing_files)),
        'extra_files': sorted(list(extra_files)),
        'complete': len(missing_files) == 0
    }

    # 報告
    logger.info("\n" + "=" * 80)
    logger.info("驗證結果")
    logger.info("=" * 80)

    logger.info(f"\n本地檔案: {result['local_count']}")
    logger.info(f"Store 檔案: {result['store_count']}")
    logger.info(f"缺失檔案: {result['missing_count']}")
    logger.info(f"多餘檔案: {result['extra_count']}")

    if result['complete']:
        logger.info("\n✅ 所有檔案都已上傳！")
    else:
        logger.warning(f"\n⚠️ 有 {result['missing_count']} 個檔案尚未上傳")

        if result['missing_count'] <= 50:
            logger.warning("\n缺失的檔案:")
            for filename in result['missing_files'][:20]:
                logger.warning(f"  - {filename}")

            if result['missing_count'] > 20:
                logger.warning(f"  ... 還有 {result['missing_count'] - 20} 個")

        # 生成重新上傳命令
        logger.info("\n重新上傳缺失檔案的方法:")
        logger.info("1. 檢查上傳日誌找出失敗原因")
        logger.info("2. 手動重新上傳失敗的檔案")
        logger.info("3. 或刪除 Store 重新全部上傳")

    if result['extra_count'] > 0:
        logger.info(f"\n注意: Store 中有 {result['extra_count']} 個本地沒有的檔案")
        logger.info("可能是之前上傳的舊版本，建議清理")

    return result


def main():
    """主函數"""
    import argparse
    import os

    parser = argparse.ArgumentParser(description='驗證 Gemini Store 上傳完整性')
    parser.add_argument(
        '--local-dir',
        default='data/plaintext_optimized/penalties_individual',
        help='本地檔案目錄'
    )
    parser.add_argument(
        '--store-id',
        required=True,
        help='Gemini File Search Store ID'
    )
    parser.add_argument(
        '--api-key',
        default=os.getenv('GEMINI_API_KEY'),
        help='Gemini API Key (預設從環境變數讀取)'
    )
    parser.add_argument(
        '--pattern',
        default='*.txt',
        help='檔案模式'
    )

    args = parser.parse_args()

    if not args.api_key:
        logger.error("請提供 GEMINI_API_KEY")
        sys.exit(1)

    try:
        result = verify_upload(
            local_dir=args.local_dir,
            store_id=args.store_id,
            api_key=args.api_key,
            pattern=args.pattern
        )

        # 返回碼
        sys.exit(0 if result['complete'] else 1)

    except Exception as e:
        logger.error(f"\n❌ 驗證失敗: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    # 設定日誌
    logger.add(
        "logs/verify_gemini_upload.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG"
    )

    main()
