"""
測試 Gemini 上傳器

注意: 需要先設定 .env 檔案中的 GEMINI_API_KEY
"""

import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
from src.uploader.gemini_uploader import GeminiUploader
from src.utils.logger import setup_logger

# 載入環境變數
load_dotenv()

# 設定日誌
logger = setup_logger(level="INFO")


def check_api_key():
    """檢查 API Key 是否已設定"""
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key or api_key == 'your_api_key_here':
        logger.error("=" * 60)
        logger.error("❌ 錯誤: 未設定 GEMINI_API_KEY")
        logger.error("=" * 60)
        logger.error("\n請按照以下步驟設定:")
        logger.error("1. 複製 .env.example 為 .env")
        logger.error("   cp .env.example .env")
        logger.error("")
        logger.error("2. 編輯 .env 檔案,填入你的 Gemini API Key")
        logger.error("   GEMINI_API_KEY=your_actual_api_key")
        logger.error("")
        logger.error("3. 如何取得 API Key:")
        logger.error("   訪問 https://aistudio.google.com/apikey")
        logger.error("=" * 60)
        sys.exit(1)

    logger.info(f"✓ API Key 已設定: {api_key[:10]}...")
    return True


def test_basic_upload():
    """測試基本上傳功能"""
    logger.info("=" * 60)
    logger.info("測試 1: 基本上傳功能")
    logger.info("=" * 60)

    try:
        # 初始化上傳器
        uploader = GeminiUploader(store_name='fsc-test-store')

        # 取得或建立 Store
        store_id = uploader.get_or_create_store()
        logger.info(f"Store ID: {store_id}")

        # 測試檔案
        test_file = Path('data/markdown/sample_single.md')

        if not test_file.exists():
            logger.error(f"測試檔案不存在: {test_file}")
            logger.error("請先執行: python scripts/test_markdown_formatter.py")
            return False

        # 上傳單一檔案
        logger.info(f"上傳測試檔案: {test_file}")
        success = uploader.upload_and_add(str(test_file), delay=2.0)

        if success:
            logger.info("✓ 上傳成功!")
        else:
            logger.error("✗ 上傳失敗")
            return False

        # 列出 Store 中的檔案
        files = uploader.list_store_files()
        logger.info(f"\nStore 中的檔案 ({len(files)} 個):")
        for i, file in enumerate(files, 1):
            logger.info(f"  {i}. {file['display_name']}")

        return True

    except Exception as e:
        logger.error(f"測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_upload():
    """測試批次上傳"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 2: 批次上傳 (按來源分檔)")
    logger.info("=" * 60)

    try:
        # 初始化上傳器
        uploader = GeminiUploader(store_name='fsc-test-store')

        # 檢查檔案
        source_dir = Path('data/markdown/by_source')

        if not source_dir.exists():
            logger.error(f"目錄不存在: {source_dir}")
            logger.error("請先執行: python scripts/test_markdown_formatter.py")
            return False

        # 列出檔案
        md_files = list(source_dir.glob('*.md'))
        logger.info(f"找到 {len(md_files)} 個檔案:")
        for f in md_files:
            size_kb = f.stat().st_size / 1024
            logger.info(f"  - {f.name} ({size_kb:.1f} KB)")

        # 確認是否繼續
        logger.info("\n⚠️  這將上傳檔案到 Gemini,可能會消耗 API 配額")
        response = input("是否繼續? (y/N): ")

        if response.lower() != 'y':
            logger.info("已取消")
            return False

        # 批次上傳
        stats = uploader.upload_directory(str(source_dir), pattern='*.md', delay=2.0)

        # 顯示統計
        logger.info("\n統計資訊:")
        logger.info(f"  總檔案數: {stats['total_files']}")
        logger.info(f"  成功上傳: {stats['uploaded_files']}")
        logger.info(f"  失敗數量: {stats['failed_files']}")
        logger.info(f"  總大小: {stats['total_bytes']:,} bytes ({stats['total_bytes']/1024:.1f} KB)")

        return True

    except Exception as e:
        logger.error(f"測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_list_files():
    """測試列出檔案"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 3: 列出 Store 中的檔案")
    logger.info("=" * 60)

    try:
        uploader = GeminiUploader(store_name='fsc-test-store')
        files = uploader.list_store_files()

        if not files:
            logger.info("Store 中沒有檔案")
            return True

        logger.info(f"Store 中共有 {len(files)} 個檔案:\n")
        for i, file in enumerate(files, 1):
            logger.info(f"{i}. {file['display_name']}")
            logger.info(f"   Name: {file['name']}")
            logger.info(f"   Created: {file.get('create_time', 'N/A')}\n")

        return True

    except Exception as e:
        logger.error(f"測試失敗: {e}")
        return False


def cleanup_test_store():
    """清理測試 Store"""
    logger.info("\n" + "=" * 60)
    logger.info("清理測試 Store")
    logger.info("=" * 60)

    response = input("⚠️  是否刪除測試 Store? (y/N): ")

    if response.lower() != 'y':
        logger.info("已取消")
        return

    try:
        uploader = GeminiUploader(store_name='fsc-test-store')
        uploader.get_or_create_store()  # 確保取得 Store ID
        uploader.delete_store()
        logger.info("✓ Store 已刪除")

    except Exception as e:
        logger.error(f"刪除失敗: {e}")


def main():
    """主程式"""
    logger.info("=" * 60)
    logger.info("Gemini 上傳器測試")
    logger.info("=" * 60)

    # 檢查 API Key
    if not check_api_key():
        return

    # 選單
    logger.info("\n請選擇測試項目:")
    logger.info("1. 測試基本上傳 (單一檔案)")
    logger.info("2. 測試批次上傳 (多個檔案)")
    logger.info("3. 列出 Store 中的檔案")
    logger.info("4. 清理測試 Store")
    logger.info("5. 執行全部測試")
    logger.info("0. 退出")

    choice = input("\n請輸入選項 (0-5): ").strip()

    if choice == '1':
        test_basic_upload()
    elif choice == '2':
        test_batch_upload()
    elif choice == '3':
        test_list_files()
    elif choice == '4':
        cleanup_test_store()
    elif choice == '5':
        test_basic_upload()
        test_batch_upload()
        test_list_files()
    elif choice == '0':
        logger.info("退出")
    else:
        logger.error("無效的選項")

    logger.info("\n" + "=" * 60)
    logger.info("測試完成!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
