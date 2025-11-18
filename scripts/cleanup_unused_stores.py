#!/usr/bin/env python3
"""
清理未使用的 Gemini Stores
保留 Deploy 專案使用的 Store
"""

import sys
import os
from pathlib import Path

# 加入專案根目錄
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from google import genai
from loguru import logger

# 載入環境變數
load_dotenv()

# Deploy 專案使用的 Store（保留）
KEEP_STORES = {
    'fileSearchStores/fscpenalties-tu709bvr1qti',  # FSC-Penalties-Deploy
    'fileSearchStores/fscpenaltycases1762854180-9kooa996ag5a',  # Sanction
}

# 需要刪除的 Store
DELETE_STORES = [
    'fileSearchStores/fscpenaltycases1762852550-df677oxvk9ke',
    'fileSearchStores/fscpenaltycases1762853298-pp7xw875g3te',
    'fileSearchStores/teststore-n2haofckqioh',
    'fileSearchStores/fscpenaltycases1762853753-f1kefbyo3sqo',
    'fileSearchStores/fscpenaltycases1762854027-y7a8l1qc6elv',
    'fileSearchStores/fscpenaltiesoptimizedtest-ixrg0l5s4967',
    'fileSearchStores/fscpenaltiesoptimized-amgl070m85d5',
    'fileSearchStores/fscpenaltiesfsc490-eg8q35dtsquz',
]

def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='清理未使用的 Gemini Stores')
    parser.add_argument('--yes', '-y', action='store_true', help='跳過確認')
    args = parser.parse_args()

    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        logger.error("請設定 GEMINI_API_KEY 環境變數")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    logger.info("=" * 80)
    logger.info("清理未使用的 Gemini Stores")
    logger.info("=" * 80)

    logger.info(f"\n保留的 Store: {len(KEEP_STORES)} 個")
    for store_id in KEEP_STORES:
        logger.info(f"  ✓ {store_id}")

    logger.info(f"\n準備刪除: {len(DELETE_STORES)} 個")
    for store_id in DELETE_STORES:
        logger.info(f"  ✗ {store_id}")

    if not args.yes:
        print("\n" + "=" * 80)
        response = input("確定要刪除以上 Store 嗎？(yes/no): ")

        if response.lower() != 'yes':
            logger.info("取消刪除")
            return

    logger.info("\n開始刪除...")

    success_count = 0
    failed_count = 0

    for i, store_id in enumerate(DELETE_STORES, 1):
        try:
            logger.info(f"\n[{i}/{len(DELETE_STORES)}] 刪除: {store_id}")
            client.file_search_stores.delete(name=store_id)
            logger.info(f"✓ 刪除成功")
            success_count += 1

        except Exception as e:
            logger.error(f"✗ 刪除失敗: {e}")
            failed_count += 1

    logger.info("\n" + "=" * 80)
    logger.info("清理完成")
    logger.info("=" * 80)
    logger.info(f"成功刪除: {success_count}/{len(DELETE_STORES)}")
    logger.info(f"失敗: {failed_count}")

    if failed_count > 0:
        logger.warning("部分 Store 刪除失敗，可能已被刪除或不存在")

if __name__ == '__main__':
    main()
