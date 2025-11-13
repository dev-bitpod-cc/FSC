"""Markdown 格式化器 - 將爬蟲資料轉換為 Gemini 友善的 Markdown 格式"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from .version_tracker import VersionTracker


class MarkdownFormatter:
    """Markdown 格式化器"""

    def __init__(self, version_tracker: Optional[VersionTracker] = None):
        """
        初始化格式化器

        Args:
            version_tracker: 版本追蹤器（用於時效性標註）
        """
        self.version_tracker = version_tracker
        self.category_names = {
            'amendment': '法規修正',
            'regulation': '法規發布',
            'announcement': '一般公告',
            'penalty': '裁罰案件',
            'press_release': '新聞稿',
            'market_info': '市場資訊',
            'other': '其他'
        }

        self.source_names = {
            'fsc_main': '金管會本會',
            'bank_bureau': '銀行局',
            'securities_bureau': '證券期貨局',
            'insurance_bureau': '保險局',
            'examination_bureau': '檢查局',
            'unknown': '未分類'
        }

    def format_announcement(self, item: Dict[str, Any]) -> str:
        """
        格式化單筆公告為 Markdown

        Args:
            item: 公告資料

        Returns:
            Markdown 格式的文字
        """
        md_lines = []

        # 標題
        title = item.get('title', '無標題')
        md_lines.append(f"# {title}\n")

        # 時效性標註（如果有 version_tracker）
        if self.version_tracker:
            version_info = self.version_tracker.get_version_info(item)

            if version_info['is_latest']:
                date = item.get('date', '')
                md_lines.append(f"⭐ **最新版本**（{date}）\n")
            elif version_info['is_superseded']:
                md_lines.append(f"⚠️ **此版本已過時** - 請參考最新版本\n")

        # Metadata 區塊
        md_lines.append("## 📋 基本資訊\n")

        # ID
        if 'id' in item:
            md_lines.append(f"- **文件編號**: `{item['id']}`")

        # 日期
        if 'date' in item:
            md_lines.append(f"- **發布日期**: {item['date']}")

        # 來源單位
        source_raw = item.get('source_raw', '')
        if source_raw:
            md_lines.append(f"- **來源單位**: {source_raw}")

        # 標準化來源
        if 'metadata' in item and 'source' in item['metadata']:
            source = item['metadata']['source']
            source_name = self.source_names.get(source, source)
            md_lines.append(f"- **單位代碼**: {source_name}")

        # 公告類型
        if 'metadata' in item and 'category' in item['metadata']:
            category = item['metadata']['category']
            if category:
                category_name = self.category_names.get(category, category)
                md_lines.append(f"- **公告類型**: {category_name}")

        # 公告文號
        if 'metadata' in item and 'announcement_number' in item['metadata']:
            ann_number = item['metadata']['announcement_number']
            if ann_number:
                md_lines.append(f"- **公告文號**: {ann_number}")

        # 原始連結
        if 'detail_url' in item:
            md_lines.append(f"- **原始連結**: {item['detail_url']}")

        md_lines.append("")  # 空行

        # 內容區塊
        if 'content' in item:
            content = item['content']

            if isinstance(content, dict) and 'text' in content:
                text = content['text'].strip()
                if text:
                    md_lines.append("## 📄 內容\n")
                    # 清理內容
                    text = self._clean_content(text)
                    md_lines.append(text)
                    md_lines.append("")

        # 修正歷程區塊（如果有版本資訊）
        if self.version_tracker:
            version_info = self.version_tracker.get_version_info(item)

            if version_info['regulation_name'] and version_info['total_versions'] > 1:
                md_lines.append("## 📜 修正歷程\n")

                history = version_info['version_history']
                for i, version in enumerate(history):
                    date = version['date']
                    is_current = (version['id'] == item.get('id'))

                    if i == 0:  # 最新版本
                        if is_current:
                            md_lines.append(f"- **{date}**：最新修正（本文件）⭐")
                        else:
                            md_lines.append(f"- **{date}**：最新修正")
                    else:
                        if is_current:
                            md_lines.append(f"- {date}：本次修正（已由最新版本取代）")
                        else:
                            md_lines.append(f"- {date}：前次修正")

                md_lines.append("")

                # 加入提示
                if version_info['is_latest']:
                    md_lines.append("*本文件為最新有效版本，取代所有先前版本。*\n")
                elif version_info['is_superseded']:
                    md_lines.append("*本文件已被新版本取代，建議參考最新版本。*\n")

        # 附件區塊
        if 'attachments' in item and item['attachments']:
            attachments = item['attachments']
            md_lines.append("## 📎 相關附件\n")

            for i, att in enumerate(attachments, 1):
                name = att.get('name', '未命名')
                url = att.get('url', '')
                file_type = att.get('type', 'unknown').upper()

                md_lines.append(f"{i}. **{name}** ([{file_type}]({url}))")

            md_lines.append("")

        # 分隔線
        md_lines.append("---\n")

        # Metadata footer (方便 RAG 檢索)
        footer_tags = []
        if 'date' in item:
            footer_tags.append(f"日期:{item['date']}")
        if 'metadata' in item and 'source' in item['metadata']:
            footer_tags.append(f"來源:{item['metadata']['source']}")
        if 'metadata' in item and 'category' in item['metadata'] and item['metadata']['category']:
            footer_tags.append(f"類型:{item['metadata']['category']}")

        if footer_tags:
            md_lines.append(f"*標籤: {' | '.join(footer_tags)}*\n")

        return "\n".join(md_lines)

    def format_batch(self, items: List[Dict[str, Any]], add_toc: bool = True) -> str:
        """
        格式化多筆公告為單一 Markdown 文件

        Args:
            items: 公告資料列表
            add_toc: 是否新增目錄

        Returns:
            完整的 Markdown 文件
        """
        md_parts = []

        # 文檔標題
        md_parts.append("# 金管會重要公告彙編\n")
        md_parts.append(f"**產生時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md_parts.append(f"**文件數量**: {len(items)} 筆\n")
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
            md_parts.append(f"\n<!-- 文件 {i}/{len(items)} -->\n")

            # 格式化單筆
            md_content = self.format_announcement(item)
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
        skip_keywords = ['FACEBOOK', 'Line', 'Twitter', '友善列印', '回上頁', '瀏覽人次', '更新日期']

        for line in cleaned_lines:
            if not any(keyword in line for keyword in skip_keywords):
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


class BatchMarkdownFormatter(MarkdownFormatter):
    """批次 Markdown 格式化器 - 依日期或來源分檔"""

    def format_by_date(self, items: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        按日期分組並格式化

        Args:
            items: 公告資料列表

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
            items: 公告資料列表

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

    def format_individual_files(
        self,
        data_type: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        將每篇公告格式化為獨立的 Markdown 檔案
        (推薦用於 RAG 上傳,每篇公告都有獨立且語意化的檔名)

        Args:
            data_type: 資料類型 (announcements, laws, penalties)
            output_dir: 輸出目錄 (預設: data/markdown/individual)

        Returns:
            統計資訊 {'total_items': ..., 'created_files': ..., 'output_dir': ...}
        """
        from pathlib import Path
        import re

        # 預設輸出目錄
        if not output_dir:
            output_dir = f'data/markdown/individual'

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"開始格式化 {data_type} 為獨立檔案...")
        logger.info(f"輸出目錄: {output_path}")

        # 讀取資料
        items = self.handler.read_all(data_type)

        if not items:
            logger.warning(f"沒有找到 {data_type} 資料")
            return {'total_items': 0, 'created_files': 0, 'output_dir': str(output_path)}

        # 來源中文映射
        source_mapping = {
            'bank_bureau': '銀行局',
            'securities_bureau': '證券期貨局',
            'insurance_bureau': '保險局',
            'inspection_bureau': '檢查局',
            'unknown': '未分類'
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

        # 為每篇公告建立獨立檔案
        created_files = []

        for item in items:
            try:
                # 格式化單篇公告
                md_content = self.format_announcement(item)

                # 建立簡潔的檔名（用於 Gemini File Search 顯示）
                item_id = item.get('id', 'unknown')
                source = item.get('metadata', {}).get('source', 'unknown')
                source_cn = source_mapping.get(source, source)

                # 單位簡稱映射（提升查詢結果可讀性）
                source_abbr = {
                    '銀行局': '銀',
                    '保險局': '保',
                    '證券期貨局': '證期',
                    '檢查局': '檢',
                    '未分類': '其他'
                }
                source_short = source_abbr.get(source_cn, source_cn[:2] if source_cn else '未知')

                # 檔名格式: {ID}_{單位簡稱}.md
                # 範例: fsc_ann_20250508_0001_證期.md
                filename = f"{item_id}_{source_short}.md"

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
