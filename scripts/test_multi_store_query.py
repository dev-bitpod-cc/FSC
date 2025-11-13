"""測試多 Store 查詢功能

驗證 Gemini File Search API 是否支援在單一查詢中使用多個 stores
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

try:
    from google import genai
    from google.genai import types
except ImportError:
    logger.error("請先安裝: pip install google-genai")
    exit(1)


def create_test_stores():
    """建立兩個測試 stores"""

    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        logger.error("請在 .env 中設定 GEMINI_API_KEY")
        return None, None

    client = genai.Client(api_key=api_key)

    # 建立測試 stores
    test_stores = []
    store_names = ['fsc-test-announcements', 'fsc-test-penalties']

    for store_name in store_names:
        try:
            # 檢查是否已存在
            stores = list(client.file_search_stores.list())
            existing = [s for s in stores if s.display_name == store_name]

            if existing:
                logger.info(f"測試 Store 已存在: {store_name}")
                test_stores.append(existing[0])
            else:
                logger.info(f"建立測試 Store: {store_name}")
                store = client.file_search_stores.create(
                    config=types.CreateFileSearchStoreConfig(
                        display_name=store_name
                    )
                )
                test_stores.append(store)
                logger.info(f"✓ Store 建立成功: {store.name}")
        except Exception as e:
            logger.error(f"建立 Store 失敗: {e}")
            return None, None

    return test_stores[0], test_stores[1]


def upload_test_files(client, store_id, store_type):
    """上傳測試檔案到 store"""

    # 建立測試檔案
    test_content = f"""# 測試{store_type}

這是一個測試{store_type}，用於驗證多 Store 查詢功能。

## 內容
- 測試項目 1
- 測試項目 2
- 測試項目 3

資料類型: {store_type}
"""

    # 寫入暫存檔案
    temp_dir = Path('data/temp_test')
    temp_dir.mkdir(parents=True, exist_ok=True)

    test_file = temp_dir / f'test_{store_type}.md'
    test_file.write_text(test_content, encoding='utf-8')

    try:
        # 上傳檔案
        logger.info(f"上傳測試檔案: {test_file.name}")
        with open(test_file, 'rb') as f:
            file_obj = client.files.upload(
                file=f,
                config=types.UploadFileConfig(
                    display_name=test_file.name,
                    mime_type='text/markdown'
                )
            )

        logger.info(f"✓ 檔案上傳成功: {file_obj.name}")

        # 加入 Store
        logger.info(f"將檔案加入 Store...")
        client.file_search_stores.import_file(
            file_search_store_name=store_id,
            file_name=file_obj.name
        )
        logger.info(f"✓ 檔案已加入 Store")

        return True
    except Exception as e:
        logger.error(f"上傳失敗: {e}")
        return False


def test_multi_store_query():
    """測試多 Store 查詢"""

    # 載入環境變數
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        logger.error("請在 .env 中設定 GEMINI_API_KEY")
        return

    # 初始化客戶端
    client = genai.Client(api_key=api_key)

    # 建立測試 stores
    logger.info("=== 步驟 1: 建立測試 Stores ===")
    store_ann, store_pen = create_test_stores()

    if not store_ann or not store_pen:
        logger.error("建立測試 stores 失敗")
        return

    # 上傳測試檔案
    logger.info("\n=== 步驟 2: 上傳測試檔案 ===")
    upload_test_files(client, store_ann.name, '公告')
    upload_test_files(client, store_pen.name, '裁罰')

    # 等待檔案處理
    import time
    logger.info("\n等待 5 秒讓檔案處理完成...")
    time.sleep(5)

    # 測試案例 1: 單一 Store 查詢
    logger.info("\n=== 測試 1: 單一 Store 查詢（公告）===")
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents='這是什麼類型的資料？',
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store_ann.name]
                        )
                    )
                ]
            )
        )
        logger.info(f"✓ 單一 Store 查詢成功")
        logger.info(f"回應: {response.text}")
    except Exception as e:
        logger.error(f"✗ 單一 Store 查詢失敗: {e}")

    # 測試案例 2: 單一 Store 查詢（裁罰）
    logger.info("\n=== 測試 2: 單一 Store 查詢（裁罰）===")
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents='這是什麼類型的資料？',
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store_pen.name]
                        )
                    )
                ]
            )
        )
        logger.info(f"✓ 單一 Store 查詢成功")
        logger.info(f"回應: {response.text}")
    except Exception as e:
        logger.error(f"✗ 單一 Store 查詢失敗: {e}")

    # 測試案例 3: 多 Store 查詢 ⭐ 關鍵測試
    logger.info("\n=== 測試 3: 多 Store 查詢（公告 + 裁罰）⭐ ===")
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents='列出所有資料類型',
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store_ann.name, store_pen.name]
                        )
                    )
                ]
            )
        )
        logger.info(f"✓✓✓ 多 Store 查詢成功！API 支援多 Store 查詢 ✓✓✓")
        logger.info(f"回應: {response.text}")

        logger.info("\n" + "="*60)
        logger.info("結論: ✅ Gemini File Search API 支援多 Store 查詢")
        logger.info("可以在查詢時指定多個 fileSearchStoreNames")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"✗✗✗ 多 Store 查詢失敗: {e}")
        logger.warning("\n" + "="*60)
        logger.warning("結論: ❌ API 可能不支援多 Store 查詢")
        logger.warning("建議使用方案 2: 單一 Store + Metadata 過濾")
        logger.warning("="*60)

    # 清理提示
    logger.info("\n" + "="*60)
    logger.info("測試完成！")
    logger.info("如需清理測試 stores，請執行:")
    logger.info("python scripts/cleanup_test_stores.py")
    logger.info("="*60)


if __name__ == '__main__':
    logger.info("開始測試多 Store 查詢功能")
    test_multi_store_query()
