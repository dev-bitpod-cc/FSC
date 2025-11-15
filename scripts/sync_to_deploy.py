"""
同步映射檔到部署專案

將生成的 file_mapping.json 複製到 FSC-Penalties-Deploy 專案
"""

import shutil
import json
from pathlib import Path
from loguru import logger


def sync_file_mapping():
    """同步映射檔到部署專案"""

    # 路徑設定
    source_file = Path.home() / 'Projects' / 'FSC' / 'data' / 'penalties' / 'file_mapping.json'
    deploy_dir = Path.home() / 'Projects' / 'FSC-Penalties-Deploy'
    target_file = deploy_dir / 'file_mapping.json'

    logger.info("=" * 80)
    logger.info("同步映射檔到部署專案")
    logger.info("=" * 80)

    # 檢查來源檔案
    if not source_file.exists():
        logger.error(f"❌ 映射檔不存在: {source_file}")
        logger.info("請先執行: python scripts/generate_file_mapping.py")
        return False

    # 檢查部署專案目錄
    if not deploy_dir.exists():
        logger.error(f"❌ 部署專案目錄不存在: {deploy_dir}")
        return False

    # 讀取並驗證映射檔
    logger.info(f"\n[1/3] 驗證映射檔")
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        logger.info(f"✓ 映射檔包含 {len(mapping)} 筆資料")
    except Exception as e:
        logger.error(f"❌ 映射檔格式錯誤: {e}")
        return False

    # 複製檔案
    logger.info(f"\n[2/3] 複製檔案")
    logger.info(f"來源: {source_file}")
    logger.info(f"目標: {target_file}")

    try:
        shutil.copy2(source_file, target_file)
        logger.info("✓ 檔案複製成功")
    except Exception as e:
        logger.error(f"❌ 複製失敗: {e}")
        return False

    # 驗證複製結果
    logger.info(f"\n[3/3] 驗證複製結果")
    if target_file.exists():
        file_size = target_file.stat().st_size
        logger.info(f"✓ 目標檔案已存在")
        logger.info(f"  檔案大小: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    else:
        logger.error(f"❌ 目標檔案不存在")
        return False

    # 顯示統計資訊
    logger.info("\n" + "=" * 80)
    logger.info("統計資訊")
    logger.info("=" * 80)

    # 統計欄位完整度
    stats = {
        'total': len(mapping),
        'with_original_url': 0,
        'with_laws': 0,
        'with_content': 0
    }

    for item in mapping.values():
        if item.get('original_url'):
            stats['with_original_url'] += 1
        if item.get('applicable_laws'):
            stats['with_laws'] += 1
        if item.get('original_content', {}).get('text'):
            stats['with_content'] += 1

    logger.info(f"\n總筆數: {stats['total']}")
    logger.info(f"包含原始 URL: {stats['with_original_url']} ({stats['with_original_url']/stats['total']*100:.1f}%)")
    logger.info(f"包含法條: {stats['with_laws']} ({stats['with_laws']/stats['total']*100:.1f}%)")
    logger.info(f"包含原始內容: {stats['with_content']} ({stats['with_content']/stats['total']*100:.1f}%)")

    logger.info("\n" + "=" * 80)
    logger.info("✅ 同步完成！")
    logger.info("=" * 80)
    logger.info("\n下一步:")
    logger.info("  1. 前往部署專案: cd ~/Projects/FSC-Penalties-Deploy")
    logger.info("  2. 檢查映射檔: ls -lh file_mapping.json")
    logger.info("  3. 提交更新: git add file_mapping.json && git commit -m 'Update file mapping'")
    logger.info("  4. 推送到 GitHub: git push (CI/CD 會自動部署)")

    return True


def main():
    """主函數"""
    try:
        success = sync_file_mapping()
        if success:
            logger.info("\n✅ 同步成功")
        else:
            logger.error("\n❌ 同步失敗")
            exit(1)

    except Exception as e:
        logger.error(f"\n❌ 錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)


if __name__ == '__main__':
    main()
