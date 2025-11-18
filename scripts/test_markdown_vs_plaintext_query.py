"""
測試 Markdown vs Plain Text 查詢效果對比

比較結構化 Markdown 和純文字上傳對 Gemini File Search 查詢效果的影響
"""

import os
import time
import json
from pathlib import Path
import google.generativeai as genai

# 載入環境變數
api_key = os.getenv('GEMINI_API_KEY')

# 如果沒有從環境變數取得,嘗試從 .env 檔案讀取
if not api_key:
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith('GEMINI_API_KEY='):
                    api_key = line.split('=', 1)[1].strip().strip('"').strip("'")

if not api_key:
    raise ValueError("請在 .env 檔案中設定 GEMINI_API_KEY")

genai.configure(api_key=api_key)

# Store IDs
MARKDOWN_STORE_ID = 'fileSearchStores/fscpenalties-tu709bvr1qti'  # Markdown 版本
PLAINTEXT_STORE_ID = None  # 待確認是否存在

# 測試查詢設計
TEST_QUERIES = [
    {
        'name': '具體事實查詢',
        'query': '董事出差報銷缺失',
        'expected': '應該找到全球人壽董事長副董事長出國考察的案例'
    },
    {
        'name': '法律依據查詢',
        'query': '違反保險法第148條之3',
        'expected': '應該找到違反內部控制制度的案例'
    },
    {
        'name': '處分金額查詢',
        'query': '罰款300萬元的裁罰案件',
        'expected': '應該找到處分金額為300萬元的案例'
    },
    {
        'name': '被處分人查詢',
        'query': '全球人壽保險公司的違規案例',
        'expected': '應該找到全球人壽的裁罰案件'
    },
    {
        'name': '違規類型查詢',
        'query': '內部控制制度缺失案例',
        'expected': '應該找到內部控制相關的違規'
    },
    {
        'name': '複合查詢',
        'query': '保險業內部控制缺失被罰300萬',
        'expected': '應該精確找到全球人壽案例'
    },
    {
        'name': '模糊查詢',
        'query': '董事出國考察沒有事前規劃',
        'expected': '測試是否能找到相關描述'
    }
]


def query_file_search_store(store_id: str, query: str, model_name: str = 'gemini-2.0-flash-exp'):
    """
    查詢 Gemini File Search Store

    Args:
        store_id: File Search Store ID
        query: 查詢問題
        model_name: 使用的模型

    Returns:
        dict: 包含回答、來源數量、引用等資訊
    """
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            tools=[{
                'file_search': {
                    'file_search_store': store_id
                }
            }]
        )

        response = model.generate_content(query)

        # 提取來源數量
        sources_count = 0
        citations = []

        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata'):
                metadata = candidate.grounding_metadata
                if hasattr(metadata, 'grounding_chunks'):
                    sources_count = len(metadata.grounding_chunks)

                    # 提取引用資訊
                    for chunk in metadata.grounding_chunks:
                        if hasattr(chunk, 'retrieved_context'):
                            ctx = chunk.retrieved_context
                            citations.append({
                                'title': getattr(ctx, 'title', 'N/A'),
                                'uri': getattr(ctx, 'uri', 'N/A')
                            })

        return {
            'answer': response.text if response.text else '(無回答)',
            'sources_count': sources_count,
            'citations': citations,
            'raw_response': response
        }

    except Exception as e:
        return {
            'error': str(e),
            'answer': None,
            'sources_count': 0,
            'citations': []
        }


def run_comparison_tests():
    """執行對比測試"""

    print("="*80)
    print("Markdown vs Plain Text 查詢效果對比測試")
    print("="*80)
    print()

    # 檢查 Plain Text Store 是否存在
    if PLAINTEXT_STORE_ID is None:
        print("⚠️  注意: Plain Text Store ID 未設定,僅測試 Markdown Store")
        print()

    results = []

    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"測試 {i}/{len(TEST_QUERIES)}: {test['name']}")
        print(f"{'='*80}")
        print(f"查詢: {test['query']}")
        print(f"預期: {test['expected']}")
        print()

        # 測試 Markdown Store
        print("📊 測試 Markdown Store...")
        md_result = query_file_search_store(MARKDOWN_STORE_ID, test['query'])

        print(f"  來源數量: {md_result['sources_count']}")
        print(f"  回答長度: {len(md_result.get('answer', '')) if md_result.get('answer') else 0} 字元")

        if md_result.get('citations'):
            print(f"  引用檔案:")
            for j, citation in enumerate(md_result['citations'][:3], 1):
                print(f"    {j}. {citation['title'][:80]}")

        if md_result.get('error'):
            print(f"  ❌ 錯誤: {md_result['error']}")

        # 如果有 Plain Text Store,也測試
        pt_result = None
        if PLAINTEXT_STORE_ID:
            print("\n📊 測試 Plain Text Store...")
            time.sleep(2)  # 避免 rate limit
            pt_result = query_file_search_store(PLAINTEXT_STORE_ID, test['query'])

            print(f"  來源數量: {pt_result['sources_count']}")
            print(f"  回答長度: {len(pt_result.get('answer', '')) if pt_result.get('answer') else 0} 字元")

            if pt_result.get('citations'):
                print(f"  引用檔案:")
                for j, citation in enumerate(pt_result['citations'][:3], 1):
                    print(f"    {j}. {citation['title'][:80]}")

        # 儲存結果
        results.append({
            'test_name': test['name'],
            'query': test['query'],
            'expected': test['expected'],
            'markdown_result': md_result,
            'plaintext_result': pt_result
        })

        # 避免 rate limit
        time.sleep(3)

    # 儲存結果到檔案
    output_file = Path('data/test_results/markdown_vs_plaintext_comparison.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        # 移除 raw_response (不可序列化)
        for r in results:
            if 'markdown_result' in r and 'raw_response' in r['markdown_result']:
                del r['markdown_result']['raw_response']
            if 'plaintext_result' in r and r['plaintext_result'] and 'raw_response' in r['plaintext_result']:
                del r['plaintext_result']['raw_response']

        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n\n{'='*80}")
    print(f"測試完成! 結果已儲存到: {output_file}")
    print(f"{'='*80}")

    # 顯示摘要
    print("\n📊 測試摘要:")
    print(f"  總測試數: {len(results)}")

    md_avg_sources = sum(r['markdown_result']['sources_count'] for r in results) / len(results)
    print(f"  Markdown 平均來源數: {md_avg_sources:.1f}")

    if PLAINTEXT_STORE_ID:
        pt_avg_sources = sum(r['plaintext_result']['sources_count'] for r in results if r['plaintext_result']) / len(results)
        print(f"  Plain Text 平均來源數: {pt_avg_sources:.1f}")

    return results


if __name__ == '__main__':
    try:
        results = run_comparison_tests()
    except KeyboardInterrupt:
        print("\n\n測試中斷")
    except Exception as e:
        print(f"\n\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
