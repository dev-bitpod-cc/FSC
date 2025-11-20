#!/usr/bin/env python3
"""
重要公告上傳到 Gemini File Search

功能:
1. 從 JSONL 讀取重要公告資料
2. 生成優化的 Plain Text 格式
3. 上傳到 Gemini File Search Store
4. 生成 announcements_mapping.json 和 gemini_id_mapping.json

上傳策略:
- P0 類型 (ann_regulation): 優先上傳
- P1 類型 (ann_amendment, ann_enactment, ann_designation): 次要上傳
- P2 類型 (ann_draft, ann_publication, ann_repeal): 選擇性上傳
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.storage.jsonl_handler import JSONLHandler
from src.processor.announcement_plaintext_optimizer import AnnouncementPlainTextOptimizer
from dotenv import load_dotenv
import os
import google.generativeai as genai


class AnnouncementsUploader:
    """重要公告上傳器"""

    def __init__(self, api_key: str, store_name: str = 'fsc-announcements'):
        """
        初始化上傳器

        Args:
            api_key: Gemini API Key
            store_name: Store 名稱
        """
        self.api_key = api_key
        self.store_name = store_name

        # 初始化 Gemini API
        genai.configure(api_key=api_key)

        # 優先級定義（使用 ann_ 前綴）
        self.priority_mapping = {
            # P0: 核心類型（一般公告令）
            'ann_regulation': 0,
            # P1: 補充類型
            'ann_amendment': 1,
            'ann_enactment': 1,
            'ann_designation': 1,
            # P2: 輔助類型
            'ann_draft': 2,
            'ann_publication': 2,
            'ann_repeal': 2,
            # 其他
            'ann_other': 3,
            'unknown': 3,
        }

        # 初始化格式化器
        self.optimizer = AnnouncementPlainTextOptimizer()

        # 上傳統計
        self.stats = {
            'total': 0,
            'uploaded_plaintext': 0,
            'skipped': 0,
            'failed': 0,
        }

        # Mapping 資料
        self.mapping_data = {}
        self.gemini_id_mapping = {}

        logger.info(f"初始化重要公告上傳器")
        logger.info(f"Store 名稱: {store_name}")

    def get_or_create_store(self) -> str:
        """
        取得或建立 File Search Store

        Returns:
            Store ID
        """
        try:
            logger.info(f"創建新的 File Search Store: {self.store_name}")

            # 使用新的 API 創建 store
            store = genai.create_file_store(display_name=self.store_name)
            store_id = store.name

            logger.info(f"Store 已創建: {store_id}")
            return store_id

        except Exception as e:
            logger.error(f"創建 Store 失敗: {e}")
            raise

    def should_upload(self, item: Dict[str, Any], priority_level: int = 1) -> bool:
        """
        判斷是否應該上傳此公告

        Args:
            item: 公告資料
            priority_level: 優先級門檻 (0=P0, 1=P0+P1, 2=全部)

        Returns:
            是否上傳
        """
        category = item.get('metadata', {}).get('category', 'unknown')
        item_priority = self.priority_mapping.get(category, 3)

        return item_priority <= priority_level

    def upload_plaintext(self, plaintext_content: str, display_name: str) -> Optional[str]:
        """
        上傳 Plain Text 到 Gemini

        Args:
            plaintext_content: Plain Text 內容
            display_name: 顯示名稱

        Returns:
            File ID 或 None
        """
        try:
            logger.info(f"上傳 Plain Text: {display_name}")

            # 建立暫存檔案
            temp_dir = Path('data/temp_plaintext_announcements')
            temp_dir.mkdir(parents=True, exist_ok=True)

            temp_file = temp_dir / f"{display_name}.txt"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(plaintext_content)

            # 上傳檔案
            uploaded_file = genai.upload_file(
                path=str(temp_file),
                display_name=display_name
            )

            # 刪除暫存檔案
            temp_file.unlink()

            logger.info(f"  ✓ 上傳成功: {uploaded_file.name}")
            return uploaded_file.name

        except Exception as e:
            logger.error(f"  ✗ 上傳失敗: {e}")
            return None

    def process_item(self, item: Dict[str, Any], delay: float = 2.0) -> bool:
        """
        處理單個公告

        Args:
            item: 公告資料
            delay: 上傳延遲（秒）

        Returns:
            是否成功
        """
        item_id = item.get('id', 'unknown')
        title = item.get('title', '無標題')
        category = item.get('metadata', {}).get('category', 'unknown')

        logger.info(f"\n處理 [{self.stats['total'] + 1}]: {item_id}")
        logger.info(f"  標題: {title[:60]}...")
        logger.info(f"  類型: {category}")

        # 生成顯示名稱
        date = item.get('date', 'unknown')
        source = item.get('metadata', {}).get('source', 'unknown')
        display_name = f"{date}_{source}_{category}_{item_id}"

        # 生成 Plain Text
        logger.info(f"  → 生成並上傳 Plain Text")
        plaintext_content = self.optimizer.format_item(item)
        file_id = self.upload_plaintext(plaintext_content, display_name)

        if file_id:
            self.stats['uploaded_plaintext'] += 1

            # 記錄到 mapping
            self.gemini_id_mapping[item_id] = file_id

            # 記錄詳細 mapping
            self.mapping_data[item_id] = {
                'display_name': display_name,
                'gemini_file_id': file_id,
                'original_url': item.get('detail_url', ''),
                'date': date,
                'source': source,
                'category': category,
                'announcement_number': item.get('metadata', {}).get('announcement_number', ''),
                'upload_type': 'plaintext',
                'uploaded_at': datetime.now().isoformat(),
            }

            self.stats['total'] += 1

            # 延遲
            time.sleep(delay)
            return True
        else:
            self.stats['failed'] += 1
            self.stats['total'] += 1
            return False

    def upload_all(
        self,
        jsonl_path: str = 'data/announcements/raw.jsonl',
        priority_level: int = 1,
        delay: float = 2.0,
        max_items: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        上傳所有重要公告

        Args:
            jsonl_path: JSONL 檔案路徑
            priority_level: 優先級門檻 (0=P0, 1=P0+P1, 2=全部)
            delay: 上傳延遲（秒）
            max_items: 最大上傳數量（測試用）

        Returns:
            統計資訊
        """
        logger.info("=" * 70)
        logger.info("開始上傳重要公告到 Gemini File Search")
        logger.info("=" * 70)

        # 讀取資料
        logger.info(f"\n讀取資料: {jsonl_path}")
        storage = JSONLHandler()
        all_items = storage.read_all('announcements')

        if not all_items:
            logger.error("沒有資料可上傳")
            return self.stats

        logger.info(f"總資料筆數: {len(all_items)}")

        # 篩選優先級
        filtered_items = [
            item for item in all_items
            if self.should_upload(item, priority_level)
        ]

        logger.info(f"符合優先級 P{priority_level} 的公告: {len(filtered_items)} 筆")

        # 限制數量（測試用）
        if max_items:
            filtered_items = filtered_items[:max_items]
            logger.info(f"限制上傳數量: {max_items} 筆")

        # 統計類型分布
        category_counts = {}
        for item in filtered_items:
            cat = item.get('metadata', {}).get('category', 'unknown')
            category_counts[cat] = category_counts.get(cat, 0) + 1

        logger.info(f"\n類型分布:")
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {cat or 'None'}: {count} 筆")

        logger.info(f"\n開始上傳...")
        logger.info("-" * 70)

        # 處理每個項目
        for item in filtered_items:
            try:
                self.process_item(item, delay=delay)
            except Exception as e:
                logger.error(f"處理失敗: {item.get('id')} - {e}")
                self.stats['failed'] += 1
                self.stats['total'] += 1

        # 儲存 mapping
        self.save_mappings()

        # 顯示統計
        self.print_stats()

        return self.stats

    def save_mappings(self):
        """儲存 mapping 檔案"""
        logger.info("\n" + "=" * 70)
        logger.info("儲存 Mapping 檔案")
        logger.info("=" * 70)

        # 1. announcements_mapping.json (詳細資訊)
        mapping_file = Path('data/announcements/announcements_mapping.json')
        mapping_file.parent.mkdir(parents=True, exist_ok=True)

        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(self.mapping_data, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ 儲存詳細 mapping: {mapping_file}")
        logger.info(f"  共 {len(self.mapping_data)} 筆")

        # 2. gemini_id_mapping.json (簡化版本)
        gemini_mapping_file = Path('data/announcements/gemini_id_mapping.json')

        with open(gemini_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(self.gemini_id_mapping, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ 儲存 Gemini ID mapping: {gemini_mapping_file}")

    def print_stats(self):
        """顯示統計資訊"""
        logger.info("\n" + "=" * 70)
        logger.info("上傳統計")
        logger.info("=" * 70)

        logger.info(f"總處理數: {self.stats['total']}")
        logger.info(f"  ✓ 上傳 Plain Text: {self.stats['uploaded_plaintext']}")
        logger.info(f"  - 跳過: {self.stats['skipped']}")
        logger.info(f"  ✗ 失敗: {self.stats['failed']}")

        success_rate = (
            self.stats['uploaded_plaintext'] / self.stats['total'] * 100
            if self.stats['total'] > 0 else 0
        )

        logger.info(f"\n成功率: {success_rate:.1f}%")


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='上傳重要公告到 Gemini File Search')
    parser.add_argument('--priority', type=int, default=1, choices=[0, 1, 2],
                        help='優先級門檻 (0=P0 only, 1=P0+P1, 2=全部)')
    parser.add_argument('--delay', type=float, default=2.0,
                        help='上傳延遲（秒）')
    parser.add_argument('--max-items', type=int, default=None,
                        help='最大上傳數量（測試用）')
    parser.add_argument('--store-name', type=str, default='fsc-announcements',
                        help='Store 名稱')

    args = parser.parse_args()

    # 設定日誌
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"logs/announcements_upload_{timestamp}.log"
    Path('logs').mkdir(exist_ok=True)

    logger.add(
        log_file,
        rotation="100 MB",
        retention="30 days",
        level="DEBUG"
    )

    logger.info(f"日誌檔案: {log_file}")

    # 載入 API Key
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        logger.error("請設定 GEMINI_API_KEY 環境變數")
        return

    # 初始化上傳器
    uploader = AnnouncementsUploader(api_key, store_name=args.store_name)

    # 上傳
    stats = uploader.upload_all(
        priority_level=args.priority,
        delay=args.delay,
        max_items=args.max_items
    )

    logger.info("\n" + "=" * 70)
    logger.info("完成！")
    logger.info("=" * 70)
    logger.info(f"日誌檔案: {log_file}")


if __name__ == '__main__':
    main()
