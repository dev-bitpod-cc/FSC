"""索引管理模組"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
from loguru import logger


class IndexManager:
    """索引管理器 - 提供快速查詢能力"""

    def __init__(self, data_dir: str = "data"):
        """
        初始化索引管理器

        Args:
            data_dir: 資料目錄
        """
        self.data_dir = Path(data_dir)

    def get_index_path(self, source: str) -> Path:
        """取得索引檔案路徑"""
        return self.data_dir / source / "index.json"

    def get_metadata_path(self, source: str) -> Path:
        """取得 metadata 檔案路徑"""
        return self.data_dir / source / "metadata.json"

    def load_index(self, source: str) -> Dict[str, Any]:
        """
        載入索引

        Args:
            source: 資料源名稱

        Returns:
            索引字典
        """
        index_path = self.get_index_path(source)

        if not index_path.exists():
            logger.info(f"索引檔案不存在,返回空索引: {index_path}")
            return self._create_empty_index()

        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"載入索引失敗: {e}")
            return self._create_empty_index()

    def save_index(self, source: str, index: Dict[str, Any]):
        """
        儲存索引

        Args:
            source: 資料源名稱
            index: 索引字典
        """
        index_path = self.get_index_path(source)
        index_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)

            logger.info(f"索引已儲存: {index_path}")

        except Exception as e:
            logger.error(f"儲存索引失敗: {e}")
            raise

    def load_metadata(self, source: str) -> Dict[str, Any]:
        """
        載入 metadata

        Args:
            source: 資料源名稱

        Returns:
            metadata 字典
        """
        metadata_path = self.get_metadata_path(source)

        if not metadata_path.exists():
            logger.info(f"Metadata 不存在,返回預設值: {metadata_path}")
            return self._create_empty_metadata(source)

        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"載入 metadata 失敗: {e}")
            return self._create_empty_metadata(source)

    def save_metadata(self, source: str, metadata: Dict[str, Any]):
        """
        儲存 metadata

        Args:
            source: 資料源名稱
            metadata: metadata 字典
        """
        metadata_path = self.get_metadata_path(source)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            logger.info(f"Metadata 已儲存: {metadata_path}")

        except Exception as e:
            logger.error(f"儲存 metadata 失敗: {e}")
            raise

    def build_index(self, source: str, items: List[Dict[str, Any]]):
        """
        從資料建立索引

        Args:
            source: 資料源名稱
            items: 資料列表
        """
        logger.info(f"開始建立索引: {source} - {len(items)} 筆資料")

        index = self._create_empty_index()

        # 按日期索引
        by_date = defaultdict(lambda: {'line_numbers': [], 'count': 0})

        # 按來源單位索引 (for announcements)
        by_source = defaultdict(lambda: {'count': 0, 'latest_line': 0})

        # 按 ID 索引
        by_id = {}

        for line_num, item in enumerate(items, 1):
            # 日期索引
            if 'date' in item:
                date = item['date']
                by_date[date]['line_numbers'].append(line_num)
                by_date[date]['count'] += 1

            # 來源單位索引 (從 metadata.source 取得)
            source_unit = None
            if 'metadata' in item and 'source' in item['metadata']:
                source_unit = item['metadata']['source']
            elif 'source' in item:
                source_unit = item['source']

            if source_unit:
                by_source[source_unit]['count'] += 1
                by_source[source_unit]['latest_line'] = line_num

            # ID 索引
            if 'id' in item:
                by_id[item['id']] = {
                    'line': line_num,
                    'date': item.get('date'),
                    'source': source_unit
                }

        # 轉換為普通字典
        index['by_date'] = dict(by_date)
        index['by_source'] = dict(by_source)
        index['by_id'] = by_id

        # 儲存索引
        self.save_index(source, index)

        # 更新 metadata
        metadata = self.load_metadata(source)
        metadata['total_count'] = len(items)
        metadata['last_index_build'] = datetime.now().isoformat()

        if items:
            # 日期範圍
            dates = [item['date'] for item in items if 'date' in item]
            if dates:
                metadata['date_range'] = [min(dates), max(dates)]

            # 最後一筆
            last_item = items[-1]
            if 'date' in last_item:
                metadata['last_crawl_date'] = last_item['date']
            if 'id' in last_item:
                metadata['last_id'] = last_item['id']

        self.save_metadata(source, metadata)

        logger.info(f"索引建立完成: {source}")

    def update_index(self, source: str, new_items: List[Dict[str, Any]]):
        """
        更新索引 (增量)

        Args:
            source: 資料源名稱
            new_items: 新增的資料列表
        """
        if not new_items:
            logger.info("無新資料,跳過索引更新")
            return

        logger.info(f"更新索引: {source} - {len(new_items)} 筆新資料")

        # 載入現有索引和 metadata
        index = self.load_index(source)
        metadata = self.load_metadata(source)

        # 取得當前行號起始位置
        current_count = metadata.get('total_count', 0)
        start_line = current_count + 1

        # 更新索引
        for offset, item in enumerate(new_items):
            line_num = start_line + offset

            # 日期索引
            if 'date' in item:
                date = item['date']
                if date not in index['by_date']:
                    index['by_date'][date] = {'line_numbers': [], 'count': 0}

                index['by_date'][date]['line_numbers'].append(line_num)
                index['by_date'][date]['count'] += 1

            # 來源單位索引
            if 'source' in item:
                source_unit = item['source']
                if source_unit not in index['by_source']:
                    index['by_source'][source_unit] = {'count': 0, 'latest_line': 0}

                index['by_source'][source_unit]['count'] += 1
                index['by_source'][source_unit]['latest_line'] = line_num

            # ID 索引
            if 'id' in item:
                index['by_id'][item['id']] = {
                    'line': line_num,
                    'date': item.get('date'),
                    'source': item.get('source')
                }

        # 儲存更新後的索引
        self.save_index(source, index)

        # 更新 metadata
        metadata['total_count'] = current_count + len(new_items)
        metadata['last_index_update'] = datetime.now().isoformat()

        if new_items:
            last_item = new_items[-1]
            if 'date' in last_item:
                metadata['last_crawl_date'] = last_item['date']
            if 'id' in last_item:
                metadata['last_id'] = last_item['id']

            # 更新日期範圍
            dates = [item['date'] for item in new_items if 'date' in item]
            if dates:
                existing_range = metadata.get('date_range', [None, None])
                min_date = min([d for d in [existing_range[0]] + dates if d])
                max_date = max([d for d in [existing_range[1]] + dates if d])
                metadata['date_range'] = [min_date, max_date]

        self.save_metadata(source, metadata)

        logger.info(f"索引更新完成: {source}")

    def get_items_by_date(self, source: str, date: str) -> List[int]:
        """
        取得特定日期的行號列表

        Args:
            source: 資料源名稱
            date: 日期 (YYYY-MM-DD)

        Returns:
            行號列表
        """
        index = self.load_index(source)
        return index['by_date'].get(date, {}).get('line_numbers', [])

    def get_items_by_source_unit(self, source: str, source_unit: str) -> Dict[str, Any]:
        """
        取得特定來源單位的統計資訊

        Args:
            source: 資料源名稱
            source_unit: 來源單位 (bank_bureau, securities_bureau, etc.)

        Returns:
            統計資訊
        """
        index = self.load_index(source)
        return index['by_source'].get(source_unit, {'count': 0, 'latest_line': 0})

    def get_line_by_id(self, source: str, item_id: str) -> Optional[int]:
        """
        根據 ID 取得行號

        Args:
            source: 資料源名稱
            item_id: 資料 ID

        Returns:
            行號或 None
        """
        index = self.load_index(source)
        item_info = index['by_id'].get(item_id)

        if item_info:
            return item_info['line']

        return None

    def _create_empty_index(self) -> Dict[str, Any]:
        """建立空索引結構"""
        return {
            'by_date': {},
            'by_source': {},
            'by_id': {}
        }

    def _create_empty_metadata(self, source: str) -> Dict[str, Any]:
        """建立空 metadata 結構"""
        return {
            'data_type': source,
            'total_count': 0,
            'last_crawl_date': None,
            'last_id': None,
            'date_range': [None, None],
            'created_at': datetime.now().isoformat()
        }
