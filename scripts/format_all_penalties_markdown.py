"""格式化所有裁罰案件為獨立 Markdown 檔案（含時效性標註）"""

import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processor.penalty_markdown_formatter import BatchPenaltyMarkdownFormatter
from src.storage.jsonl_handler import JSONLHandler
from loguru import logger
import argparse

# 設定日誌
logger.remove()
logger.add(sys.stderr, level="INFO")


def main():
    """主程式"""

    # 解析命令列參數
    parser = argparse.ArgumentParser(description='格式化所有裁罰案件為獨立 Markdown 檔案')
    parser.add_argument('--no-confirm', action='store_true',
                        help='跳過確認提示，直接開始格式化')
    parser.add_argument('--output-dir', type=str,
                        default='data/markdown/penalties',
                        help='輸出目錄（預設: data/markdown/penalties）')
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("格式化所有裁罰案件為獨立 Markdown 檔案")
    logger.info("=" * 80)

    try:
        # 1. 讀取資料
        logger.info("\n[1/4] 讀取裁罰案件資料")

        storage = JSONLHandler()
        items = storage.read_all('penalties')

        if not items:
            logger.error("找不到裁罰案件資料")
            logger.info("請先執行 python scripts/crawl_all_penalties.py --no-confirm")
            return

        logger.info(f"✓ 讀取完成: {len(items)} 筆裁罰案件")

        # 統計資訊
        logger.info("\n資料概覽:")

        # 統計來源單位
        sources = {}
        for item in items:
            src = item.get('metadata', {}).get('source', 'unknown')
            sources[src] = sources.get(src, 0) + 1

        for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(items) * 100
            logger.info(f"  {src}: {count} 筆 ({percentage:.1f}%)")

        # 詢問確認（除非使用 --no-confirm）
        if not args.no_confirm:
            print("\n" + "=" * 80)
            print(f"準備格式化 {len(items)} 筆裁罰案件")
            print(f"輸出目錄: {args.output_dir}")
            print("=" * 80)
            print("\n預計耗時: 2-3 分鐘")
            print("注意事項:")
            print("  - 將生成 495 個獨立 Markdown 檔案")
            print("  - 包含時效性標註（版本追蹤）")
            print("  - 使用簡化檔名格式（ID_單位簡稱.md）")
            print("\n")

            response = input("確定要開始嗎？(yes/no): ").strip().lower()

            if response != 'yes':
                print("已取消")
                return
        else:
            logger.info("\n開始格式化（跳過確認）")

        # 2. 初始化格式化器
        logger.info("\n[2/4] 初始化 Markdown 格式化器")
        formatter = BatchPenaltyMarkdownFormatter()
        logger.info("✓ 格式化器初始化完成")

        # 3. 格式化為獨立檔案
        logger.info(f"\n[3/4] 格式化為獨立 Markdown 檔案")
        logger.info(f"輸出目錄: {args.output_dir}")

        result = formatter.format_individual_files(items, args.output_dir)

        logger.info(f"\n✓ 格式化完成")
        logger.info(f"  總案件數: {result['total_items']}")
        logger.info(f"  成功建立: {result['created_files']} 個檔案")
        logger.info(f"  失敗: {result['total_items'] - result['created_files']} 個檔案")

        # 4. 驗證結果
        logger.info("\n[4/4] 驗證結果")

        output_path = Path(args.output_dir)
        all_files = sorted(output_path.glob('*.md'))

        logger.info(f"✓ 共建立 {len(all_files)} 個 Markdown 檔案")

        # 計算總大小
        total_size = sum(f.stat().st_size for f in all_files)
        logger.info(f"✓ 總大小: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")

        # 顯示檔名範例
        logger.info("\n檔名範例（前 5 個）:")
        for filepath in all_files[:5]:
            logger.info(f"  - {filepath.name}")

        # 顯示第一個檔案預覽
        if all_files:
            logger.info("\n" + "=" * 80)
            logger.info(f"第一個檔案預覽 ({all_files[0].name}):")
            logger.info("=" * 80)

            with open(all_files[0], 'r', encoding='utf-8') as f:
                content = f.read()
                preview = content[:500]
                print("\n" + preview)
                logger.info(f"\n... (完整內容共 {len(content)} 字元)")

        logger.info("\n" + "=" * 80)
        logger.info("✅ 格式化完成！")
        logger.info("=" * 80)
        logger.info(f"\n所有檔案已儲存至: {args.output_dir}/")
        logger.info("\n下一步:")
        logger.info("  1. 檢查 Markdown 檔案格式")
        logger.info("  2. 上傳到 Gemini File Search Store")
        logger.info("     python scripts/upload_penalties_to_gemini.py")

    except Exception as e:
        logger.error(f"格式化過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
