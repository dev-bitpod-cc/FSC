"""使用官方文檔的正確語法測試"""

import os
from dotenv import load_dotenv
from loguru import logger
from google import genai
from google.genai import types


def main():
    """測試正確語法"""

    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        logger.error("請設定 GEMINI_API_KEY")
        return

    client = genai.Client(api_key=api_key)

    # 列出 stores
    stores = list(client.file_search_stores.list())
    logger.info(f"找到 {len(stores)} 個 stores")

    if len(stores) == 0:
        logger.error("沒有 stores")
        return

    # 選擇測試 stores
    test_stores = [s for s in stores if 'test' in s.display_name.lower()]
    if not test_stores:
        test_stores = [stores[0]]

    store1 = test_stores[0]
    store2 = test_stores[1] if len(test_stores) > 1 else (stores[1] if len(stores) > 1 else None)

    logger.info(f"Store 1: {store1.display_name}")
    if store2:
        logger.info(f"Store 2: {store2.display_name}")

    # 測試 1: 使用 Tool 但不包metadata filter（單一 Store）
    logger.info("\n=== 測試 1: Tool 語法無 metadata（單一 Store）===")
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents='請描述這些資料',
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        fileSearch=types.FileSearch(
                            file_search_store_names=[store1.name]
                        )
                    )
                ]
            )
        )

        logger.info(f"✓ 成功！")
        logger.info(f"回應: {response.text[:200]}...")

    except Exception as e:
        logger.error(f"✗ 失敗: {e}")
        return

    # 測試 2: 多 store ⭐ 關鍵測試
    if store2:
        logger.info("\n=== 測試 2: Tool 語法無 metadata（多 Store）⭐ ===")
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash-001',
                contents='請描述這些資料',
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            fileSearch=types.FileSearch(
                                file_search_store_names=[store1.name, store2.name]
                            )
                        )
                    ]
                )
            )

            logger.info(f"✓✓✓ 多 Store 查詢成功！")
            logger.info(f"回應: {response.text[:200]}...")

            logger.info("\n" + "="*60)
            logger.info("✅ 結論: Gemini File Search API 支援多 Store 查詢")
            logger.info("查詢介面可以實作「只查公告」、「只查裁罰」、「兩者都查」")
            logger.info("="*60)

        except Exception as e:
            logger.error(f"✗✗✗ 多 Store 查詢失敗: {e}")
            logger.warning("\n" + "="*60)
            logger.warning("❌ 結論: Gemini 不支援多 Store 查詢")
            logger.warning("建議使用方案 2: 單一 Store + Metadata 過濾")
            logger.warning("="*60)


if __name__ == '__main__':
    main()
