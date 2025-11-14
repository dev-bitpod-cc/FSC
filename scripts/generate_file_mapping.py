"""生成增強型檔案映射檔

此腳本從 raw.jsonl 生成完整的檔案映射，包含：
- display_name: 顯示名稱
- original_url: 原始網頁連結
- date: 日期
- institution: 受罰機構
- original_content: 原始內容（純文字和HTML）
- applicable_laws: 提取的法條列表
- law_links: 法條到法規資料庫的連結映射
- attachments: 附件列表
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any

# 加入專案根目錄到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.storage.jsonl_handler import JSONLHandler
from src.utils.law_link_generator import generate_law_urls_from_list


def extract_applicable_laws(content_text: str) -> List[str]:
    """
    從內容中提取適用法條（僅提取核心違規法規）

    常見法條格式：
    - 銀行法第61條
    - 保險法第149條第1項
    - 證券交易法第66條之1
    - 金融控股公司法第57條第2項第1款

    優化策略：
    1. 只提取違規相關法條（有「違反」等關鍵字）
    2. 過濾程序性法規（訴願法、行政執行法）
    3. 去重（避免同一法條重複出現）

    Args:
        content_text: 內容文字

    Returns:
        法條列表（去重排序）
    """
    # 程序性法規黑名單（不列入違規法規）
    PROCEDURAL_LAWS = {
        '訴願法',           # 救濟程序
        '行政執行法',       # 執行程序
        '行政程序法',       # 行政程序
        '行政罰法',         # 行政罰則（通用規定）
    }

    laws = set()  # 使用 set 自動去重

    # 策略1: 優先提取明確標示違反的法條
    # 例如：「違反銀行法第45條」、「核有違反保險法第149條」
    violation_patterns = [
        r'違反.*?([a-zA-Z\u4e00-\u9fff]{2,15}法)第(\d+)條(?:之(\d+))?(?:第(\d+)項)?(?:第(\d+)款)?',
        r'核.*?違反.*?([a-zA-Z\u4e00-\u9fff]{2,15}法)第(\d+)條(?:之(\d+))?(?:第(\d+)項)?(?:第(\d+)款)?',
    ]

    for pattern in violation_patterns:
        matches = re.finditer(pattern, content_text)
        for match in matches:
            law_name = match.group(1)

            # 過濾程序性法規
            if law_name in PROCEDURAL_LAWS:
                continue

            # 移除法名中的前綴詞
            law_name = re.sub(r'^(依|核|核已|核有|已|有|與|分別為|應依|爰依|按|惟|同)', '', law_name)

            # 過濾掉無效法名（如「同法」、「本法」）
            if law_name in ['法', '同法', '本法']:
                continue

            # 重建法條文字（純淨格式）
            law_text = law_name + '第' + match.group(2) + '條'
            if match.group(3):  # 之X
                law_text += '之' + match.group(3)
            if match.group(4):  # 第X項
                law_text += '第' + match.group(4) + '項'
            if match.group(5):  # 第X款
                law_text += '第' + match.group(5) + '款'

            laws.add(law_text)

    # 策略2: 如果沒找到違反相關的，才提取裁罰依據
    # 例如：「依銀行法第129條」、「爰依保險法第171條」
    if not laws:
        penalty_patterns = [
            r'依.*?([a-zA-Z\u4e00-\u9fff]{2,15}法)第(\d+)條(?:之(\d+))?(?:第(\d+)項)?(?:第(\d+)款)?.*?(?:處|核處|罰鍰)',
            r'爰依.*?([a-zA-Z\u4e00-\u9fff]{2,15}法)第(\d+)條(?:之(\d+))?(?:第(\d+)項)?(?:第(\d+)款)?',
        ]

        for pattern in penalty_patterns:
            matches = re.finditer(pattern, content_text)
            for match in matches:
                law_name = match.group(1)

                # 過濾程序性法規
                if law_name in PROCEDURAL_LAWS:
                    continue

                # 移除法名中的前綴詞
                law_name = re.sub(r'^(依|核|核已|核有|已|有|與|分別為|應依|爰依|按|惟|同)', '', law_name)

                # 過濾掉無效法名（如「同法」、「本法」）
                if law_name in ['法', '同法', '本法']:
                    continue

                # 重建法條文字（純淨格式）
                law_text = law_name + '第' + match.group(2) + '條'
                if match.group(3):  # 之X
                    law_text += '之' + match.group(3)
                if match.group(4):  # 第X項
                    law_text += '第' + match.group(4) + '項'
                if match.group(5):  # 第X款
                    law_text += '第' + match.group(5) + '款'

                laws.add(law_text)

    # 排序並返回列表
    return sorted(list(laws))


def extract_institution_from_title(title: str) -> str:
    """
    從標題中提取機構名稱

    標題格式通常是：[機構名稱] + [動詞/分隔詞] + [違規事項...]
    例如：
    - "三商美邦人壽因113年底自有資本..." → "三商美邦人壽"
    - "國泰世華商業銀行客服專員涉及..." → "國泰世華銀行"
    - "明台產物保險股份有限公司辦理..." → "明台產險"

    Args:
        title: 標題文字

    Returns:
        機構名稱（簡化）
    """
    if not title:
        return '未知機構'

    # 分隔詞（機構名稱後通常接這些詞）
    separators = [
        '因', '辦理', '經營', '涉及', '所涉', '客服', '催收',
        '未依', '未於', '未經', '未能', '違反', '核有', '經',
        '於民國', '從事', '受託', '自', '前於'
    ]

    # 找到第一個分隔詞的位置
    institution = title
    min_pos = len(title)

    for sep in separators:
        pos = title.find(sep)
        if pos > 0 and pos < min_pos:  # 必須在開頭之後找到
            min_pos = pos

    if min_pos < len(title):
        institution = title[:min_pos]
    else:
        # 如果找不到分隔詞，取前50個字
        institution = title[:50]

    # 簡化機構名稱（移除常見後綴）
    simplifications = [
        ('股份有限公司', ''),
        ('有限公司', ''),
        ('商業銀行', '銀行'),
        ('產物保險', '產險'),
        ('人壽保險', '人壽'),
        ('證券投資信託', '投信'),
        ('證券投資顧問', '投顧'),
        ('證券金融', '證金'),
        ('期貨', '期貨'),
    ]

    for old, new in simplifications:
        institution = institution.replace(old, new)

    # 清理空白
    institution = institution.strip()

    # 如果太短或為空，返回未知
    if len(institution) < 2:
        return '未知機構'

    return institution


def generate_display_name(item: Dict[str, Any]) -> str:
    """
    生成顯示名稱

    格式: {日期}_{來源單位}_{受罰機構}
    例如: 2025-07-31_保險局_三商美邦人壽

    Args:
        item: 裁罰案件資料

    Returns:
        顯示名稱
    """
    date = item.get('date', '')
    source_raw = item.get('source_raw', '')

    # 從 institution 欄位或 title 提取機構名稱
    institution = item.get('institution', '').strip()
    if not institution:
        # 如果 institution 為空，從 title 提取
        title = item.get('title', '')
        institution = extract_institution_from_title(title)

    # 來源單位映射（轉換為簡短名稱）
    source_mapping = {
        '銀行局': '銀行局',
        '保險局': '保險局',
        '證券期貨局': '證期局',
        '檢查局': '檢查局',
    }

    # 查找匹配的來源單位
    source = '未知'
    for key, value in source_mapping.items():
        if key in source_raw:
            source = value
            break

    # 組合顯示名稱
    if date:
        return f"{date}_{source}_{institution}"
    else:
        return f"{source}_{institution}"


def generate_file_mapping(source: str = 'penalties') -> Dict[str, Any]:
    """
    生成檔案映射

    Args:
        source: 資料源名稱（預設: penalties）

    Returns:
        檔案映射字典
    """
    logger.info("=" * 80)
    logger.info("生成增強型檔案映射")
    logger.info("=" * 80)

    # 讀取資料
    logger.info(f"\n[1/3] 讀取資料: data/{source}/raw.jsonl")
    storage = JSONLHandler()
    items = storage.read_all(source)
    logger.info(f"✓ 讀取成功: {len(items)} 筆")

    # 生成映射
    logger.info(f"\n[2/3] 生成映射")
    mapping = {}

    stats = {
        'total': len(items),
        'with_laws': 0,
        'with_original_url': 0,
        'law_count': 0
    }

    for i, item in enumerate(items, 1):
        file_id = item.get('id')

        if not file_id:
            logger.warning(f"  跳過第 {i} 筆（無 ID）")
            continue

        # 提取內容
        content = item.get('content', {})
        content_text = content.get('text', '')
        content_html = content.get('html', '')

        # 提取適用法條
        applicable_laws = extract_applicable_laws(content_text)

        # 生成法條連結
        law_links = generate_law_urls_from_list(applicable_laws)

        # 統計
        if applicable_laws:
            stats['with_laws'] += 1
            stats['law_count'] += len(applicable_laws)

        detail_url = item.get('detail_url', '')
        if detail_url:
            stats['with_original_url'] += 1

        # 建立映射
        mapping[file_id] = {
            'display_name': generate_display_name(item),
            'original_url': detail_url,
            'date': item.get('date', ''),
            'institution': item.get('institution', ''),
            'source': item.get('metadata', {}).get('source', ''),
            'category': item.get('metadata', {}).get('category', ''),
            'original_content': {
                'text': content_text,
                'html': content_html
            },
            'applicable_laws': applicable_laws,
            'law_links': law_links,  # 新增：法條連結
            'attachments': item.get('attachments', [])
        }

        # 每100筆顯示進度
        if i % 100 == 0:
            logger.info(f"  進度: {i}/{len(items)}")

    logger.info(f"✓ 映射生成完成: {len(mapping)} 筆")

    # 儲存映射
    logger.info(f"\n[3/3] 儲存映射檔")

    output_path = project_root / 'data' / source / 'file_mapping.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    logger.info(f"✓ 已儲存: {output_path}")

    # 統計資訊
    logger.info("\n" + "=" * 80)
    logger.info("統計資訊")
    logger.info("=" * 80)
    logger.info(f"\n總筆數: {stats['total']}")
    logger.info(f"包含原始 URL: {stats['with_original_url']} ({stats['with_original_url']/stats['total']*100:.1f}%)")
    logger.info(f"包含適用法條: {stats['with_laws']} ({stats['with_laws']/stats['total']*100:.1f}%)")
    logger.info(f"法條總數: {stats['law_count']}")

    if stats['with_laws'] > 0:
        avg_laws = stats['law_count'] / stats['with_laws']
        logger.info(f"平均每案法條數: {avg_laws:.1f}")

    # 法條分布統計
    all_laws = []
    for item in mapping.values():
        all_laws.extend(item['applicable_laws'])

    if all_laws:
        law_counts = {}
        for law in all_laws:
            # 提取法律名稱（不含條號）
            law_name = re.match(r'([a-zA-Z\u4e00-\u9fff]{2,15}法)', law)
            if law_name:
                name = law_name.group(1)
                law_counts[name] = law_counts.get(name, 0) + 1

        logger.info("\n最常見的法律（前10）:")
        for law, count in sorted(law_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {law}: {count} 次")

    logger.info("\n" + "=" * 80)
    logger.info("✓ 完成！")
    logger.info("=" * 80)

    return mapping


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='生成增強型檔案映射')
    parser.add_argument('--source', default='penalties', help='資料源名稱（預設: penalties）')
    parser.add_argument('--output', help='輸出檔案路徑（可選）')

    args = parser.parse_args()

    try:
        mapping = generate_file_mapping(args.source)

        # 如果指定輸出路徑，額外儲存一份
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
            logger.info(f"\n✓ 額外儲存到: {output_path}")

        logger.info(f"\n✅ 映射檔已生成")
        logger.info(f"位置: data/{args.source}/file_mapping.json")

    except Exception as e:
        logger.error(f"\n❌ 錯誤: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
