"""
裁罰案件 Plain Text 格式化器 - 移除網頁雜訊,生成乾淨的純文字

用於 Gemini File Search RAG,相比 Markdown 格式有以下優勢:
- 零重複內容
- 語義密度更高
- 向量化效果更好
- 檔案大小更小 (約減少 50%)
"""

from typing import Dict, Any, List
from pathlib import Path
from loguru import logger


class PenaltyPlainTextFormatter:
    """裁罰案件 Plain Text 格式化器 - 專為 RAG 優化"""

    def __init__(self):
        """初始化格式化器"""
        # 網頁雜訊關鍵字 (會被移除)
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

    def format_penalty(self, item: Dict[str, Any]) -> str:
        """
        格式化單筆裁罰案件為 Plain Text

        Args:
            item: 裁罰案件資料

        Returns:
            Plain Text 格式的文字
        """
        lines = []

        # ===== 元資料區 (純文字格式) =====
        lines.append("=" * 80)
        lines.append("金管會裁罰案件")
        lines.append("=" * 80)
        lines.append("")

        # 文件編號
        if 'id' in item:
            lines.append(f"文件編號: {item['id']}")

        # 發布日期
        if 'date' in item:
            lines.append(f"發布日期: {item['date']}")

        # 來源單位
        source_raw = item.get('source_raw', '')
        if source_raw:
            lines.append(f"來源單位: {source_raw}")

        # 提取 metadata
        metadata = item.get('metadata', {})

        # 發文字號
        doc_number = metadata.get('doc_number')
        if doc_number:
            lines.append(f"發文字號: {doc_number}")

        # 被處分人
        penalized_entity = metadata.get('penalized_entity', {})
        if penalized_entity and penalized_entity.get('name'):
            lines.append(f"被處分人: {penalized_entity['name']}")

        # 處分金額
        penalty_amount = metadata.get('penalty_amount')
        penalty_amount_text = metadata.get('penalty_amount_text')

        if penalty_amount_text:
            lines.append(f"處分金額: {penalty_amount_text}")
        elif penalty_amount:
            formatted_amount = f"{penalty_amount:,}"
            lines.append(f"處分金額: 新臺幣 {formatted_amount} 元")

        # 原始連結
        if 'detail_url' in item:
            lines.append(f"原始連結: {item['detail_url']}")

        lines.append("")
        lines.append("-" * 80)
        lines.append("裁處書內容")
        lines.append("-" * 80)
        lines.append("")

        # ===== 裁處書完整內容 (清理後) =====
        if 'content' in item:
            content = item['content']

            if isinstance(content, dict) and 'text' in content:
                text = content['text'].strip()
                if text:
                    # 清理網頁雜訊
                    cleaned_text = self._clean_content(text)
                    lines.append(cleaned_text)
                    lines.append("")

        # ===== 附件資訊 (如果有相關附件) =====
        attachments = item.get('attachments', [])

        # 過濾掉不相關的通用附件
        irrelevant_attachments = [
            '失智者經濟安全保障推動計畫',
            '金管會永續發展目標自願檢視報告'
        ]

        relevant_attachments = [
            att for att in attachments
            if att.get('name', '') not in irrelevant_attachments
        ]

        if relevant_attachments:
            lines.append("-" * 80)
            lines.append("相關附件")
            lines.append("-" * 80)
            lines.append("")

            for i, att in enumerate(relevant_attachments, 1):
                name = att.get('name', '未命名')
                url = att.get('url', '')
                file_type = att.get('type', 'unknown').upper()

                lines.append(f"{i}. {name} ({file_type})")
                lines.append(f"   連結: {url}")

            lines.append("")

        # ===== 結尾分隔線 =====
        lines.append("=" * 80)
        lines.append("")

        return "\n".join(lines)

    def _clean_content(self, text: str) -> str:
        """
        清理內容文字,移除網頁雜訊

        Args:
            text: 原始文字

        Returns:
            清理後的文字
        """
        # 分行處理
        lines = text.split('\n')
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            line = line.strip()

            # 跳過空行 (但保留一個)
            if not line:
                if not prev_empty:
                    cleaned_lines.append('')
                prev_empty = True
                continue

            # 跳過包含雜訊關鍵字的行
            if self._is_noise_line(line):
                continue

            # 跳過單一字元或過短的行 (可能是導航元素)
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
        output_dir: str = 'data/plaintext/penalties_individual'
    ) -> Dict[str, Any]:
        """
        批次格式化裁罰案件為獨立的 Plain Text 檔案

        Args:
            items: 裁罰案件資料列表
            output_dir: 輸出目錄

        Returns:
            統計資訊 {'total_items': ..., 'created_files': ..., 'output_dir': ...}
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"開始格式化裁罰案件為 Plain Text 檔案...")
        logger.info(f"輸出目錄: {output_path}")

        if not items:
            logger.warning("沒有裁罰案件資料")
            return {'total_items': 0, 'created_files': 0, 'output_dir': str(output_path)}

        created_files = []

        for item in items:
            try:
                # 格式化單個案件
                plain_text = self.format_penalty(item)

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

        logger.info(f"完成! 共建立 {len(created_files)} 個 Plain Text 檔案")
        logger.info(f"輸出目錄: {output_path}")

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
            'files': created_files[:10]  # 前 10 個檔案作為範例
        }


# ===== 便捷函數 =====

def format_penalties_to_plaintext(
    jsonl_file: str = 'data/penalties_test/test_penalties.jsonl',
    output_dir: str = 'data/plaintext/penalties_individual'
) -> Dict[str, Any]:
    """
    從 JSONL 檔案讀取裁罰案件並格式化為 Plain Text

    Args:
        jsonl_file: JSONL 檔案路徑
        output_dir: 輸出目錄

    Returns:
        統計資訊
    """
    import json

    logger.info(f"讀取 JSONL: {jsonl_file}")

    items = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    logger.info(f"讀取 {len(items)} 筆案件")

    formatter = PenaltyPlainTextFormatter()
    return formatter.format_batch(items, output_dir)


if __name__ == '__main__':
    # 測試
    from loguru import logger

    logger.add(
        "logs/plaintext_formatter.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG"
    )

    # 格式化測試資料
    stats = format_penalties_to_plaintext()

    print("\n" + "=" * 80)
    print("Plain Text 格式化完成!")
    print("=" * 80)
    print(f"總案件數: {stats['total_items']}")
    print(f"成功建立: {stats['created_files']} 個檔案")
    print(f"輸出目錄: {stats['output_dir']}")
    print(f"總大小: {stats['total_size_kb']:.2f} KB")
    print(f"平均大小: {stats['avg_size_kb']:.2f} KB")

    if stats['files']:
        print("\n範例檔案:")
        for f in stats['files'][:3]:
            print(f"  - {f}")
