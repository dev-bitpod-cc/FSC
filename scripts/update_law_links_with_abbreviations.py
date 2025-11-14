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
    """生成包含簡寫版本的法條連結"""
    result = {}

    # 先生成所有完整版本的連結
    law_info_list = []
    for law_text in law_texts:
        url = generate_law_url(law_text)
        if url:
            result[law_text] = url
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

            # 策略: 省略法律名稱，生成兩個版本
            # 1. 基礎版：第X條 或 第X條之Y
            # 2. 完整版：包含項/款/目（如果有的話）

            # 基礎版（只到條）
            base_parts = [f"第{current.get('article', '')}條"]
            if current.get('sub_article'):
                base_parts.append(f"之{current['sub_article']}")
            base_abbr = ''.join(base_parts)
            if len(base_abbr) >= 3 and base_abbr not in result:
                result[base_abbr] = url

            # 完整版（包含項/款）
            full_parts = base_parts[:]
            if current.get('paragraph'):
                full_parts.append(f"第{current['paragraph']}項")
            if current.get('subparagraph'):
                full_parts.append(f"第{current['subparagraph']}款")

            full_abbr = ''.join(full_parts)
            # 只有當完整版不同於基礎版時才加入
            if full_abbr != base_abbr and full_abbr not in result:
                result[full_abbr] = url

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
