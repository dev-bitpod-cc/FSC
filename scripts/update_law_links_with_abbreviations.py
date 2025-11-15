#!/usr/bin/env python3
"""更新 file_mapping.json 的 law_links，加入簡寫版本"""

import json
import sys
from pathlib import Path

# 加入專案根目錄
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.law_link_generator import generate_law_url, parse_law_article


def generate_law_urls_with_abbreviations(law_texts):
    """生成只到條層級的法條連結"""
    result = {}

    # 解析所有法條（但不直接加入 result）
    law_info_list = []
    for law_text in law_texts:
        url = generate_law_url(law_text)
        if url:
            parsed = parse_law_article(law_text)
            if parsed:
                law_info_list.append({
                    'full_text': law_text,
                    'parsed': parsed,
                    'url': url
                })

    # 按法律名稱分組
    law_groups = {}
    for info in law_info_list:
        law_name = info['parsed']['law_name']
        if law_name not in law_groups:
            law_groups[law_name] = []
        law_groups[law_name].append(info)

    # 為每組生成簡寫版本
    for law_name, laws in law_groups.items():
        if len(laws) < 2:
            continue

        # 按條文順序排序
        laws.sort(key=lambda x: (
            x['parsed'].get('article', 0),
            x['parsed'].get('sub_article', '') or '',
            x['parsed'].get('paragraph', 0) or 0
        ))

        # 為所有法律生成簡寫
        for law_info in laws:
            current = law_info['parsed']
            url = law_info['url']
            law_name = current['law_name']

            # 策略: 只生成到「條」或「條之X」層級的連結
            # 1. 帶法律名稱：保險法第X條、保險法第X條之Y
            # 2. 省略法律名稱：第X條、第X條之Y

            # 基礎條號
            base_parts = [f"第{current.get('article', '')}條"]
            if current.get('sub_article'):
                base_parts.append(f"之{current['sub_article']}")
            base_article = ''.join(base_parts)

            # 帶法律名稱的基礎版本（用於匹配「保險法第149條」）
            full_base = f"{law_name}{base_article}"
            if full_base not in result:
                result[full_base] = url

            # 簡寫版本（用於匹配「第171條之1」）
            if len(base_article) >= 3 and base_article not in result:
                result[base_article] = url

    return result


def main():
    print("=" * 80)
    print("更新 law_links 加入簡寫版本")
    print("=" * 80)

    # 讀取現有的 file_mapping.json
    mapping_path = project_root / 'data' / 'penalties' / 'file_mapping.json'
    with open(mapping_path, 'r', encoding='utf-8') as f:
        file_mapping = json.load(f)

    print(f"\n讀取: {len(file_mapping)} 筆資料")

    # 更新 law_links
    updated_count = 0
    total_added = 0

    for file_id, info in file_mapping.items():
        applicable_laws = info.get('applicable_laws', [])
        if not applicable_laws:
            continue

        # 重新生成包含簡寫的 law_links
        old_law_links = info.get('law_links', {})
        new_law_links = generate_law_urls_with_abbreviations(applicable_laws)
        old_count = len(old_law_links)
        new_count = len(new_law_links)

        # 強制更新（因為簡寫邏輯可能改變）
        if new_law_links != old_law_links:
            file_mapping[file_id]['law_links'] = new_law_links
            updated_count += 1
            if new_count > old_count:
                total_added += (new_count - old_count)
            elif new_count < old_count:
                total_added -= (old_count - new_count)

    # 儲存
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(file_mapping, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完成！")
    print(f"   更新了 {updated_count} 筆資料")
    print(f"   新增了 {total_added} 個簡寫連結")
    print(f"   儲存: {mapping_path}")

    # 驗證 2015-08-28 案例
    print(f"\n驗證案例 (2015-08-28 三商美邦人壽):")
    for file_id, info in file_mapping.items():
        if info.get('date') == '2015-08-28' and '三商美邦' in info.get('institution', ''):
            applicable_laws = info.get('applicable_laws', [])
            law_links = info.get('law_links', {})

            print(f"  法條數: {len(applicable_laws)}")
            print(f"  連結數: {len(law_links)}")
            print(f"\n  連結列表:")

            for law_text in sorted(law_links.keys()):
                if law_text in applicable_laws:
                    print(f"    ✓ {law_text} (完整版)")
                else:
                    print(f"    + {law_text} (簡寫版)")
            break

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
