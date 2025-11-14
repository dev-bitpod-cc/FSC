"""
從上傳日誌和原始數據生成 file_id -> 顯示名稱映射

使用背景任務輸出（包含 file_id）和原始 JSONL 數據（包含完整資訊）
"""

import re
import json
from pathlib import Path
from typing import Dict

def extract_from_raw_data(raw_jsonl_path: Path) -> Dict[str, Dict]:
    """從原始 JSONL 讀取數據，建立 ID -> 資訊映射"""
    id_to_info = {}

    with open(raw_jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line.strip())
            doc_id = data.get('id', '')  # fsc_pen_20250508_0005

            # 提取基本資訊
            date = data.get('date', '')
            source = data.get('source', '')

            # 從 metadata 或 content 提取被處分對象
            metadata = data.get('metadata', {})
            target = metadata.get('target', '').strip()

            if not target:
                # 從標題提取
                title = data.get('title', '')
                # 嘗試提取公司名稱（通常在標題開頭）
                target = title.split('辦理')[0].split('因')[0].split('違反')[0].strip()

            if date and source and target:
                id_to_info[doc_id] = {
                    'date': date,
                    'source': source,
                    'target': target,
                    'display_name': f"{date}_{source}_{target}"
                }

    print(f"✓ 從原始數據提取 {len(id_to_info)} 筆資訊")
    return id_to_info

def extract_file_mapping_from_upload_log(log_content: str) -> Dict[str, str]:
    """從上傳日誌提取 doc_id -> file_id 映射"""
    doc_to_file = {}

    # 正則：處理 [N/495]: fsc_pen_YYYYMMDD_NNNN_來源_標題...
    pattern_doc = r'處理 \[\d+/\d+\]:\s*(fsc_pen_\d{8}_\d{4})_[^\.]+\.md'
    # 正則：檔案上傳成功: files/XXXXXX
    pattern_file = r'檔案上傳成功:\s*files/([a-z0-9]+)'

    lines = log_content.split('\n')
    current_doc_id = None

    for line in lines:
        # 檢查是否是 "處理" 行
        doc_match = re.search(pattern_doc, line)
        if doc_match:
            current_doc_id = doc_match.group(1)
            continue

        # 檢查是否是 "檔案上傳成功" 行
        if current_doc_id:
            file_match = re.search(pattern_file, line)
            if file_match:
                file_id = file_match.group(1)
                doc_to_file[current_doc_id] = file_id
                current_doc_id = None  # 重置

    print(f"✓ 從上傳日誌提取 {len(doc_to_file)} 筆 file_id 映射")
    return doc_to_file

def main():
    print("=" * 70)
    print("從上傳日誌和原始數據生成 File ID 映射")
    print("=" * 70)

    # 路徑
    raw_data_path = Path('data/penalties/raw.jsonl')
    output_path = Path('data/file_id_mapping.json')

    # 步驟 1: 從原始數據提取資訊
    print("\n步驟 1/3: 從原始數據提取資訊...")
    id_to_info = extract_from_raw_data(raw_data_path)

    # 步驟 2: 從背景任務輸出提取 file_id
    print("\n步驟 2/3: 讀取上傳日誌...")
    print("請提供上傳日誌內容（或將日誌保存為 logs/penalties_upload.log）")

    # 嘗試從可能的日誌位置讀取
    log_content = None
    possible_logs = [
        Path('logs/penalties_upload.log'),
        Path('logs/upload_penalties.log'),
    ]

    for log_path in possible_logs:
        if log_path.exists():
            print(f"找到日誌文件: {log_path}")
            log_content = log_path.read_text(encoding='utf-8')
            break

    if not log_content:
        print("⚠️  找不到上傳日誌文件")
        print("   請將背景任務輸出保存為 logs/penalties_upload.log")
        return

    doc_to_file = extract_file_mapping_from_upload_log(log_content)

    # 步驟 3: 合併映射
    print("\n步驟 3/3: 合併映射...")
    file_to_display = {}

    for doc_id, file_id in doc_to_file.items():
        if doc_id in id_to_info:
            display_name = id_to_info[doc_id]['display_name']
            file_to_display[file_id] = display_name
        else:
            print(f"⚠️  找不到資訊: {doc_id}")

    print(f"✓ 成功建立 {len(file_to_display)} 筆映射")

    # 保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(file_to_display, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 映射文件已保存: {output_path}")
    print(f"   共 {len(file_to_display)} 筆映射")

    # 顯示範例
    print("\n範例映射:")
    for i, (file_id, display_name) in enumerate(list(file_to_display.items())[:5], 1):
        print(f"  {i}. {file_id} -> {display_name}")

    print("\n" + "=" * 70)
    print("完成！")
    print("=" * 70)

if __name__ == '__main__':
    main()
