"""
公告 Plain Text 優化格式化器 - 為 RAG 檢索優化

設計原則：
- 移除網頁雜訊（Facebook、Line、友善列印等）
- 最小化 metadata（只保留檢索相關資訊）
- 零重複、高語義密度
- 統一格式，易於維護
"""

from typing import Dict, Any, List
from .base_plaintext_optimizer import BasePlainTextOptimizer


class AnnouncementPlainTextOptimizer(BasePlainTextOptimizer):
    """公告 Plain Text 優化格式化器"""

    def __init__(self):
        """初始化格式化器"""
        super().__init__()

        # 公告類型人類可讀對應
        self.category_display_names = {
            'ann_regulation': '一般公告（令）',
            'ann_amendment': '修正類',
            'ann_enactment': '訂定類',
            'ann_designation': '指定類',
            'ann_draft': '預告類',
            'ann_publication': '發布類',
            'ann_repeal': '廢止類'
        }

    def format_metadata(self, item: Dict[str, Any]) -> List[str]:
        """
        格式化公告 metadata 部分

        Args:
            item: 公告資料項目

        Returns:
            metadata 文字行列表
        """
        lines = []

        # 發文日期 - 重要（時間範圍查詢）
        if 'date' in item and item['date']:
            lines.append(f"發文日期: {item['date']}")

        # 來源單位 - 重要（單位篩選）
        source_raw = item.get('source_raw', '')
        if source_raw:
            lines.append(f"來源單位: {source_raw}")

        # 標題 - 極重要（核心檢索欄位）
        title = item.get('title', '')
        if title:
            lines.append(f"標題: {title}")

        # 提取 metadata
        metadata = item.get('metadata', {})

        # 公告文號 - 重要（精確查詢）
        announcement_number = metadata.get('announcement_number')
        if announcement_number:
            lines.append(f"發文字號: {announcement_number}")

        # 公告類型 - 有用（類型篩選）
        category = metadata.get('category')
        if category:
            category_name = self.category_display_names.get(category, category)
            lines.append(f"公告類型: {category_name}")

        # 附件數量 - 參考資訊
        attachments = item.get('attachments', [])
        if attachments:
            lines.append(f"附件數量: {len(attachments)} 個")

        return lines
