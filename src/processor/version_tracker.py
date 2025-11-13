"""版本追蹤器 - 識別公告的修正關係與時效性"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict
import re
from loguru import logger


class VersionTracker:
    """公告版本追蹤器"""

    def __init__(self):
        """初始化版本追蹤器"""
        self.regulation_versions = defaultdict(list)
        self.latest_versions = {}
        self.superseded_items = set()

    def extract_regulation_name(self, title: str) -> Optional[str]:
        """
        從標題中提取法規名稱

        Args:
            title: 公告標題

        Returns:
            法規名稱（正規化後）
        """
        # 模式 1: 修正「XXX」
        match = re.search(r'修正[「『]([^」』]+)[」』]', title)
        if match:
            return match.group(1).strip()

        # 模式 2: 訂定「XXX」
        match = re.search(r'訂定[「『]([^」』]+)[」』]', title)
        if match:
            return match.group(1).strip()

        # 模式 3: 發布「XXX」
        match = re.search(r'發布[「『]([^」』]+)[」』]', title)
        if match:
            return match.group(1).strip()

        # 模式 4: 廢止「XXX」
        match = re.search(r'廢止[「『]([^」』]+)[」』]', title)
        if match:
            return match.group(1).strip()

        # 模式 5: 增訂「XXX」
        match = re.search(r'增訂[「『]([^」』]+)[」』]', title)
        if match:
            return match.group(1).strip()

        return None

    def is_amendment_type(self, item: Dict[str, Any]) -> bool:
        """
        判斷是否為修正類公告

        Args:
            item: 公告資料

        Returns:
            是否為修正類
        """
        category = item.get('metadata', {}).get('category')
        if category in ['amendment', 'regulation']:
            return True

        title = item.get('title', '')
        keywords = ['修正', '訂定', '發布', '廢止', '增訂']
        return any(keyword in title for keyword in keywords)

    def build_version_map(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        建立版本對應表

        Args:
            items: 公告列表

        Returns:
            版本統計資訊
        """
        logger.info("開始建立版本對應表...")

        # 重置
        self.regulation_versions.clear()
        self.latest_versions.clear()
        self.superseded_items.clear()

        amendment_count = 0
        regulation_count = 0

        for item in items:
            # 只處理修正類公告
            if not self.is_amendment_type(item):
                continue

            amendment_count += 1

            # 提取法規名稱
            title = item.get('title', '')
            regulation_name = self.extract_regulation_name(title)

            if not regulation_name:
                continue

            # 正規化法規名稱（移除空格、全形轉半形）
            regulation_name = self._normalize_regulation_name(regulation_name)

            # 記錄此法規的版本
            self.regulation_versions[regulation_name].append({
                'id': item.get('id'),
                'date': item.get('date'),
                'title': title,
                'item': item
            })

        # 統計每個法規的版本
        for regulation_name, versions in self.regulation_versions.items():
            if len(versions) > 1:
                regulation_count += 1

                # 按日期排序
                versions.sort(key=lambda x: x['date'], reverse=True)

                # 記錄最新版本
                latest = versions[0]
                self.latest_versions[regulation_name] = latest['id']

                # 標記過時版本
                for version in versions[1:]:
                    self.superseded_items.add(version['id'])

        logger.info(f"版本對應表建立完成:")
        logger.info(f"  修正類公告: {amendment_count} 筆")
        logger.info(f"  有多版本的法規: {regulation_count} 個")
        logger.info(f"  最新版本: {len(self.latest_versions)} 個")
        logger.info(f"  過時版本: {len(self.superseded_items)} 個")

        return {
            'amendment_count': amendment_count,
            'regulation_count': regulation_count,
            'latest_count': len(self.latest_versions),
            'superseded_count': len(self.superseded_items)
        }

    def get_version_info(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        取得公告的版本資訊

        Args:
            item: 公告資料

        Returns:
            版本資訊 {
                'is_latest': bool,
                'is_superseded': bool,
                'regulation_name': str,
                'version_history': List[Dict],
                'total_versions': int
            }
        """
        item_id = item.get('id')

        # 預設資訊
        info = {
            'is_latest': False,
            'is_superseded': False,
            'regulation_name': None,
            'version_history': [],
            'total_versions': 1
        }

        # 不是修正類，直接返回
        if not self.is_amendment_type(item):
            return info

        # 提取法規名稱
        title = item.get('title', '')
        regulation_name = self.extract_regulation_name(title)

        if not regulation_name:
            return info

        regulation_name = self._normalize_regulation_name(regulation_name)
        info['regulation_name'] = regulation_name

        # 檢查是否有版本資訊
        if regulation_name not in self.regulation_versions:
            return info

        versions = self.regulation_versions[regulation_name]
        info['total_versions'] = len(versions)
        info['version_history'] = [
            {
                'date': v['date'],
                'title': v['title'],
                'id': v['id']
            }
            for v in versions
        ]

        # 判斷是否為最新版本
        if regulation_name in self.latest_versions:
            info['is_latest'] = (self.latest_versions[regulation_name] == item_id)

        # 判斷是否已過時
        info['is_superseded'] = (item_id in self.superseded_items)

        return info

    def _normalize_regulation_name(self, name: str) -> str:
        """
        正規化法規名稱

        Args:
            name: 原始法規名稱

        Returns:
            正規化後的法規名稱
        """
        # 移除空格
        name = name.replace(' ', '').replace('　', '')

        # 全形轉半形（數字、英文）
        name = name.translate(str.maketrans(
            '０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
            '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        ))

        return name.strip()

    def get_statistics(self) -> Dict[str, Any]:
        """
        取得版本追蹤統計資訊

        Returns:
            統計資訊
        """
        # 找出版本最多的法規
        top_regulations = []
        for regulation_name, versions in self.regulation_versions.items():
            if len(versions) > 1:
                top_regulations.append({
                    'name': regulation_name,
                    'versions': len(versions),
                    'dates': [v['date'] for v in versions]
                })

        # 按版本數排序
        top_regulations.sort(key=lambda x: x['versions'], reverse=True)

        return {
            'total_regulations': len(self.regulation_versions),
            'multi_version_regulations': len([r for r in self.regulation_versions.values() if len(r) > 1]),
            'latest_versions': len(self.latest_versions),
            'superseded_versions': len(self.superseded_items),
            'top_10_regulations': top_regulations[:10]
        }
