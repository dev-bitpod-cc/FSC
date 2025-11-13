"""測試公告時效性標註功能"""

import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processor.markdown_formatter import MarkdownFormatter
from src.processor.version_tracker import VersionTracker
from loguru import logger

# 設定日誌
logger.remove()
logger.add(sys.stderr, level="INFO")


def create_test_data():
    """建立測試資料"""

    # 模擬同一法規的多個版本
    items = [
        # 法規 A - 3 個版本
        {
            'id': 'fsc_ann_20250101_0001',
            'data_type': 'announcement',
            'date': '2025-01-01',
            'title': '修正「保險業內部控制及稽核制度實施辦法」',
            'source_raw': '保險局',
            'detail_url': 'https://www.fsc.gov.tw/...',
            'content': {
                'text': '為強化保險業內部控制，修正相關條文...',
                'html': '...'
            },
            'metadata': {
                'announcement_number': '金管保壽字第1140000001號',
                'category': 'amendment',
                'source': 'insurance_bureau'
            }
        },
        {
            'id': 'fsc_ann_20231215_0001',
            'data_type': 'announcement',
            'date': '2023-12-15',
            'title': '修正「保險業內部控制及稽核制度實施辦法」',
            'source_raw': '保險局',
            'detail_url': 'https://www.fsc.gov.tw/...',
            'content': {
                'text': '為完善保險業內部控制機制，修正部分條文...',
                'html': '...'
            },
            'metadata': {
                'announcement_number': '金管保壽字第1120000001號',
                'category': 'amendment',
                'source': 'insurance_bureau'
            }
        },
        {
            'id': 'fsc_ann_20220801_0001',
            'data_type': 'announcement',
            'date': '2022-08-01',
            'title': '修正「保險業內部控制及稽核制度實施辦法」',
            'source_raw': '保險局',
            'detail_url': 'https://www.fsc.gov.tw/...',
            'content': {
                'text': '為提升保險業風險管理能力，修正相關規定...',
                'html': '...'
            },
            'metadata': {
                'announcement_number': '金管保壽字第1110000001號',
                'category': 'amendment',
                'source': 'insurance_bureau'
            }
        },

        # 法規 B - 2 個版本
        {
            'id': 'fsc_ann_20250315_0002',
            'data_type': 'announcement',
            'date': '2025-03-15',
            'title': '修正「公開發行公司年報應行記載事項準則」',
            'source_raw': '證券期貨局',
            'detail_url': 'https://www.fsc.gov.tw/...',
            'content': {
                'text': '為強化公司治理資訊揭露，修正年報記載事項...',
                'html': '...'
            },
            'metadata': {
                'announcement_number': '金管證發字第1140000002號',
                'category': 'amendment',
                'source': 'securities_bureau'
            }
        },
        {
            'id': 'fsc_ann_20230520_0002',
            'data_type': 'announcement',
            'date': '2023-05-20',
            'title': '修正「公開發行公司年報應行記載事項準則」',
            'source_raw': '證券期貨局',
            'detail_url': 'https://www.fsc.gov.tw/...',
            'content': {
                'text': '為完善年報揭露制度，修正部分條文...',
                'html': '...'
            },
            'metadata': {
                'announcement_number': '金管證發字第1120000002號',
                'category': 'amendment',
                'source': 'securities_bureau'
            }
        },

        # 一般公告（不是修正類，沒有版本關係）
        {
            'id': 'fsc_ann_20250410_0003',
            'data_type': 'announcement',
            'date': '2025-04-10',
            'title': '金管會舉辦金融科技創新論壇',
            'source_raw': '金管會',
            'detail_url': 'https://www.fsc.gov.tw/...',
            'content': {
                'text': '為推動金融科技發展，將舉辦創新論壇...',
                'html': '...'
            },
            'metadata': {
                'announcement_number': '金管會字第1140000003號',
                'category': 'announcement',
                'source': 'fsc_main'
            }
        }
    ]

    return items


def main():
    """主程式"""
    logger.info("=" * 70)
    logger.info("測試公告時效性標註功能")
    logger.info("=" * 70)

    try:
        # 1. 建立測試資料
        logger.info("\n[1/5] 建立測試資料")
        items = create_test_data()
        logger.info(f"✓ 建立 {len(items)} 筆測試公告")
        logger.info(f"  - 保險業內部控制辦法: 3 個版本")
        logger.info(f"  - 年報記載事項準則: 2 個版本")
        logger.info(f"  - 一般公告: 1 筆")

        # 2. 建立版本追蹤器
        logger.info("\n[2/5] 建立版本追蹤器")
        tracker = VersionTracker()
        stats = tracker.build_version_map(items)

        logger.info(f"✓ 版本對應表建立完成")
        logger.info(f"  - 修正類公告: {stats['amendment_count']} 筆")
        logger.info(f"  - 有多版本的法規: {stats['regulation_count']} 個")
        logger.info(f"  - 最新版本: {stats['latest_count']} 個")
        logger.info(f"  - 過時版本: {stats['superseded_count']} 個")

        # 3. 測試版本識別
        logger.info("\n[3/5] 測試版本識別")
        logger.info("=" * 70)

        for item in items[:3]:  # 只顯示前 3 筆
            version_info = tracker.get_version_info(item)
            logger.info(f"\n標題: {item['title'][:50]}...")
            logger.info(f"  日期: {item['date']}")
            logger.info(f"  法規名稱: {version_info['regulation_name']}")
            logger.info(f"  是否最新: {version_info['is_latest']}")
            logger.info(f"  是否過時: {version_info['is_superseded']}")
            logger.info(f"  總版本數: {version_info['total_versions']}")

        # 4. 格式化 Markdown（含時效性標註）
        logger.info("\n[4/5] 格式化 Markdown（含時效性標註）")
        logger.info("=" * 70)

        formatter = MarkdownFormatter(version_tracker=tracker)
        output_dir = Path('data/markdown/temporal_test')
        output_dir.mkdir(parents=True, exist_ok=True)

        for item in items:
            md_content = formatter.format_announcement(item)

            # 儲存為檔案
            filename = f"{item['id']}.md"
            output_file = output_dir / filename

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md_content)

            logger.info(f"✓ {filename}")

        logger.info(f"\n所有檔案已儲存至: {output_dir}/")

        # 5. 顯示最新版本的範例
        logger.info("\n[5/5] 最新版本範例預覽")
        logger.info("=" * 70)

        # 找到最新版本
        latest_item = items[0]  # 保險業內部控制辦法 2025-01-01
        md_content = formatter.format_announcement(latest_item)

        logger.info("\n前 1000 字元預覽:\n")
        print(md_content[:1000])
        logger.info("\n...")

        # 6. 顯示過時版本的範例
        logger.info("\n" + "=" * 70)
        logger.info("過時版本範例預覽")
        logger.info("=" * 70)

        superseded_item = items[1]  # 保險業內部控制辦法 2023-12-15
        md_content = formatter.format_announcement(superseded_item)

        logger.info("\n前 1000 字元預覽:\n")
        print(md_content[:1000])
        logger.info("\n...")

        # 7. 統計資訊
        logger.info("\n" + "=" * 70)
        logger.info("時效性標註統計")
        logger.info("=" * 70)

        latest_count = sum(1 for item in items if tracker.get_version_info(item)['is_latest'])
        superseded_count = sum(1 for item in items if tracker.get_version_info(item)['is_superseded'])
        no_version_count = len(items) - latest_count - superseded_count

        logger.info(f"總公告數: {len(items)}")
        logger.info(f"  ⭐ 最新版本: {latest_count} 筆")
        logger.info(f"  ⚠️ 已過時: {superseded_count} 筆")
        logger.info(f"  📄 無版本關係: {no_version_count} 筆")

        # 8. 版本歷程詳情
        logger.info("\n" + "=" * 70)
        logger.info("版本歷程詳情")
        logger.info("=" * 70)

        tracker_stats = tracker.get_statistics()
        top_regulations = tracker_stats['top_10_regulations']

        for i, reg in enumerate(top_regulations, 1):
            logger.info(f"\n[{i}] {reg['name']}")
            logger.info(f"    版本數: {reg['versions']}")
            logger.info(f"    日期: {', '.join(reg['dates'])}")

        logger.info("\n" + "=" * 70)
        logger.info("測試完成!")
        logger.info("=" * 70)

        logger.info("\n✓ 公告時效性標註功能測試完成")
        logger.info(f"\nMarkdown 檔案已儲存至: {output_dir}/")

    except Exception as e:
        logger.error(f"測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
