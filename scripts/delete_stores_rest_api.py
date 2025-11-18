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
    import argparse

    parser = argparse.ArgumentParser(description='使用 REST API 強制刪除 Gemini Stores')
    parser.add_argument('--yes', '-y', action='store_true', help='跳過確認')
    args = parser.parse_args()

    # 設定 API Key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ 錯誤: 找不到 GEMINI_API_KEY")
        return

    # 要刪除的 Store IDs (保留 Deploy 專案使用的)
    # 保留: fileSearchStores/fscpenalties-tu709bvr1qti (FSC-Penalties-Deploy)
    # 保留: fileSearchStores/fscpenaltycases1762854180-9kooa996ag5a (Sanction)

    stores_to_delete = [
        ("Store #1", "fileSearchStores/fscpenaltycases1762852550-df677oxvk9ke"),
        ("Store #2", "fileSearchStores/fscpenaltycases1762853298-pp7xw875g3te"),
        ("Store #3", "fileSearchStores/teststore-n2haofckqioh"),
        ("Store #4", "fileSearchStores/fscpenaltycases1762853753-f1kefbyo3sqo"),
        ("Store #5", "fileSearchStores/fscpenaltycases1762854027-y7a8l1qc6elv"),
        ("Store #8", "fileSearchStores/fscpenaltiesoptimizedtest-ixrg0l5s4967"),
        ("Store #9", "fileSearchStores/fscpenaltiesoptimized-amgl070m85d5"),
        ("Store #10", "fileSearchStores/fscpenaltiesfsc490-eg8q35dtsquz"),
    ]

    print("🗑️  使用 REST API 強制刪除 Stores (force=true)")
    print("=" * 80)
    for name, store_id in stores_to_delete:
        print(f"   {name}: {store_id}")
    print("=" * 80)

    if not args.yes:
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
