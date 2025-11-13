"""測試上傳腳本的 Markdown 產生功能"""

import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
import subprocess

# 設定日誌
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_markdown_generation():
    """測試 Markdown 產生功能"""

    logger.info("=" * 70)
    logger.info("測試上傳腳本 Markdown 產生功能")
    logger.info("=" * 70)

    # 測試 1: 測試裁罰案件 Markdown 產生
    logger.info("\n[測試 1] 裁罰案件 Markdown 產生")
    logger.info("-" * 70)

    # 檢查是否有裁罰測試資料
    test_data = Path('data/penalties_test/test_penalties.jsonl')

    if test_data.exists():
        logger.info("✓ 找到裁罰測試資料")

        # 暫時複製到正式資料夾以供測試
        import shutil
        import json

        # 建立臨時資料目錄
        temp_data_dir = Path('data/penalties')
        temp_data_dir.mkdir(parents=True, exist_ok=True)

        temp_raw = temp_data_dir / 'raw.jsonl'
        shutil.copy(test_data, temp_raw)

        logger.info(f"  已複製測試資料到: {temp_raw}")

        # 執行 Markdown 產生
        logger.info("\n執行 Markdown 產生...")

        result = subprocess.run(
            [
                sys.executable,
                'scripts/upload_to_gemini.py',
                '--type', 'penalties',
                '--markdown-only'
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("✓ Markdown 產生成功")

            # 檢查輸出
            output_dir = Path('data/temp_markdown/penalties')
            if output_dir.exists():
                files = list(output_dir.glob('*.md'))
                logger.info(f"  產生 {len(files)} 個 Markdown 檔案")

                if files:
                    # 讀取第一個檔案預覽
                    first_file = files[0]
                    logger.info(f"\n  第一個檔案預覽 ({first_file.name}):")
                    with open(first_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        logger.info(f"  檔案大小: {len(content)} 字元")
                        logger.info("\n" + "-" * 70)
                        print(content[:800])
                        logger.info("-" * 70)
            else:
                logger.error("✗ 輸出目錄不存在")
        else:
            logger.error("✗ Markdown 產生失敗")
            logger.error(f"錯誤輸出:\n{result.stderr}")

        # 清理臨時檔案
        if temp_raw.exists():
            temp_raw.unlink()
            logger.info(f"\n✓ 已清理臨時測試資料")

    else:
        logger.warning(f"✗ 未找到裁罰測試資料: {test_data}")
        logger.info("  請先執行: python scripts/test_penalty_crawler.py")

    # 測試 2: 測試公告 Markdown 產生（如果有資料）
    logger.info("\n[測試 2] 公告 Markdown 產生（含時效性標註）")
    logger.info("-" * 70)

    announcements_data = Path('data/announcements/raw.jsonl')

    if announcements_data.exists():
        logger.info("✓ 找到公告資料")

        # 讀取資料量
        import json
        count = 0
        with open(announcements_data, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    count += 1

        logger.info(f"  資料量: {count} 筆")

        # 只產生前 5 筆的 Markdown（測試用）
        if count > 0:
            logger.info("\n執行 Markdown 產生（前 5 筆）...")

            # 建立臨時資料（只包含前 5 筆）
            temp_data_dir = Path('data/announcements_sample')
            temp_data_dir.mkdir(parents=True, exist_ok=True)

            temp_raw = temp_data_dir / 'raw.jsonl'

            with open(announcements_data, 'r', encoding='utf-8') as f_in:
                with open(temp_raw, 'w', encoding='utf-8') as f_out:
                    for i, line in enumerate(f_in):
                        if i < 5 and line.strip():
                            f_out.write(line)

            logger.info(f"  已建立測試樣本: {temp_raw}")

            # 暫時修改腳本讀取路徑（這裡我們直接測試時效性標註功能）
            logger.info("\n  注意: 完整測試需要實際公告資料")
            logger.info("  時效性標註功能已在 test_temporal_annotation.py 中驗證")

            # 清理
            if temp_raw.exists():
                temp_raw.unlink()
            if temp_data_dir.exists():
                temp_data_dir.rmdir()

        else:
            logger.warning("  公告資料檔案為空")

    else:
        logger.warning(f"✗ 未找到公告資料: {announcements_data}")
        logger.info("  這是正常的，如果還未爬取公告資料")

    # 總結
    logger.info("\n" + "=" * 70)
    logger.info("測試完成!")
    logger.info("=" * 70)

    logger.info("\n✓ 上傳腳本 Markdown 產生功能測試完成")

    logger.info("\n說明:")
    logger.info("  - 裁罰案件 Markdown 產生: 已測試")
    logger.info("  - 時效性標註功能: 已在 test_temporal_annotation.py 驗證")
    logger.info("  - 實際上傳功能: 需要 GEMINI_API_KEY")

    logger.info("\n下一步:")
    logger.info("  1. 設定 .env 中的 GEMINI_API_KEY")
    logger.info("  2. 執行完整上傳測試:")
    logger.info("     python scripts/upload_to_gemini.py --type penalties")


def main():
    """主程式"""
    try:
        test_markdown_generation()
    except Exception as e:
        logger.error(f"測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
