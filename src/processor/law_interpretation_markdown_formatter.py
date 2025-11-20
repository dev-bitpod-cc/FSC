"""法令函釋 Markdown 格式化器 - 將法令函釋資料轉換為 Gemini 友善的 Markdown 格式"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class LawInterpretationMarkdownFormatter:
    """法令函釋 Markdown 格式化器"""

    def __init__(self):
        """初始化格式化器"""
        self.category_names = {
            'law_amendment': '修正',
            'law_enactment': '訂定',
            'law_interpretation_decree': '函釋',
            'law_clarification': '有關',
            'law_repeal': '廢止',
            'law_publication': '公告',  # 發布/公布型（原 announcement）
            'law_approval': '核准',
            'law_adjustment': '調整',
            'law_notice': '通知'
        }

        self.source_names = {
            'fsc_main': '金管會本會',
            'bank_bureau': '銀行局',
            'securities_bureau': '證券期貨局',
            'insurance_bureau': '保險局',
            'examination_bureau': '檢查局',
            'unknown': '未分類'
        }

    def format_interpretation(self, item: Dict[str, Any]) -> str:
        """
        格式化單筆法令函釋為 Markdown

        Args:
            item: 法令函釋資料

        Returns:
            Markdown 格式的文字
        """
        md_lines = []

        # 標題
        title = item.get('title', '無標題')
        md_lines.append(f"# {title}\n")

        # 提取 metadata
        metadata = item.get('metadata', {})

        # ===== 基本資訊區塊 =====
        md_lines.append("## 📋 基本資訊\n")

        # 文件編號
        if 'id' in item:
            md_lines.append(f"- **文件編號**: `{item['id']}`")

        # 發文字號
        doc_number = metadata.get('document_number')
        if doc_number:
            md_lines.append(f"- **發文字號**: {doc_number}")

        # 發布日期
        if 'date' in item:
            md_lines.append(f"- **發布日期**: {item['date']}")

        # 來源單位
        source_raw = item.get('source_raw', '')
        if source_raw:
            md_lines.append(f"- **來源單位**: {source_raw}")

        # 標準化來源
        source = metadata.get('source')
        if source:
            source_name = self.source_names.get(source, source)
            md_lines.append(f"- **單位代碼**: {source_name}")

        # 法令函釋類型
        category = metadata.get('category')
        if category:
            category_name = self.category_names.get(category, category)
            md_lines.append(f"- **類型**: {category_name}")

        # 原始連結
        if 'detail_url' in item:
            md_lines.append(f"- **原始連結**: {item['detail_url']}")

        md_lines.append("")  # 空行

        # ===== 法律資訊 =====
        law_name = metadata.get('law_name')
        if law_name:
            md_lines.append("## 📜 相關法律\n")
            md_lines.append(f"- **法律名稱**: {law_name}")

            # 修正/訂定條文
            amended_articles = metadata.get('amended_articles')
            if amended_articles:
                if category == 'law_amendment':
                    md_lines.append(f"- **修正條文**: {amended_articles}")
                elif category == 'law_enactment':
                    md_lines.append(f"- **訂定條文**: {amended_articles}")

            # 法條參照
            law_reference = metadata.get('law_reference')
            if law_reference:
                md_lines.append(f"- **法條依據**: {law_reference}")

            md_lines.append("")  # 空行

        # ===== 完整內容 =====
        if 'content' in item:
            content = item['content']

            if isinstance(content, dict) and 'text' in content:
                text = content['text'].strip()
                if text:
                    md_lines.append("## 📄 函釋內容\n")
                    # 清理內容
                    text = self._clean_content(text)
                    md_lines.append(text)
                    md_lines.append("")

        # ===== 附件區塊 =====
        attachments = item.get('attachments', [])

        if attachments:
            md_lines.append("## 📎 相關附件\n")

            for i, att in enumerate(attachments, 1):
                name = att.get('name', '未命名')
                url = att.get('url', '')
                file_type = att.get('type', 'unknown').upper()
                att_classification = att.get('classification', 'other')

                # 附件分類說明
                classification_labels = {
                    'comparison_table': '對照表',
                    'amended_text': '修正條文',
                    'enacted_text': '訂定條文',
                    'explanation': '修正說明',
                    'interpretation': '函釋內容',
                    'other': '其他'
                }
                classification_label = classification_labels.get(att_classification, '其他')

                # 如果有本地檔案路徑，也顯示
                local_path = att.get('local_path')
                if local_path:
                    md_lines.append(f"{i}. **{name}** ([{file_type}]({url})) - *{classification_label}*")
                    md_lines.append(f"   - 本地路徑: `{local_path}`")
                else:
                    md_lines.append(f"{i}. **{name}** ([{file_type}]({url})) - *{classification_label}*")

            md_lines.append("")

        # ===== 分隔線 =====
        md_lines.append("---\n")

        # ===== Metadata footer (方便 RAG 檢索) =====
        footer_tags = []

        if 'date' in item:
            footer_tags.append(f"日期:{item['date']}")

        if source:
            footer_tags.append(f"來源:{source}")

        if category:
            footer_tags.append(f"類型:{category}")

        if law_name:
            footer_tags.append(f"法律:{law_name}")

        if doc_number:
            footer_tags.append(f"發文字號:{doc_number}")

        if footer_tags:
            md_lines.append(f"*標籤: {' | '.join(footer_tags)}*\n")

        return "\n".join(md_lines)

    def format_batch(self, items: List[Dict[str, Any]], add_toc: bool = True) -> str:
        """
        格式化多筆法令函釋為單一 Markdown 文件

        Args:
            items: 法令函釋資料列表
            add_toc: 是否新增目錄

        Returns:
            完整的 Markdown 文件
        """
        md_parts = []

        # 文檔標題
        md_parts.append("# 金管會法令函釋彙編\n")
        md_parts.append(f"**產生時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md_parts.append(f"**函釋數量**: {len(items)} 筆\n")
        md_parts.append("---\n")

        # 目錄 (可選)
        if add_toc and len(items) > 1:
            md_parts.append("## 📑 目錄\n")

            for i, item in enumerate(items, 1):
                title = item.get('title', '無標題')
                date = item.get('date', 'N/A')
                # Markdown 錨點 (GitHub style)
                anchor = self._create_anchor(title)
                md_parts.append(f"{i}. [{title}](#{anchor}) - {date}")

            md_parts.append("\n---\n")

        # 內容
        for i, item in enumerate(items, 1):
            logger.debug(f"格式化第 {i}/{len(items)} 筆: {item.get('title', 'N/A')[:50]}")

            # 新增序號標記
            md_parts.append(f"\n<!-- 函釋 {i}/{len(items)} -->\n")

            # 格式化單筆
            md_content = self.format_interpretation(item)
            md_parts.append(md_content)

            # 分頁符號 (除了最後一筆)
            if i < len(items):
                md_parts.append("\n\n")

        return "\n".join(md_parts)

    def _clean_content(self, text: str) -> str:
        """
        清理內容文字

        Args:
            text: 原始文字

        Returns:
            清理後的文字
        """
        # 移除過多空行
        lines = text.split('\n')
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            line = line.strip()

            # 跳過連續空行
            if not line:
                if not prev_empty:
                    cleaned_lines.append('')
                prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False

        # 移除社群分享相關文字
        filtered_lines = []
        skip_keywords = [
            'FACEBOOK', 'facebook', 'Facebook',
            'Line', 'LINE',
            'Twitter', 'TWITTER',
            '友善列印', '回上頁', '瀏覽人次', '更新日期',
            '轉寄', '列印', '分享',
            '點閱', '發布單位', '發布日期',
            ':::',  # 金管會網站的特殊分隔符
            '網站導覽', '意見信箱',
            'QRCode',
            '下載',
        ]

        for line in cleaned_lines:
            # 跳過包含任何關鍵字的行
            if any(keyword in line for keyword in skip_keywords):
                continue
            # 跳過只有標點符號的行
            if line and all(c in '.,;:!?()[]{}「」『』…─—' for c in line):
                continue
            filtered_lines.append(line)

        return '\n'.join(filtered_lines)

    def _create_anchor(self, title: str) -> str:
        """
        建立 Markdown 錨點

        Args:
            title: 標題文字

        Returns:
            錨點 ID
        """
        # GitHub Markdown 錨點規則:
        # 1. 轉小寫
        # 2. 移除標點符號
        # 3. 空格轉 -
        import re

        anchor = title.lower()
        # 移除標點符號
        anchor = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', anchor)
        # 空格轉 -
        anchor = re.sub(r'\s+', '-', anchor)

        return anchor

    def save_to_file(self, markdown: str, filepath: str):
        """
        儲存 Markdown 到檔案

        Args:
            markdown: Markdown 內容
            filepath: 檔案路徑
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown)

            logger.info(f"Markdown 已儲存: {filepath}")

        except Exception as e:
            logger.error(f"儲存 Markdown 失敗: {e}")
            raise


class BatchLawInterpretationMarkdownFormatter(LawInterpretationMarkdownFormatter):
    """批次法令函釋 Markdown 格式化器 - 依日期、來源或類型分檔"""

    def format_by_date(self, items: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        按日期分組並格式化

        Args:
            items: 法令函釋資料列表

        Returns:
            {date: markdown_content} 字典
        """
        from collections import defaultdict

        grouped = defaultdict(list)

        for item in items:
            date = item.get('date', 'unknown')
            grouped[date].append(item)

        results = {}
        for date, group_items in grouped.items():
            md = self.format_batch(group_items, add_toc=False)
            results[date] = md

        logger.info(f"按日期分組完成: {len(results)} 個檔案")
        return results

    def format_by_source(self, items: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        按來源單位分組並格式化

        Args:
            items: 法令函釋資料列表

        Returns:
            {source: markdown_content} 字典
        """
        from collections import defaultdict

        grouped = defaultdict(list)

        for item in items:
            source = 'unknown'
            if 'metadata' in item and 'source' in item['metadata']:
                source = item['metadata']['source']

            grouped[source].append(item)

        results = {}
        for source, group_items in grouped.items():
            md = self.format_batch(group_items, add_toc=True)
            results[source] = md

        logger.info(f"按來源分組完成: {len(results)} 個檔案")
        return results

    def format_by_category(self, items: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        按函釋類型分組並格式化

        Args:
            items: 法令函釋資料列表

        Returns:
            {category: markdown_content} 字典
        """
        from collections import defaultdict

        grouped = defaultdict(list)

        for item in items:
            category = 'unknown'
            if 'metadata' in item and 'category' in item['metadata']:
                category = item['metadata']['category']

            grouped[category].append(item)

        results = {}
        for category, group_items in grouped.items():
            md = self.format_batch(group_items, add_toc=True)
            results[category] = md

        logger.info(f"按函釋類型分組完成: {len(results)} 個檔案")
        return results

    def format_individual_files(
        self,
        items: List[Dict[str, Any]],
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        將每個法令函釋格式化為獨立的 Markdown 檔案
        (用於 RAG 上傳,每個函釋都有獨立且語意化的檔名)

        Args:
            items: 法令函釋資料列表
            output_dir: 輸出目錄 (預設: data/markdown/law_interpretations_individual)

        Returns:
            統計資訊 {'total_items': ..., 'created_files': ..., 'output_dir': ...}
        """
        from pathlib import Path
        import re

        # 預設輸出目錄
        if not output_dir:
            output_dir = 'data/markdown/law_interpretations_individual'

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"開始格式化法令函釋為獨立檔案...")
        logger.info(f"輸出目錄: {output_path}")

        if not items:
            logger.warning("沒有法令函釋資料")
            return {'total_items': 0, 'created_files': 0, 'output_dir': str(output_path)}

        # 來源中文映射
        source_mapping = {
            'bank_bureau': '銀行局',
            'securities_bureau': '證券期貨局',
            'insurance_bureau': '保險局',
            'examination_bureau': '檢查局',
            'fsc_main': '金管會',
            'unknown': '未分類'
        }

        # 類型簡稱映射
        category_abbr = {
            'law_amendment': '修正',
            'law_enactment': '訂定',
            'law_interpretation_decree': '函釋',
            'law_clarification': '有關',
            'law_repeal': '廢止',
            'law_publication': '公告',  # 發布/公布型（原 announcement）
            'law_approval': '核准',
            'law_adjustment': '調整',
            'law_notice': '通知'
        }

        def sanitize_filename(text: str, max_length: int = 50) -> str:
            """清理檔名,移除不合法字元"""
            # 移除或替換不合法字元
            text = re.sub(r'[<>:"/\\|?*]', '_', text)
            # 移除前後空白
            text = text.strip()
            # 限制長度
            if len(text) > max_length:
                text = text[:max_length]
            return text

        # 為每個函釋建立獨立檔案
        created_files = []

        for item in items:
            try:
                # 格式化單個函釋
                md_content = self.format_interpretation(item)

                # 建立簡潔的檔名（用於 Gemini File Search 顯示）
                item_id = item.get('id', 'unknown')
                source = item.get('metadata', {}).get('source', 'unknown')
                source_cn = source_mapping.get(source, source)
                category = item.get('metadata', {}).get('category', 'unknown')
                category_cn = category_abbr.get(category, category)

                # 單位簡稱映射（提升查詢結果可讀性）
                source_short_mapping = {
                    '銀行局': '銀',
                    '保險局': '保',
                    '證券期貨局': '證期',
                    '檢查局': '檢',
                    '金管會': '金',
                    '未分類': '其他'
                }
                source_short = source_short_mapping.get(source_cn, source_cn[:2] if source_cn else '未知')

                # 檔名格式: {ID}_{單位簡稱}_{類型}.md
                # 範例: fsc_law_20230315_0045_銀_修正.md
                filename = f"{item_id}_{source_short}_{category_cn}.md"

                # 寫入檔案
                filepath = output_path / filename
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(md_content)

                created_files.append(str(filepath))
                logger.debug(f"建立檔案: {filename}")

            except Exception as e:
                logger.error(f"格式化項目失敗: {item.get('id', 'unknown')} - {e}")
                continue

        logger.info(f"完成! 共建立 {len(created_files)} 個檔案")
        logger.info(f"輸出目錄: {output_path}")

        return {
            'total_items': len(items),
            'created_files': len(created_files),
            'output_dir': str(output_path),
            'files': created_files[:10]  # 只返回前 10 個檔案路徑作為範例
        }
