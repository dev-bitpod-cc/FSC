"""使用生產環境相同的代碼結構測試"""

import os
import sys
from pathlib import Path

# 加入 src 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger
from google import genai
from google.genai import types


def main():
    """主測試函數"""

    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        logger.error("請設定 GEMINI_API_KEY")
        return

    # 初始化客戶端（和生產環境相同）
    client = genai.Client(api_key=api_key)
    model_name = 'gemini-2.0-flash-001'

    # 列出 stores
    stores = list(client.file_search_stores.list())
    logger.info(f"找到 {len(stores)} 個 stores")

    if len(stores) == 0:
        logger.error("沒有 stores")
        return

    # 選擇測試 stores
    test_stores = [s for s in stores if 'test' in s.display_name.lower()]
    if not test_stores:
        logger.warning("沒有測試 stores，使用第一個 store")
        test_stores = [stores[0]]

    store1 = test_stores[0]
    store2 = test_stores[1] if len(test_stores) > 1 else (stores[1] if len(stores) > 1 else None)

    logger.info(f"Store 1: {store1.display_name} ({store1.name})")
    if store2:
        logger.info(f"Store 2: {store2.display_name} ({store2.name})")

    # 測試 1: 單一 store（完全使用生產環境的代碼結構）
    logger.info("\n=== 測試 1: 單一 Store（生產環境結構）===")
    try:
        question = "請描述這些資料"
        system_instruction = "你是一個專業的資料分析助手"

        response = client.models.generate_content(
            model=model_name,
            contents=question,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store1.name]
                        )
                    )
                ],
                temperature=0.1,
                max_output_tokens=2000,
                system_instruction=system_instruction
            )
        )

        answer = response.text if hasattr(response, 'text') else str(response)
        logger.info(f"✓ 單一 Store 查詢成功")
        logger.info(f"回應: {answer[:200]}...")

    except Exception as e:
        logger.error(f"✗ 單一 Store 查詢失敗: {e}")
        import traceback
        traceback.print_exc()

    # 測試 2: 多 store
    if store2:
        logger.info("\n=== 測試 2: 多 Store 查詢 ⭐ ===")
        try:
            question = "請描述這些資料"
            system_instruction = "你是一個專業的資料分析助手"

            response = client.models.generate_content(
                model=model_name,
                contents=question,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[store1.name, store2.name]
                            )
                        )
                    ],
                    temperature=0.1,
                    max_output_tokens=2000,
                    system_instruction=system_instruction
                )
            )

            answer = response.text if hasattr(response, 'text') else str(response)
            logger.info(f"✓✓✓ 多 Store 查詢成功！")
            logger.info(f"回應: {answer[:200]}...")

            logger.info("\n" + "="*60)
            logger.info("結論: ✅ Gemini 支援多 Store 查詢")
            logger.info("="*60)

        except Exception as e:
            logger.error(f"✗✗✗ 多 Store 查詢失敗: {e}")
            logger.warning("\n" + "="*60)
            logger.warning("結論: ❌ Gemini 不支援多 Store 查詢")
            logger.warning("="*60)
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
