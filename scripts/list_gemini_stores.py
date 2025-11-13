#!/usr/bin/env python3
"""
列出所有 Gemini File Search Stores
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

def list_all_stores():
    """列出所有 Gemini File Search Stores (Corpora)"""

    # 設定 API Key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ 錯誤: 找不到 GEMINI_API_KEY")
        return

    client = genai.Client(api_key=api_key)

    print("🔍 正在查詢所有 Gemini 資源...\n")
    print("=" * 80)

    try:
        # 1. 列出所有 File Search Stores (新版 API)
        print("\n📦 File Search Stores (永久儲存):")
        print("-" * 80)
        stores = list(client.file_search_stores.list())

        store_count = 0
        for store in stores:
            store_count += 1

            # 取得 store 的詳細資訊
            print(f"\n📦 Store #{store_count}")
            print(f"   ID: {store.name}")

            if hasattr(store, 'display_name'):
                print(f"   顯示名稱: {store.display_name}")

            # 嘗試獲取文件數量
            try:
                documents = list(client.file_search_stores.documents.list(file_search_store=store.name))
                print(f"   文件數量: {len(documents)}")
            except Exception as doc_err:
                print(f"   文件數量: (無法取得)")

            # 建立時間
            if hasattr(store, 'create_time'):
                print(f"   建立時間: {store.create_time}")

            # 更新時間
            if hasattr(store, 'update_time'):
                print(f"   更新時間: {store.update_time}")

            print("-" * 80)

        if store_count == 0:
            print("\n⚠️  沒有找到任何 File Search Store")
        else:
            print(f"\n✅ File Search Stores 總數: {store_count}")

        # 2. 列出 Files API 上傳的文件 (48小時有效期)
        print("\n" + "=" * 80)
        print("\n📄 Files API (臨時文件，48小時有效期):")
        print("-" * 80)

        try:
            files = list(client.files.list())
            file_count = 0

            for file in files:
                file_count += 1
                print(f"\n📄 File #{file_count}")
                print(f"   名稱: {file.name}")

                if hasattr(file, 'display_name'):
                    print(f"   顯示名稱: {file.display_name}")

                if hasattr(file, 'state'):
                    print(f"   狀態: {file.state}")

                if hasattr(file, 'create_time'):
                    print(f"   建立時間: {file.create_time}")

                if hasattr(file, 'expiration_time'):
                    print(f"   過期時間: {file.expiration_time}")

                print("-" * 80)

            if file_count == 0:
                print("\n⚠️  沒有找到任何臨時文件")
            else:
                print(f"\n✅ Files API 文件總數: {file_count}")

        except Exception as e:
            print(f"\n⚠️  無法列出 Files API: {e}")

        print("\n" + "=" * 80)
        print(f"\n📊 總結:")
        print(f"   File Search Stores: {store_count}")
        print(f"   Files API 文件: {file_count if 'file_count' in locals() else 0}")

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_all_stores()
