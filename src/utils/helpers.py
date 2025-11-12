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
