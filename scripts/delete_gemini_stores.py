#!/usr/bin/env python3
"""
刪除指定的 Gemini File Search Stores
需要先刪除 Store 中的所有文件，然後才能刪除 Store
"""

import os
import sys
from pathlib import Path

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 載入環境變數
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

def delete_stores():
    """刪除指定的 File Search Stores"""

    # 設定 API Key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ 錯誤: 找不到 GEMINI_API_KEY")
        return

    client = genai.Client(api_key=api_key)

    # 要刪除的 Store IDs (Store #7-13)
    stores_to_delete = [
        "fileSearchStores/fscteststore-m87rpvke09bn",              # #7
        "fileSearchStores/fscannouncements150-1s4syh83mg6k",       # #8
        "fileSearchStores/fscannouncements-z0ri8kcrrwfe",          # #9
        "fileSearchStores/fsctestupload-4slqf03z2c5x",             # #10
        "fileSearchStores/fscannouncementsall-86u9vp2mw8vc",       # #11
        "fileSearchStores/fsctestannouncements-60r3k474fmf0",      # #12
        "fileSearchStores/fsctestpenalties-5o5dqvd9a7ck",          # #13
    ]

    print("🗑️  準備刪除以下 Stores:")
    print("=" * 80)
    for i, store_id in enumerate(stores_to_delete, 7):
        print(f"   Store #{i}: {store_id}")
    print("=" * 80)

    input("\n按 Enter 確認刪除，或 Ctrl+C 取消...")

    deleted_count = 0
    failed_stores = []

    for i, store_id in enumerate(stores_to_delete, 7):
        print(f"\n🔄 處理 Store #{i}: {store_id}")

        try:
            # 1. 列出並刪除 Store 中的所有文件
            print(f"   📄 正在列出文件...")
            try:
                # 嘗試列出文件 (使用 parent 參數)
                documents = list(client.file_search_stores.documents.list(parent=store_id))
                doc_count = len(documents)
                print(f"   找到 {doc_count} 個文件")

                if doc_count > 0:
                    print(f"   🗑️  正在刪除文件...")
                    deleted_docs = 0
                    for doc in documents:
                        try:
                            # 先刪除 Document 內部的所有 Chunks/Parts
                            try:
                                chunks = list(client.file_search_stores.documents.chunks.list(parent=doc.name))
                                for chunk in chunks:
                                    try:
                                        client.file_search_stores.documents.chunks.delete(name=chunk.name)
                                    except Exception as chunk_err:
                                        # 忽略 chunk 刪除錯誤，繼續嘗試
                                        pass
                            except Exception as chunks_err:
                                # 如果沒有 chunks API，跳過
                                pass

                            # 刪除 Document
                            client.file_search_stores.documents.delete(name=doc.name)
                            deleted_docs += 1
                            if deleted_docs % 10 == 0:
                                print(f"      已刪除 {deleted_docs}/{doc_count} 個文件")
                        except Exception as e:
                            print(f"      ⚠️  刪除文件失敗: {doc.name}: {e}")

                    print(f"   ✅ 成功刪除 {deleted_docs}/{doc_count} 個文件")
            except Exception as e:
                print(f"   ⚠️  列出文件時出錯: {e}")

            # 2. 刪除 Store
            print(f"   🗑️  正在刪除 Store...")
            client.file_search_stores.delete(name=store_id)
            print(f"   ✅ Store 刪除成功")
            deleted_count += 1

        except Exception as e:
            print(f"   ❌ 刪除失敗: {e}")
            failed_stores.append((i, store_id, str(e)))
            continue

    print("\n" + "=" * 80)
    print(f"\n📊 刪除完成:")
    print(f"   成功刪除: {deleted_count}/{len(stores_to_delete)} 個 Stores")

    if failed_stores:
        print(f"\n❌ 失敗的 Stores:")
        for num, store_id, error in failed_stores:
            print(f"   Store #{num}: {store_id}")
            print(f"      錯誤: {error}")
    else:
        print(f"\n✅ 所有 Stores 都已成功刪除！")

if __name__ == "__main__":
    try:
        delete_stores()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        sys.exit(1)
