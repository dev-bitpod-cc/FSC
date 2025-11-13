"""簡單測試 Gemini File Search 查詢"""

import os
from dotenv import load_dotenv
from loguru import logger

try:
    from google import genai
    from google.genai import types
except ImportError:
    logger.error("請先安裝: pip install google-genai")
    exit(1)


def test_simple_query():
    """測試基本查詢功能"""

    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        logger.error("請在 .env 中設定 GEMINI_API_KEY")
        return

    client = genai.Client(api_key=api_key)

    # 列出所有 stores
    stores = list(client.file_search_stores.list())
    logger.info(f"找到 {len(stores)} 個 stores")

    if len(stores) < 2:
        logger.error("需要至少 2 個 stores 才能測試")
        return

    # 選擇兩個測試 stores（避開生產環境的）
    test_stores = [s for s in stores if 'test' in s.display_name.lower()]

    if len(test_stores) < 2:
        logger.warning(f"只找到 {len(test_stores)} 個測試 stores，嘗試使用前兩個 stores")
        test_stores = stores[:2]

    store1 = test_stores[0]
    store2 = test_stores[1] if len(test_stores) > 1 else stores[1]

    logger.info(f"Store 1: {store1.display_name}")
    logger.info(f"Store 2: {store2.display_name}")

    # 測試 1: 單一 store
    logger.info("\n=== 測試 1: 單一 Store ===")
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-001',  # 使用穩定版本
            contents='請簡單描述這些資料',
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store1.name]
                        )
                    )
                ],
                temperature=0.1
            )
        )
        logger.info(f"✓ 成功")
        logger.info(f"回應: {response.text[:200]}...")
    except Exception as e:
        logger.error(f"✗ 失敗: {e}")

    # 測試 2: 多 store
    logger.info("\n=== 測試 2: 多 Store（關鍵測試）===")
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents='請簡單描述這些資料',
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store1.name, store2.name]
                        )
                    )
                ],
                temperature=0.1
            )
        )
        logger.info(f"✓✓✓ 多 Store 查詢成功！API 支援多 Store 查詢")
        logger.info(f"回應: {response.text[:200]}...")
    except Exception as e:
        logger.error(f"✗✗✗ 多 Store 查詢失敗: {e}")


if __name__ == '__main__':
    test_simple_query()
