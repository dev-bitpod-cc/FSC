"""
法令函釋 Plain Text 優化格式化器 - 為 RAG 檢索優化

設計原則：
- 移除網頁雜訊（Facebook、Line、友善列印等）
- 最小化 metadata（只保留檢索相關資訊）
- 零重複、高語義密度
- 統一格式，易於維護
"""

from typing import Dict, Any, List
from .base_plaintext_optimizer import BasePlainTextOptimizer


class LawInterpretationPlainTextOptimizer(BasePlainTextOptimizer):
    """法令函釋 Plain Text 優化格式化器"""

    def __init__(self):
        """初始化格式化器"""
        super().__init__()

        # 函釋類型人類可讀對應
        self.category_display_names = {
            'law_amendment': '修正型',
            'law_enactment': '訂定型',
            'law_clarification': '函釋型（有關）',
            'law_repeal': '廢止型',
            'law_publication': '發布/公布型',
            'law_approval': '核准/指定型',
            'law_adjustment': '調整型',
            'law_notice': '公告型',
            'law_interpretation_decree': '解釋令',
            'law_other': '其他'
        }

    def format_metadata(self, item: Dict[str, Any]) -> List[str]:
        """
        格式化法令函釋 metadata 部分

        Args:
            item: 法令函釋資料項目

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

        # 發文字號 - 重要（精確查詢）
        document_number = metadata.get('document_number')
        if document_number:
            lines.append(f"發文字號: {document_number}")

        # 法規名稱 - 重要（法規查詢）
        law_name = metadata.get('law_name')
        if law_name:
            lines.append(f"相關法規: {law_name}")

        # 修正條文 - 重要（條文查詢）
        amended_articles = metadata.get('amended_articles')
        if amended_articles and isinstance(amended_articles, list):
            articles_str = '、'.join(f'第{art}條' for art in amended_articles)
            lines.append(f"修正條文: {articles_str}")

        # 法條引用 - 重要（函釋型）
        law_reference = metadata.get('law_reference')
        if law_reference:
            lines.append(f"法條引用: {law_reference}")

        # 函釋類型 - 有用（類型篩選）
        category = metadata.get('category')
        if category:
            category_name = self.category_display_names.get(category, category)
            lines.append(f"函釋類型: {category_name}")

        # 附件數量 - 參考資訊
        attachments = item.get('attachments', [])
        if attachments:
            lines.append(f"附件數量: {len(attachments)} 個")

        return lines
