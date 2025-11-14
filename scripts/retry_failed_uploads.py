"""
重新上傳失敗的裁罰案件

失敗案件：
1. fsc_pen_20250731_0003 - 三商美邦人壽
2. fsc_pen_20201126_0134 - 玉山商業銀行
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# 加入專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

from src.processor.penalty_markdown_formatter import PenaltyMarkdownFormatter
from src.uploader.gemini_uploader import GeminiUploader

FAILED_IDS = [
    'fsc_pen_20250731_0003',
    'fsc_pen_20201126_0134'
]

def main():
    print("=" * 70)
    print("重新上傳失敗的裁罰案件")
    print("=" * 70)

    # 設定路徑
    raw_data_path = Path('data/penalties/raw.jsonl')
    temp_dir = Path('data/temp_retry')
    temp_dir.mkdir(parents=True, exist_ok=True)

    # API Key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ 找不到 GEMINI_API_KEY")
        return

    store_id = 'fileSearchStores/fscpenalties-ma1326u8ck77'

    print(f"\n要重新上傳的案件：")
    for idx, doc_id in enumerate(FAILED_IDS, 1):
        print(f"  {idx}. {doc_id}")

    # 步驟 1: 從 raw.jsonl 提取資料
    print(f"\n步驟 1/3: 從原始數據提取失敗案件...")
    failed_cases = []

    with open(raw_data_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line.strip())
            if data.get('id') in FAILED_IDS:
                failed_cases.append(data)
                print(f"  ✓ 找到: {data['id']}")

    if len(failed_cases) != len(FAILED_IDS):
        print(f"⚠️  只找到 {len(failed_cases)}/{len(FAILED_IDS)} 筆案件")

    # 步驟 2: 生成 Markdown
    print(f"\n步驟 2/3: 生成 Markdown 文件...")
    formatter = PenaltyMarkdownFormatter()
    md_files = []

    for case in failed_cases:
        doc_id = case['id']
        md_content = formatter.format_penalty(case)

        # 生成文件名（與原始上傳格式一致）
        date = case.get('date', '').replace('-', '')
        seq = doc_id.split('_')[-1]  # 序號
        source = case.get('source', '未知')
        title = case.get('title', '')[:50]  # 取前50字符

        filename = f"{doc_id}_{source}_{title}.md"
        # 清理文件名中的非法字符
        filename = filename.replace('/', '_').replace('\\', '_').replace(':', '_')

        md_path = temp_dir / filename
        md_path.write_text(md_content, encoding='utf-8')
        md_files.append(md_path)

        print(f"  ✓ 已生成: {filename}")

    # 步驟 3: 上傳到 Gemini
    print(f"\n步驟 3/3: 上傳到 Gemini Store...")
    print(f"Store ID: {store_id}")

    uploader = GeminiUploader(
        api_key=api_key,
        store_name='fsc-penalties',
        max_retries=5,      # 增加重試次數
        retry_delay=3.0     # 增加延遲
    )

    # 設定 Store ID (直接使用已知的 store ID)
    uploader.store_id = store_id

    success_count = 0
    fail_count = 0

    for md_path in md_files:
        print(f"\n處理: {md_path.name}")

        try:
            # 使用 upload_and_add 方法 (返回 bool)
            success = uploader.upload_and_add(
                filepath=str(md_path),
                delay=3.0  # 每次操作間延遲 3 秒
            )

            if success:
                print(f"  ✅ 成功上傳")
                success_count += 1
            else:
                print(f"  ❌ 上傳失敗")
                fail_count += 1

        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
            fail_count += 1

        # 添加延遲避免觸發速率限制
        import time
        time.sleep(3)

    # 總結
    print("\n" + "=" * 70)
    print("上傳結果:")
    print(f"  成功: {success_count}/{len(md_files)}")
    print(f"  失敗: {fail_count}/{len(md_files)}")
    print("=" * 70)

    # 清理臨時文件
    if success_count == len(md_files):
        print("\n清理臨時文件...")
        for md_path in md_files:
            md_path.unlink()
        temp_dir.rmdir()
        print("✓ 臨時文件已清理")

if __name__ == '__main__':
    main()
