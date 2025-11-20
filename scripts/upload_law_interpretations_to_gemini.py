#!/usr/bin/env python3
"""
法令函釋上傳到 Gemini File Search

功能:
1. 從 JSONL 讀取法令函釋資料
2. 根據類型和附件情況決定上傳策略：
   - 修正型：只上傳對照表 PDF（最重要）
   - 訂定型/函釋型：有附件上傳 PDF，無附件生成 Markdown
3. 上傳到 Gemini File Search Store
4. 生成 law_interpretations_mapping.json 和 gemini_id_mapping.json

上傳策略 (基於 docs/law_interpretations_analysis.md):
- P0 類型 (amendment, enactment, clarification): 優先上傳
- P1 類型 (approval, announcement): 次要上傳
- P2 類型 (repeal, adjustment): 選擇性上傳
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.storage.jsonl_handler import JSONLHandler
from src.processor.law_interpretation_markdown_formatter import LawInterpretationMarkdownFormatter
from dotenv import load_dotenv
import os
import google.generativeai as genai


class LawInterpretationsUploader:
    """法令函釋上傳器"""

    def __init__(self, api_key: str, store_name: str = 'fsc-law-interpretations'):
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

        # 優先級定義
        self.priority_mapping = {
            # P0: 核心類型 (69%)
            'amendment': 0,
            'enactment': 0,
            'clarification': 0,
            # P1: 補充類型 (17%)
            'approval': 1,
            'announcement': 1,
            # P2: 歷史類型 (15%)
            'repeal': 2,
            'adjustment': 2,
            'notice': 2,
            # 其他
            'other': 3,
            'unknown': 3,
        }

        # 初始化格式化器
        self.formatter = LawInterpretationMarkdownFormatter()

        # 上傳統計
        self.stats = {
            'total': 0,
            'uploaded_pdf': 0,
            'uploaded_markdown': 0,
            'skipped': 0,
            'failed': 0,
        }

        # Mapping 資料
        self.mapping_data = {}
        self.gemini_id_mapping = {}

        logger.info(f"初始化法令函釋上傳器")
        logger.info(f"Store 名稱: {store_name}")

    def get_or_create_store(self) -> str:
        """
        取得或建立 File Search Store

        Returns:
            Store ID
        """
        try:
            # 列出所有 stores
            stores = genai.list_files()

            # 尋找同名 store (實際上 list_files 不會返回 store，需要另外處理)
            # 這裡我們直接創建新的 store
            logger.info(f"創建新的 File Search Store: {self.store_name}")

            # 使用新的 API 創建 store
            # 注意：這裡需要根據實際 Gemini API 文檔調整
            store = genai.create_file_store(display_name=self.store_name)
            store_id = store.name

            logger.info(f"Store 已創建: {store_id}")
            return store_id

        except Exception as e:
            logger.error(f"創建 Store 失敗: {e}")
            raise

    def should_upload(self, item: Dict[str, Any], priority_level: int = 1) -> bool:
        """
        判斷是否應該上傳此函釋

        Args:
            item: 函釋資料
            priority_level: 優先級門檻 (0=P0, 1=P0+P1, 2=全部)

        Returns:
            是否上傳
        """
        category = item.get('metadata', {}).get('category', 'unknown')
        item_priority = self.priority_mapping.get(category, 3)

        return item_priority <= priority_level

    def determine_upload_strategy(self, item: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        """
        決定上傳策略

        Args:
            item: 函釋資料

        Returns:
            (upload_type, file_path)
            - upload_type: 'pdf' 或 'markdown' 或 'skip'
            - file_path: PDF 路徑或 None (如果是 markdown)
        """
        category = item.get('metadata', {}).get('category', 'unknown')
        attachments = item.get('attachments', [])

        # 修正型：只上傳對照表 PDF
        if category == 'amendment':
            # 尋找對照表
            for att in attachments:
                if att.get('classification') == 'comparison_table':
                    # 檢查是否已下載
                    local_path = att.get('local_path')
                    if local_path and Path(local_path).exists():
                        return ('pdf', local_path)
                    else:
                        logger.warning(f"對照表未下載: {item['id']}")
                        return ('skip', None)

            # 如果沒有對照表，跳過
            logger.warning(f"修正型函釋缺少對照表: {item['id']}")
            return ('skip', None)

        # 訂定型 / 函釋型：有附件上傳，無附件生成 Markdown
        elif category in ['enactment', 'clarification', 'interpretation_decree']:
            if attachments:
                # 上傳第一個 PDF 附件
                for att in attachments:
                    if att.get('type') == 'pdf':
                        local_path = att.get('local_path')
                        if local_path and Path(local_path).exists():
                            return ('pdf', local_path)

                # 沒有 PDF，生成 Markdown
                return ('markdown', None)
            else:
                # 無附件，生成 Markdown
                return ('markdown', None)

        # 其他類型：根據附件情況決定
        else:
            if attachments:
                # 有附件，上傳 PDF
                for att in attachments:
                    if att.get('type') == 'pdf':
                        local_path = att.get('local_path')
                        if local_path and Path(local_path).exists():
                            return ('pdf', local_path)
                return ('markdown', None)
            else:
                # 無附件，生成 Markdown
                return ('markdown', None)

    def upload_pdf(self, pdf_path: str, display_name: str) -> Optional[str]:
        """
        上傳 PDF 到 Gemini

        Args:
            pdf_path: PDF 路徑
            display_name: 顯示名稱

        Returns:
            File ID 或 None
        """
        try:
            logger.info(f"上傳 PDF: {display_name}")

            # 上傳檔案
            uploaded_file = genai.upload_file(
                path=pdf_path,
                display_name=display_name
            )

            logger.info(f"  ✓ 上傳成功: {uploaded_file.name}")
            return uploaded_file.name

        except Exception as e:
            logger.error(f"  ✗ 上傳失敗: {e}")
            return None

    def upload_markdown(self, markdown_content: str, display_name: str) -> Optional[str]:
        """
        上傳 Markdown 到 Gemini

        Args:
            markdown_content: Markdown 內容
            display_name: 顯示名稱

        Returns:
            File ID 或 None
        """
        try:
            logger.info(f"上傳 Markdown: {display_name}")

            # 建立暫存檔案
            temp_dir = Path('data/temp_markdown_law_interpretations')
            temp_dir.mkdir(parents=True, exist_ok=True)

            temp_file = temp_dir / f"{display_name}.md"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

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
        處理單個函釋

        Args:
            item: 函釋資料
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

        # 決定上傳策略
        upload_type, file_path = self.determine_upload_strategy(item)

        if upload_type == 'skip':
            logger.info(f"  → 跳過")
            self.stats['skipped'] += 1
            self.stats['total'] += 1
            return False

        # 生成顯示名稱
        date = item.get('date', 'unknown')
        source = item.get('metadata', {}).get('source', 'unknown')
        display_name = f"{date}_{source}_{category}_{item_id}"

        # 上傳
        file_id = None

        if upload_type == 'pdf':
            logger.info(f"  → 上傳 PDF: {Path(file_path).name}")
            file_id = self.upload_pdf(file_path, display_name)
            if file_id:
                self.stats['uploaded_pdf'] += 1

        elif upload_type == 'markdown':
            logger.info(f"  → 生成並上傳 Markdown")
            # 生成 Markdown
            markdown_content = self.formatter.format_interpretation(item)
            file_id = self.upload_markdown(markdown_content, display_name)
            if file_id:
                self.stats['uploaded_markdown'] += 1

        if file_id:
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
                'law_name': item.get('metadata', {}).get('law_name', ''),
                'document_number': item.get('metadata', {}).get('document_number', ''),
                'upload_type': upload_type,
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
        jsonl_path: str = 'data/law_interpretations/raw.jsonl',
        priority_level: int = 1,
        delay: float = 2.0,
        max_items: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        上傳所有法令函釋

        Args:
            jsonl_path: JSONL 檔案路徑
            priority_level: 優先級門檻 (0=P0, 1=P0+P1, 2=全部)
            delay: 上傳延遲（秒）
            max_items: 最大上傳數量（測試用）

        Returns:
            統計資訊
        """
        logger.info("=" * 70)
        logger.info("開始上傳法令函釋到 Gemini File Search")
        logger.info("=" * 70)

        # 讀取資料
        handler = JSONLHandler()
        all_items = handler.read_all('law_interpretations')

        if not all_items:
            logger.error("找不到法令函釋資料")
            return self.stats

        logger.info(f"總共 {len(all_items)} 筆法令函釋")

        # 過濾優先級
        filtered_items = [
            item for item in all_items
            if self.should_upload(item, priority_level)
        ]

        logger.info(f"符合優先級 P{priority_level} 的函釋: {len(filtered_items)} 筆")

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
            logger.info(f"  {cat}: {count} 筆")

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

        # 1. law_interpretations_mapping.json (詳細資訊)
        mapping_file = Path('data/law_interpretations/law_interpretations_mapping.json')
        mapping_file.parent.mkdir(parents=True, exist_ok=True)

        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(self.mapping_data, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ 儲存詳細 mapping: {mapping_file}")
        logger.info(f"  共 {len(self.mapping_data)} 筆")

        # 2. gemini_id_mapping.json (簡化版本)
        gemini_mapping_file = Path('data/law_interpretations/gemini_id_mapping.json')

        with open(gemini_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(self.gemini_id_mapping, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ 儲存 Gemini ID mapping: {gemini_mapping_file}")

    def print_stats(self):
        """顯示統計資訊"""
        logger.info("\n" + "=" * 70)
        logger.info("上傳統計")
        logger.info("=" * 70)

        logger.info(f"總處理數: {self.stats['total']}")
        logger.info(f"  ✓ 上傳 PDF: {self.stats['uploaded_pdf']}")
        logger.info(f"  ✓ 上傳 Markdown: {self.stats['uploaded_markdown']}")
        logger.info(f"  - 跳過: {self.stats['skipped']}")
        logger.info(f"  ✗ 失敗: {self.stats['failed']}")

        success_rate = (
            (self.stats['uploaded_pdf'] + self.stats['uploaded_markdown']) /
            self.stats['total'] * 100
            if self.stats['total'] > 0 else 0
        )

        logger.info(f"\n成功率: {success_rate:.1f}%")


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='上傳法令函釋到 Gemini File Search')
    parser.add_argument('--priority', type=int, default=1, choices=[0, 1, 2],
                        help='優先級門檻 (0=P0 only, 1=P0+P1, 2=全部)')
    parser.add_argument('--delay', type=float, default=2.0,
                        help='上傳延遲（秒）')
    parser.add_argument('--max-items', type=int, default=None,
                        help='最大上傳數量（測試用）')
    parser.add_argument('--store-name', type=str, default='fsc-law-interpretations',
                        help='Store 名稱')

    args = parser.parse_args()

    # 載入環境變數
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        logger.error("未設定 GEMINI_API_KEY")
        return

    # 初始化上傳器
    uploader = LawInterpretationsUploader(api_key, store_name=args.store_name)

    # 上傳
    uploader.upload_all(
        priority_level=args.priority,
        delay=args.delay,
        max_items=args.max_items
    )


if __name__ == '__main__':
    main()
