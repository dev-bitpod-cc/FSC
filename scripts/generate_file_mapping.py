"""
從 Markdown 文件和上傳日誌生成 file_id -> 顯示名稱映射文件

生成格式：日期_來源單位_裁罰對象
例如：2025-09-25_保險局_全球人壽保險股份有限公司
"""

import re
import json
from pathlib import Path
from typing import Dict, Optional

def extract_info_from_markdown(md_path: Path) -> Optional[Dict[str, str]]:
    """從 Markdown 文件中提取基本資訊"""
    try:
        content = md_path.read_text(encoding='utf-8')

        # 提取發布日期
        date_match = re.search(r'- \*\*發布日期\*\*:\s*(\d{4}-\d{2}-\d{2})', content)
        date = date_match.group(1) if date_match else None

        # 提取來源單位
        source_match = re.search(r'- \*\*來源單位\*\*:\s*(.+)', content)
        source = source_match.group(1).strip() if source_match else None

        # 提取被處分對象
        target_match = re.search(r'- \*\*名稱\*\*:\s*(.+)', content)
        target = target_match.group(1).strip() if target_match else None

        if date and source and target:
            # 生成顯示名稱：日期_來源_對象
            display_name = f"{date}_{source}_{target}"

            return {
                'date': date,
                'source': source,
                'target': target,
                'display_name': display_name,
                'original_filename': md_path.name
            }
        else:
            print(f"⚠️ 缺少資訊: {md_path.name}")
            return None

    except Exception as e:
        print(f"❌ 讀取失敗: {md_path.name} - {e}")
        return None

def extract_file_id_from_log(log_path: Path) -> Dict[str, str]:
    """從上傳日誌中提取 filename -> file_id 映射"""
    filename_to_id = {}

    try:
        log_content = log_path.read_text(encoding='utf-8')

        # 正則表達式匹配：
        # 處理 [N/495]: {filename}
        # 檔案上傳成功: files/{file_id}
        pattern = r'處理 \[\d+/\d+\]:\s*(.+?\.md)\n.*?檔案上傳成功:\s*files/([a-z0-9]+)'

        matches = re.findall(pattern, log_content, re.MULTILINE | re.DOTALL)

        for filename, file_id in matches:
            filename_to_id[filename.strip()] = file_id.strip()

        print(f"✓ 從日誌提取 {len(filename_to_id)} 筆映射")
        return filename_to_id

    except Exception as e:
        print(f"❌ 讀取日誌失敗: {e}")
        return {}

def generate_mapping(markdown_dir: Path, log_path: Path, output_path: Path):
    """生成 file_id -> display_name 映射文件"""

    print("步驟 1/3: 從 Markdown 文件提取資訊...")
    filename_to_display = {}

    md_files = list(markdown_dir.glob('*.md'))
    print(f"找到 {len(md_files)} 個 Markdown 文件")

    for md_path in md_files:
        info = extract_info_from_markdown(md_path)
        if info:
            filename_to_display[info['original_filename']] = info['display_name']

    print(f"✓ 成功提取 {len(filename_to_display)} 筆資訊")

    print("\n步驟 2/3: 從上傳日誌提取 file_id...")
    filename_to_id = extract_file_id_from_log(log_path)

    print("\n步驟 3/3: 合併映射...")
    file_id_to_display = {}

    for filename, display_name in filename_to_display.items():
        file_id = filename_to_id.get(filename)
        if file_id:
            file_id_to_display[file_id] = display_name
        else:
            print(f"⚠️  未找到 file_id: {filename}")

    print(f"✓ 成功建立 {len(file_id_to_display)} 筆映射")

    # 保存到 JSON 文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(file_id_to_display, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 映射文件已保存: {output_path}")
    print(f"   共 {len(file_id_to_display)} 筆映射")

    # 顯示幾個範例
    print("\n範例映射:")
    for i, (file_id, display_name) in enumerate(list(file_id_to_display.items())[:5], 1):
        print(f"  {i}. {file_id} -> {display_name}")

if __name__ == '__main__':
    # 路徑設定
    markdown_dir = Path('data/temp_markdown/penalties')
    log_path = Path('logs/fsc_crawler.log')  # 假設日誌在這裡
    output_path = Path('data/file_id_mapping.json')

    print("=" * 70)
    print("生成 File ID 映射文件")
    print("=" * 70)

    generate_mapping(markdown_dir, log_path, output_path)

    print("\n" + "=" * 70)
    print("完成！")
    print("=" * 70)
