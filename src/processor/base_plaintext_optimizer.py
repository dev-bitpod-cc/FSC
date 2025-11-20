"""
通用 Plain Text 優化器基類 - 為 RAG 檢索優化

設計原則：
- 移除網頁雜訊（Facebook、Line、友善列印等）
- 最小化 metadata（只保留檢索相關資訊）
- 零重複、高語義密度
- 統一格式，易於維護

支援資料類型：
- 裁罰案件
- 法令函釋
- 重要公告
"""

from typing import Dict, Any, List
from pathlib import Path
from loguru import logger
from abc import ABC, abstractmethod


class BasePlainTextOptimizer(ABC):
    """Plain Text 優化器抽象基類"""

    def __init__(self):
        """初始化格式化器"""
        # 通用網頁雜訊關鍵字
        self.noise_keywords = [
            'FACEBOOK', 'facebook',
            'Line', 'line',
            'Twitter', 'twitter',
            '友善列印', '列印',
            '回上頁', '上一頁',
            '瀏覽人次', '點閱數',
            '更新日期',
            '分享至',
            'Share',
            'Print'
        ]

    @abstractmethod
    def format_metadata(self, item: Dict[str, Any]) -> List[str]:
        """
        格式化 metadata 部分（需由子類實作）

        Args:
            item: 資料項目

        Returns:
            metadata 文字行列表
        """
        pass

    def format_item(self, item: Dict[str, Any]) -> str:
        """
        格式化單筆資料為優化的 Plain Text

        Args:
            item: 資料項目

        Returns:
            優化的 Plain Text
        """
        lines = []

        # 1. Metadata（由子類實作）
        metadata_lines = self.format_metadata(item)
        if metadata_lines:
            lines.extend(metadata_lines)
            lines.append("")
            lines.append("---")
            lines.append("")

        # 2. 主要內容（清理後）
        if 'content' in item:
            content = item['content']

            if isinstance(content, dict) and 'text' in content:
                text = content['text'].strip()
                if text:
                    cleaned_text = self._clean_content(text)
                    lines.append(cleaned_text)

        return "\n".join(lines)

    def _clean_content(self, text: str) -> str:
        """
        清理內容文字，移除網頁雜訊

        Args:
            text: 原始文字

        Returns:
            清理後的文字
        """
        lines = text.split('\n')
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            line = line.strip()

            # 跳過空行（但保留一個）
            if not line:
                if not prev_empty:
                    cleaned_lines.append('')
                prev_empty = True
                continue

            # 跳過包含雜訊關鍵字的行
            if self._is_noise_line(line):
                continue

            # 跳過單一字元或過短的行（可能是導航元素）
            if len(line) <= 2:
                continue

            cleaned_lines.append(line)
            prev_empty = False

        return '\n'.join(cleaned_lines)

    def _is_noise_line(self, line: str) -> bool:
        """
        判斷是否為雜訊行

        Args:
            line: 單行文字

        Returns:
            True if 是雜訊行
        """
        return any(keyword in line for keyword in self.noise_keywords)

    def format_batch(
        self,
        items: List[Dict[str, Any]],
        output_dir: str
    ) -> Dict[str, Any]:
        """
        批次格式化為優化的 Plain Text 檔案

        Args:
            items: 資料列表
            output_dir: 輸出目錄

        Returns:
            統計資訊
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"開始格式化為優化 Plain Text 檔案...")
        logger.info(f"輸出目錄: {output_path}")

        if not items:
            logger.warning("沒有資料")
            return {'total_items': 0, 'created_files': 0, 'output_dir': str(output_path)}

        created_files = []

        for item in items:
            try:
                # 格式化單個項目
                plain_text = self.format_item(item)

                # 建立檔名
                item_id = item.get('id', 'unknown')
                filename = f"{item_id}.txt"

                # 寫入檔案
                filepath = output_path / filename
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(plain_text)

                created_files.append(str(filepath))
                logger.debug(f"建立檔案: {filename}")

            except Exception as e:
                logger.error(f"格式化項目失敗: {item.get('id', 'unknown')} - {e}")
                continue

        logger.info(f"完成! 共建立 {len(created_files)} 個優化 Plain Text 檔案")

        # 統計檔案大小
        total_size = sum(Path(f).stat().st_size for f in created_files)
        avg_size = total_size / len(created_files) if created_files else 0

        logger.info(f"總大小: {total_size / 1024:.2f} KB")
        logger.info(f"平均大小: {avg_size / 1024:.2f} KB")

        return {
            'total_items': len(items),
            'created_files': len(created_files),
            'output_dir': str(output_path),
            'total_size_kb': total_size / 1024,
            'avg_size_kb': avg_size / 1024,
            'files': created_files[:10]
        }
