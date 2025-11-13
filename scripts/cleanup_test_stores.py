"""清理測試用的 File Search Stores

警告：會刪除 store，請確認不是生產環境的 store！
生產環境 store: fscpenaltycases (490 筆裁罰案件)
"""

import os
from dotenv import load_dotenv
from loguru import logger

try:
    from google import genai
except ImportError:
    logger.error("請先安裝: pip install google-genai")
    exit(1)


def list_and_cleanup_stores():
    """列出並清理測試用的 stores"""

    # 載入環境變數
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        logger.error("請在 .env 中設定 GEMINI_API_KEY")
        return

    # 初始化客戶端
    client = genai.Client(api_key=api_key)

    # 列出現有 stores
    logger.info("列出現有 File Search Stores...")
    stores = list(client.file_search_stores.list())

    if not stores:
        logger.info("沒有找到任何 stores")
        return

    logger.info(f"\n找到 {len(stores)} 個 stores:\n")

    # 生產環境 store（不能刪除）
    PRODUCTION_STORES = [
        'fscpenaltycases',     # 裁罰案件生產環境
        'fsc-announcements',   # 公告正在爬取中（不可刪除）
    ]

    test_stores = []
    production_stores = []

    for i, store in enumerate(stores, 1):
        store_info = f"[{i}] {store.display_name} (ID: {store.name})"

        # 檢查是否為生產環境 store
        is_production = any(prod_name in store.display_name.lower()
                           for prod_name in PRODUCTION_STORES)

        if is_production:
            logger.warning(f"🔒 生產環境: {store_info}")
            production_stores.append(store)
        else:
            logger.info(f"🧪 測試環境: {store_info}")
            test_stores.append(store)

    # 詢問是否刪除測試 stores
    if test_stores:
        logger.info(f"\n找到 {len(test_stores)} 個測試用 stores")
        logger.warning(f"生產環境 stores 不會被刪除: {[s.display_name for s in production_stores]}")

        # 列出要刪除的 stores
        logger.info("\n準備刪除以下測試 stores:")
        for store in test_stores:
            logger.info(f"  - {store.display_name}")

        confirm = input("\n確定要刪除這些測試 stores 嗎？(yes/no): ")

        if confirm.lower() == 'yes':
            for store in test_stores:
                try:
                    logger.info(f"刪除: {store.display_name}")
                    client.file_search_stores.delete(name=store.name)
                    logger.info(f"✓ 已刪除: {store.display_name}")
                except Exception as e:
                    logger.error(f"✗ 刪除失敗: {store.display_name} - {e}")

            logger.info("\n✓ 清理完成！")
        else:
            logger.info("取消刪除")
    else:
        logger.info("\n沒有找到測試用的 stores")


if __name__ == '__main__':
    logger.info("=== File Search Store 清理工具 ===")
    list_and_cleanup_stores()
