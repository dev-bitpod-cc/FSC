#!/usr/bin/env python3
"""從上傳 manifest 生成 Gemini ID 反向映射檔

此腳本讀取 upload_manifest.json，生成從 Gemini file_id 到原始檔名的映射，
用於在 Streamlit 前端查詢時將 Gemini 內部 ID 轉換回原始檔名。

輸出格式：
{
  "files/4ax547mbfiot": "fsc_pen_20230602_0043",
  "files/2zagr8okgv8c": "fsc_pen_20210204_0124",
  ...
}
"""

import json
import re
from pathlib import Path

def extract_file_id(filename: str) -> str:
    """從檔名中提取 file_id

    例如：fsc_pen_20230602_0043_保.md → fsc_pen_20230602_0043
    """
    # 移除 .md 後綴
    name = filename.replace('.md', '')

    # 提取 fsc_pen_YYYYMMDD_NNNN 部分
    match = re.match(r'(fsc_pen_\d{8}_\d{4})', name)
    if match:
        return match.group(1)

    return name


def generate_gemini_id_mapping(
    manifest_path: str = 'data/temp_uploads/upload_manifest.json',
    output_path: str = 'data/penalties/gemini_id_mapping.json'
):
    """生成 Gemini ID 反向映射"""

    manifest_file = Path(manifest_path)

    if not manifest_file.exists():
        print(f"❌ Manifest 檔案不存在: {manifest_path}")
        return

    # 讀取 manifest
    print(f"讀取 manifest: {manifest_path}")
    with open(manifest_file, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    # 建立反向映射
    gemini_id_mapping = {}

    for filepath, info in manifest['uploaded'].items():
        if info['status'] != 'success':
            continue

        gemini_file_id = info['file_id']  # 例如 files/4ax547mbfiot
        display_name = info['display_name']  # 例如 fsc_pen_20230602_0043_保.md

        # 提取 file_id（用於 file_mapping.json 查找）
        file_id = extract_file_id(display_name)

        # 建立映射
        gemini_id_mapping[gemini_file_id] = file_id

    # 儲存映射檔
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(gemini_id_mapping, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 反向映射已生成")
    print(f"位置: {output_path}")
    print(f"映射筆數: {len(gemini_id_mapping)}")

    # 顯示範例
    print(f"\n範例映射:")
    for i, (gemini_id, file_id) in enumerate(list(gemini_id_mapping.items())[:5]):
        print(f"  {gemini_id} → {file_id}")

    return gemini_id_mapping


if __name__ == '__main__':
    import sys
    import os

    # 切換到專案根目錄
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    print("=" * 80)
    print("生成 Gemini ID 反向映射")
    print("=" * 80)
    print()

    try:
        mapping = generate_gemini_id_mapping()

        print("\n" + "=" * 80)
        print("✅ 完成！")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
