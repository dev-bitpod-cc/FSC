"""
法條連結生成工具

將法條文字（如「銀行法第61條」）轉換為法規資料庫的連結
"""

import re
from typing import Optional, Dict


# 法律名稱到 PCode 的映射表
LAW_PCODE_MAPPING = {
    # 銀行相關
    '銀行法': 'G0380001',
    '金融控股公司法': 'G0380112',
    '國際金融業務條例': 'G0380037',

    # 保險相關
    '保險法': 'G0390002',
    '保險法施行細則': 'G0390003',
    '強制汽車責任保險法': 'G0390060',

    # 證券相關
    '證券交易法': 'G0400001',
    '證券交易法施行細則': 'G0400002',
    '證券投資信託及顧問法': 'G0400121',

    # 期貨相關
    '期貨交易法': 'G0400035',

    # 信託相關
    '信託法': 'I0020020',
    '信託業法': 'G0380055',

    # 其他金融法規
    '金融消費者保護法': 'G0380226',
    '洗錢防制法': 'I0030023',
    '資恐防制法': 'I0030033',
    '票券金融管理法': 'G0380031',
    '信用合作社法': 'G0380002',
    '農業金融法': 'M0090005',
    '電子票證發行管理條例': 'G0380239',
    '電子支付機構管理條例': 'G0380273',

    # 通用法規
    '公司法': 'J0080001',
    '民法': 'B0000001',
    '刑法': 'C0000001',
    '行政罰法': 'A0030210',
    '個人資料保護法': 'I0050021',
    '臺灣地區與大陸地區人民關係條例': 'Q0010001',
}


def parse_law_article(law_text: str) -> Optional[Dict[str, str]]:
    """
    解析法條文字

    支援格式：
    - 銀行法第61條
    - 保險法第149條第1項
    - 證券交易法第66條之1
    - 金融控股公司法第57條第2項第1款
    - 保險法第143條之6第2款第1目

    Args:
        law_text: 法條文字

    Returns:
        包含 law_name, article, paragraph, subparagraph, point 的字典，如果無法解析則返回 None
    """
    # 正則表達式：法律名稱 + 第X條 + (可選：之X) + (可選：第X項) + (可選：第X款) + (可選：第X目)
    # 支援「法」和「條例」結尾的法規名稱（包含民法、刑法等單字法規）
    pattern = r'([a-zA-Z\u4e00-\u9fff]{1,30}(?:法|條例)(?:施行細則)?)\s*第\s*(\d+)\s*條(?:\s*之\s*(\d+))?(?:\s*第\s*(\d+)\s*項)?(?:\s*第\s*(\d+)\s*款)?(?:\s*第\s*(\d+)\s*目)?'

    match = re.match(pattern, law_text.strip())

    if not match:
        return None

    law_name = match.group(1)
    article = match.group(2)
    sub_article = match.group(3)  # 之X
    paragraph = match.group(4)     # 第X項
    subparagraph = match.group(5)  # 第X款
    point = match.group(6)         # 第X目

    return {
        'law_name': law_name,
        'article': article,
        'sub_article': sub_article,
        'paragraph': paragraph,
        'subparagraph': subparagraph,
        'point': point
    }


def generate_law_url(law_text: str) -> Optional[str]:
    """
    生成法條的法規資料庫連結

    Args:
        law_text: 法條文字（如「銀行法第61條」）

    Returns:
        法規資料庫 URL，如果無法生成則返回 None
    """
    parsed = parse_law_article(law_text)

    if not parsed:
        return None

    law_name = parsed['law_name']
    pcode = LAW_PCODE_MAPPING.get(law_name)

    if not pcode:
        # 如果找不到 PCode，返回搜尋頁面
        return f"https://law.moj.gov.tw/LawClass/LawSearchContent.aspx?kw={law_name}"

    # 組合條號
    article_number = parsed['article']
    if parsed['sub_article']:
        article_number += f"-{parsed['sub_article']}"

    # 生成 URL（單一條文頁面）
    url = f"https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode={pcode}&flno={article_number}"

    return url


def generate_law_urls_from_list(law_texts: list) -> Dict[str, str]:
    """
    批次生成法條連結

    Args:
        law_texts: 法條文字列表

    Returns:
        {法條文字: URL} 的字典
    """
    result = {}

    for law_text in law_texts:
        url = generate_law_url(law_text)
        if url:
            result[law_text] = url

    return result


def get_supported_laws() -> list:
    """
    取得支援的法律列表

    Returns:
        支援的法律名稱列表
    """
    return list(LAW_PCODE_MAPPING.keys())


# 測試用例
if __name__ == '__main__':
    test_cases = [
        '銀行法第61條',
        '保險法第149條第1項',
        '證券交易法第66條',
        '金融控股公司法第57條第2項第1款',
        '證券交易法第171條之1',
        '洗錢防制法第15條',
        '不存在的法律第1條',
    ]

    print("=" * 80)
    print("法條連結生成工具測試")
    print("=" * 80)

    for law_text in test_cases:
        url = generate_law_url(law_text)
        print(f"\n法條: {law_text}")
        print(f"連結: {url if url else '(無法生成)'}")

    print("\n" + "=" * 80)
    print(f"支援的法律數量: {len(LAW_PCODE_MAPPING)}")
    print("=" * 80)
