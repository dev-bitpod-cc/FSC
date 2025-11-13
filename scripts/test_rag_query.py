#!/usr/bin/env python3
"""測試 RAG 查詢和參考文件顯示"""

import sys
from pathlib import Path

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import logger
from dotenv import load_dotenv
import os

try:
    from google import genai
    from google.genai import types
except ImportError:
    logger.error("請先安裝 google-genai: pip install google-genai")
    sys.exit(1)


def main():
    """主程式"""
    # 載入環境變數
    load_dotenv()

    # 檢查 API Key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("未設定 GEMINI_API_KEY,請在 .env 檔案中設定")
        return

    logger.info("=" * 60)
    logger.info("測試 Gemini File Search RAG 查詢")
    logger.info("=" * 60)

    # 初始化 Gemini 客戶端
    client = genai.Client(api_key=api_key)

    # 取得 File Search Store
    store_name = 'fsc-announcements'
    logger.info(f"\n尋找 Store: {store_name}")

    stores = list(client.file_search_stores.list())
    store_id = None

    for store in stores:
        if store.display_name == store_name:
            store_id = store.name
            logger.info(f"找到 Store: {store_id}")
            break

    if not store_id:
        logger.error(f"找不到 Store: {store_name}")
        return

    # 列出 Store 中的檔案
    logger.info(f"\n列出 Store 中的檔案:")
    try:
        store_info = client.file_search_stores.get(name=store_id)

        if hasattr(store_info, 'files') and store_info.files:
            logger.info(f"Store 中共有 {len(store_info.files)} 個檔案:")
            for i, file_ref in enumerate(store_info.files[:5], 1):
                logger.info(f"  {i}. {file_ref}")
        else:
            logger.warning("Store 中沒有檔案")
    except Exception as e:
        logger.error(f"列出檔案失敗: {e}")

    # 測試查詢
    test_queries = [
        "銀行局最近有什麼重要公告?",
        "關於保險的規定",
        "證券相關的法規"
    ]

    for query in test_queries:
        logger.info("\n" + "=" * 60)
        logger.info(f"查詢: {query}")
        logger.info("=" * 60)

        try:
            # 執行查詢 (使用 file_search 參數,依照官方文檔格式)
            response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[{'file_search': {'file_search_store_names': [store_id]}}],
                    temperature=0.0,
                )
            )

            # 顯示回答
            logger.info("\n回答:")
            logger.info(response.text)

            # 顯示參考來源 (grounding metadata)
            logger.info("\n參考來源:")
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]

                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    metadata = candidate.grounding_metadata

                    if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                        logger.info(f"找到 {len(metadata.grounding_chunks)} 個參考文件:")

                        for i, chunk in enumerate(metadata.grounding_chunks, 1):
                            logger.info(f"\n參考文件 #{i}:")

                            # 檢查 chunk 的屬性
                            if hasattr(chunk, 'web'):
                                logger.info(f"  類型: 網頁")
                                logger.info(f"  URI: {chunk.web.uri}")
                                logger.info(f"  標題: {chunk.web.title}")

                            elif hasattr(chunk, 'retrieved_context'):
                                logger.info(f"  類型: File Search")
                                context = chunk.retrieved_context

                                if hasattr(context, 'uri'):
                                    logger.info(f"  URI: {context.uri}")
                                if hasattr(context, 'title'):
                                    logger.info(f"  標題: {context.title}")
                                if hasattr(context, 'text'):
                                    logger.info(f"  內容預覽: {context.text[:200]}...")

                            # 顯示所有可用屬性
                            logger.info(f"  可用屬性: {dir(chunk)}")
                            logger.info(f"  Chunk 內容: {chunk}")
                    else:
                        logger.info("沒有 grounding_chunks")
                else:
                    logger.info("沒有 grounding_metadata")
            else:
                logger.info("沒有 candidates")

            # 顯示完整 response 結構
            logger.info("\n完整 Response 結構:")
            logger.info(f"Response 屬性: {dir(response)}")

        except Exception as e:
            logger.error(f"查詢失敗: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
