"""分析公告附件的統計資訊"""

import json
from pathlib import Path
from collections import Counter, defaultdict
from loguru import logger

def analyze_attachments():
    """分析附件統計"""

    # 嘗試從不同可能的位置讀取資料
    possible_paths = [
        Path('data/announcements/raw.jsonl'),
        Path('data/announcements/announcements.jsonl'),
        Path('../data/announcements/raw.jsonl'),
    ]

    data_file = None
    for path in possible_paths:
        if path.exists():
            data_file = path
            break

    if not data_file:
        logger.error("找不到公告資料檔案")
        logger.info("嘗試過的路徑:")
        for p in possible_paths:
            logger.info(f"  - {p.absolute()}")
        return

    logger.info(f"讀取資料: {data_file}")

    # 統計資訊
    total_announcements = 0
    announcements_with_attachments = 0
    attachment_types = Counter()
    attachment_count_distribution = Counter()

    # 附件名稱關鍵字統計
    attachment_keywords = Counter()

    # 範例
    examples = {
        'with_pdf': [],
        'with_multiple': [],
        'with_comparison': []  # 對照表
    }

    # 讀取 JSONL
    with open(data_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue

            try:
                item = json.loads(line)
                total_announcements += 1

                attachments = item.get('attachments', [])

                if attachments:
                    announcements_with_attachments += 1

                    # 附件數量分布
                    attachment_count_distribution[len(attachments)] += 1

                    # 附件類型
                    for att in attachments:
                        att_type = att.get('type', 'unknown')
                        attachment_types[att_type] += 1

                        # 關鍵字統計
                        name = att.get('name', '').lower()
                        if '對照' in name or '對照表' in name:
                            attachment_keywords['對照表'] += 1
                            if len(examples['with_comparison']) < 3:
                                examples['with_comparison'].append({
                                    'id': item.get('id'),
                                    'title': item.get('title'),
                                    'attachment': att.get('name')
                                })
                        if '修正' in name:
                            attachment_keywords['修正'] += 1
                        if '說明' in name:
                            attachment_keywords['說明'] += 1

                    # 收集範例
                    if len(examples['with_pdf']) < 3:
                        pdf_attachments = [a for a in attachments if a.get('type') == 'pdf']
                        if pdf_attachments:
                            examples['with_pdf'].append({
                                'id': item.get('id'),
                                'title': item.get('title'),
                                'pdf_count': len(pdf_attachments)
                            })

                    if len(examples['with_multiple']) < 3 and len(attachments) >= 2:
                        examples['with_multiple'].append({
                            'id': item.get('id'),
                            'title': item.get('title'),
                            'attachment_count': len(attachments),
                            'attachments': [a.get('name') for a in attachments]
                        })

            except json.JSONDecodeError as e:
                logger.error(f"第 {line_num} 行 JSON 解析錯誤: {e}")
                continue

    # 輸出報告
    print("\n" + "="*70)
    print("📊 公告附件統計分析")
    print("="*70)

    print(f"\n總公告數: {total_announcements:,}")
    print(f"有附件的公告: {announcements_with_attachments:,} ({announcements_with_attachments/total_announcements*100:.1f}%)")
    print(f"無附件的公告: {total_announcements - announcements_with_attachments:,} ({(total_announcements - announcements_with_attachments)/total_announcements*100:.1f}%)")

    print(f"\n📎 附件類型分布:")
    for att_type, count in attachment_types.most_common():
        print(f"  {att_type:10s}: {count:4d} 個")

    print(f"\n📊 每個公告的附件數量分布:")
    for count, freq in sorted(attachment_count_distribution.items()):
        print(f"  {count} 個附件: {freq:4d} 個公告")

    print(f"\n🔍 附件名稱關鍵字:")
    for keyword, count in attachment_keywords.most_common(10):
        print(f"  {keyword:15s}: {count:4d} 次")

    # 範例
    print(f"\n📋 範例 - 有 PDF 附件的公告:")
    for ex in examples['with_pdf'][:3]:
        print(f"  [{ex['id']}] {ex['title'][:40]}... ({ex['pdf_count']} 個 PDF)")

    print(f"\n📋 範例 - 有多個附件的公告:")
    for ex in examples['with_multiple'][:3]:
        print(f"  [{ex['id']}] {ex['title'][:40]}...")
        print(f"      附件數: {ex['attachment_count']}")
        for att_name in ex['attachments']:
            print(f"        - {att_name}")

    print(f"\n📋 範例 - 有對照表的公告:")
    for ex in examples['with_comparison'][:3]:
        print(f"  [{ex['id']}] {ex['title'][:40]}...")
        print(f"      附件: {ex['attachment']}")

    # 結論
    print("\n" + "="*70)
    print("💡 結論與建議")
    print("="*70)

    if announcements_with_attachments / total_announcements > 0.3:
        print("\n⚠️  超過 30% 的公告有附件，建議下載並上傳")
        print("   理由:")
        print("   - 附件包含詳細的條文對照、修正說明等重要資訊")
        print("   - Gemini File Search 原生支援 PDF，可自動提取和索引")
        print("   - 缺少附件內容會導致回答不完整")
    else:
        print("\n✅ 附件比例較低，可考慮只下載重要附件（如對照表）")

    if attachment_keywords.get('對照表', 0) > 100:
        print(f"\n⭐ 發現 {attachment_keywords['對照表']} 個對照表附件")
        print("   建議優先下載對照表類型的附件")


if __name__ == '__main__':
    analyze_attachments()
