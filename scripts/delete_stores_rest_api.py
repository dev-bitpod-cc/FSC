#!/usr/bin/env python3
"""
使用 REST API 強制刪除 Gemini File Search Stores
"""

import os
import sys
import requests
from pathlib import Path

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 載入環境變數
from dotenv import load_dotenv
load_dotenv()

def delete_store_via_rest_api(store_id, api_key):
    """使用 REST API 刪除 Store"""

    # Gemini API endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/{store_id}"

    headers = {
        "x-goog-api-key": api_key
    }

    # 嘗試強制刪除 (加上 force 參數)
    params = {
        "force": "true"
    }

    response = requests.delete(url, headers=headers, params=params)

    return response

def main():
    """主函式"""

    # 設定 API Key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ 錯誤: 找不到 GEMINI_API_KEY")
        return

    # 要刪除的 Store IDs (Store #7-13)
    stores_to_delete = [
        ("Store #7", "fileSearchStores/fscteststore-m87rpvke09bn"),
        ("Store #8", "fileSearchStores/fscannouncements150-1s4syh83mg6k"),
        ("Store #9", "fileSearchStores/fscannouncements-z0ri8kcrrwfe"),
        ("Store #10", "fileSearchStores/fsctestupload-4slqf03z2c5x"),
        ("Store #11", "fileSearchStores/fscannouncementsall-86u9vp2mw8vc"),
        ("Store #12", "fileSearchStores/fsctestannouncements-60r3k474fmf0"),
        ("Store #13", "fileSearchStores/fsctestpenalties-5o5dqvd9a7ck"),
    ]

    print("🗑️  使用 REST API 強制刪除 Stores")
    print("=" * 80)
    for name, store_id in stores_to_delete:
        print(f"   {name}: {store_id}")
    print("=" * 80)

    input("\n按 Enter 確認刪除，或 Ctrl+C 取消...")

    deleted_count = 0
    failed_stores = []

    for name, store_id in stores_to_delete:
        print(f"\n🔄 刪除 {name}...")

        try:
            response = delete_store_via_rest_api(store_id, api_key)

            if response.status_code == 200:
                print(f"   ✅ 刪除成功")
                deleted_count += 1
            else:
                print(f"   ❌ 刪除失敗: HTTP {response.status_code}")
                print(f"   回應: {response.text}")
                failed_stores.append((name, store_id, response.text))

        except Exception as e:
            print(f"   ❌ 錯誤: {e}")
            failed_stores.append((name, store_id, str(e)))

    print("\n" + "=" * 80)
    print(f"\n📊 刪除完成:")
    print(f"   成功刪除: {deleted_count}/{len(stores_to_delete)} 個 Stores")

    if failed_stores:
        print(f"\n❌ 失敗的 Stores:")
        for name, store_id, error in failed_stores:
            print(f"   {name}: {store_id}")
            print(f"      錯誤: {error[:200]}")
    else:
        print(f"\n✅ 所有 Stores 都已成功刪除！")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        sys.exit(1)
