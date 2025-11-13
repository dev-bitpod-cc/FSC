"""輔助函數模組"""

import re
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse


def generate_id(source: str, date: str, index: int) -> str:
    """
    生成唯一 ID

    Args:
        source: 資料來源 (announcements, laws, penalties)
        date: 日期 (YYYY-MM-DD)
        index: 索引編號

    Returns:
        唯一 ID (例如: fsc_ann_20251112_001)
    """
    date_str = date.replace('-', '')
    source_abbr = {
        'announcements': 'ann',
        'laws': 'law',
        'penalties': 'pen'
    }.get(source, 'unk')

    return f"fsc_{source_abbr}_{date_str}_{index:04d}"


def generate_hash(content: str) -> str:
    """
    生成內容 hash (用於去重)

    Args:
        content: 內容文字

    Returns:
        SHA256 hash
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def clean_text(text: str) -> str:
    """
    清理文字

    Args:
        text: 原始文字

    Returns:
        清理後的文字
    """
    if not text:
        return ""

    # 移除多餘空白
    text = re.sub(r'\s+', ' ', text)

    # 移除前後空白
    text = text.strip()

    return text


def parse_date(date_str: str) -> Optional[str]:
    """
    解析日期字串為標準格式

    Args:
        date_str: 日期字串 (支援多種格式)

    Returns:
        標準格式日期 (YYYY-MM-DD) 或 None
    """
    if not date_str:
        return None

    # 常見日期格式
    formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y.%m.%d',
        '%Y年%m月%d日',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return None


def normalize_url(url: str, base_url: str = None) -> str:
    """
    標準化 URL

    Args:
        url: 原始 URL
        base_url: 基礎 URL (用於相對路徑)

    Returns:
        完整的 URL
    """
    if not url:
        return ""

    # 如果是完整 URL,直接返回
    if url.startswith('http://') or url.startswith('https://'):
        return url

    # 如果是相對路徑,結合基礎 URL
    if base_url:
        return urljoin(base_url, url)

    return url


def detect_category(title: str, category_mapping: Dict[str, str]) -> Optional[str]:
    """
    從標題偵測公告類型

    Args:
        title: 公告標題
        category_mapping: 類型對應表

    Returns:
        公告類型代碼
    """
    for keyword, category in category_mapping.items():
        if keyword in title:
            return category

    return None


def format_file_size(size_bytes: int) -> str:
    """
    格式化檔案大小

    Args:
        size_bytes: 位元組數

    Returns:
        人類可讀的大小 (例如: 1.5 MB)
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0

    return f"{size_bytes:.1f} TB"


def extract_announcement_number(text: str) -> Optional[str]:
    """
    從文字中提取公告文號

    Args:
        text: 文字內容

    Returns:
        公告文號 (例如: 金管證發字第1140385140號)
    """
    # 常見公告文號格式
    patterns = [
        r'金管[^字]+字第\d+號',
        r'金管會[^字]+字第\d+號',
        r'[A-Z]+字第\d+號',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)

    return None


def extract_penalty_amount(text: str) -> tuple[Optional[int], Optional[str]]:
    """
    從文字中提取處分金額

    Args:
        text: 文字內容

    Returns:
        (金額數值, 金額文字)
        例如: (3000000, "新臺幣300萬元")
    """
    # 匹配模式：新臺幣XXX萬元、新臺幣XXX元
    patterns = [
        r'新臺幣(\d+)萬元',
        r'新台幣(\d+)萬元',
        r'新臺幣(\d+)元',
        r'新台幣(\d+)元',
        r'罰鍰[^\d]*(\d+)萬元',
        r'罰鍰[^\d]*(\d+)元',
    ]

    for i, pattern in enumerate(patterns):
        match = re.search(pattern, text)
        if match:
            amount_str = match.group(1)
            amount = int(amount_str)

            # 如果是萬元，轉換為元
            if '萬元' in match.group(0):
                amount = amount * 10000

            return amount, match.group(0)

    return None, None


def extract_legal_basis(text: str) -> list[str]:
    """
    從文字中提取法條依據

    Args:
        text: 文字內容

    Returns:
        法條清單
        例如: ["保險法第171條之1第4項", "保險法第148條之3第1項"]
    """
    legal_basis = []

    # 匹配模式：XXX法第XXX條
    patterns = [
        r'[^。，\n]+法第\d+條[^。，\n]*',
        r'[^。，\n]+辦法第\d+條[^。，\n]*',
        r'[^。，\n]+規則第\d+條[^。，\n]*',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # 清理文字
            cleaned = match.strip()
            # 避免重複
            if cleaned and cleaned not in legal_basis:
                legal_basis.append(cleaned)

    return legal_basis


def extract_inspection_report_number(text: str) -> Optional[str]:
    """
    從文字中提取檢查報告編號

    Args:
        text: 文字內容

    Returns:
        檢查報告編號
        例如: "112I018"
    """
    # 匹配模式：（編號：112I018）或 編號：112I018
    patterns = [
        r'編號[：:]\s*([A-Z0-9]+)',
        r'[（(]編號[：:]\s*([A-Z0-9]+)[）)]',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    return None


def detect_penalty_category(title: str, content: str, category_mapping: Dict[str, str]) -> str:
    """
    偵測裁罰案件違規類型

    Args:
        title: 標題
        content: 內容
        category_mapping: 類型映射字典

    Returns:
        違規類型標準名稱
    """
    # 合併標題和內容（只取前1000字元以提升效率）
    text = f"{title} {content[:1000]}"

    # 檢查關鍵字
    for keyword, category in category_mapping.items():
        if keyword in text:
            return category

    return 'other'


def extract_penalized_entity_type(source: str, title: str) -> str:
    """
    推斷被處分人的業別類型

    Args:
        source: 資料來源（如「保險局」）
        title: 標題

    Returns:
        業別類型: insurance, bank, securities, other
    """
    # 根據來源判斷
    if '保險' in source:
        return 'insurance'
    elif '銀行' in source:
        return 'bank'
    elif '證期' in source or '證券' in source:
        return 'securities'

    # 根據標題判斷
    if any(keyword in title for keyword in ['保險', '壽險', '產險']):
        return 'insurance'
    elif any(keyword in title for keyword in ['銀行', '商業銀行', '信用合作社']):
        return 'bank'
    elif any(keyword in title for keyword in ['證券', '期貨', '投信', '投顧']):
        return 'securities'

    return 'other'
