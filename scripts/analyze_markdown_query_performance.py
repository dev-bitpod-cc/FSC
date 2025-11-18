"""
分析 Markdown 格式化對 Gemini File Search 查詢效果的影響

使用最新的 Gemini File Search API 測試查詢效果
"""

import os
import time
import json
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("請先安裝: pip install google-genai")
    exit(1)

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

# Store ID (Markdown 版本)
MARKDOWN_STORE_ID = 'fscpenalties-tu709bvr1qti'

# 測試查詢設計
TEST_QUERIES = [
    {
        'name': '具體事實查詢',
        'query': '董事出差報銷缺失',
        'expected': '應該找到全球人壽董事長副董事長出國考察的案例',
        'keywords': ['董事', '出國', '考察', '全球人壽']
    },
    {
        'name': '法律依據查詢',
        'query': '違反保險法第148條之3',
        'expected': '應該找到違反內部控制制度的案例',
        'keywords': ['保險法', '148', '內部控制']
    },
    {
        'name': '處分金額查詢',
        'query': '罰款300萬元的裁罰案件',
        'expected': '應該找到處分金額為300萬元的案例',
        'keywords': ['300萬', '罰鍰']
    },
    {
        'name': '被處分人查詢',
        'query': '全球人壽保險公司的違規案例',
        'expected': '應該找到全球人壽的裁罰案件',
        'keywords': ['全球人壽']
    },
    {
        'name': '違規類型查詢',
        'query': '內部控制制度缺失案例',
        'expected': '應該找到內部控制相關的違規',
        'keywords': ['內部控制', '缺失']
    },
    {
        'name': '複合查詢',
        'query': '保險業內部控制缺失被罰300萬',
        'expected': '應該精確找到全球人壽案例',
        'keywords': ['保險', '內部控制', '300萬']
    },
    {
        'name': '模糊查詢',
        'query': '董事出國考察沒有事前規劃',
        'expected': '測試是否能找到相關描述',
        'keywords': ['董事', '出國', '事前規劃']
    }
]


def query_file_search_store(store_id: str, query: str, model_name: str = 'gemini-2.0-flash-exp'):
    """
    查詢 Gemini File Search Store

    Args:
        store_id: File Search Store ID (不含 fileSearchStores/ 前綴)
        query: 查詢問題
        model_name: 使用的模型

    Returns:
        dict: 包含回答、來源數量、引用等資訊
    """
    try:
        client = genai.Client(api_key=api_key)

        # 組合完整的 store name
        store_name = f'fileSearchStores/{store_id}'

        response = client.models.generate_content(
            model=model_name,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store_name]
                        )
                    )
                ],
                temperature=0.1
            )
        )

        # 提取來源數量和引用資訊
        sources_count = 0
        citations = []
        grounding_supports = []

        # 檢查 grounding metadata
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]

            # 提取 grounding metadata
            if hasattr(candidate, 'grounding_metadata'):
                metadata = candidate.grounding_metadata

                # 提取 grounding chunks (來源文件)
                if hasattr(metadata, 'grounding_chunks'):
                    sources_count = len(metadata.grounding_chunks)

                    for chunk in metadata.grounding_chunks:
                        if hasattr(chunk, 'retrieved_context'):
                            ctx = chunk.retrieved_context
                            citations.append({
                                'title': getattr(ctx, 'title', 'N/A'),
                                'uri': getattr(ctx, 'uri', 'N/A')
                            })

                # 提取 grounding supports (哪些文字片段來自哪個來源)
                if hasattr(metadata, 'grounding_supports'):
                    for support in metadata.grounding_supports:
                        grounding_supports.append({
                            'segment': getattr(support, 'segment', None),
                            'grounding_chunk_indices': getattr(support, 'grounding_chunk_indices', [])
                        })

        return {
            'success': True,
            'answer': response.text if response.text else '(無回答)',
            'answer_length': len(response.text) if response.text else 0,
            'sources_count': sources_count,
            'citations': citations,
            'grounding_supports_count': len(grounding_supports),
            'has_grounding': sources_count > 0
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'answer': None,
            'answer_length': 0,
            'sources_count': 0,
            'citations': [],
            'grounding_supports_count': 0,
            'has_grounding': False
        }


def analyze_answer_quality(result: dict, test: dict) -> dict:
    """
    分析回答品質

    Args:
        result: 查詢結果
        test: 測試案例

    Returns:
        dict: 品質分析結果
    """
    if not result['success'] or not result['answer']:
        return {
            'has_keywords': False,
            'keyword_count': 0,
            'is_relevant': False,
            'confidence': 'low'
        }

    answer = result['answer'].lower()
    keywords = test['keywords']

    # 檢查關鍵字出現次數
    keyword_count = sum(1 for kw in keywords if kw.lower() in answer)
    has_keywords = keyword_count > 0

    # 判斷相關性
    is_relevant = keyword_count >= len(keywords) / 2

    # 信心程度
    if result['sources_count'] == 0:
        confidence = 'none'  # 沒有來源,可能是編造
    elif result['sources_count'] >= 3 and keyword_count >= 2:
        confidence = 'high'
    elif result['sources_count'] >= 1 and keyword_count >= 1:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'has_keywords': has_keywords,
        'keyword_count': keyword_count,
        'total_keywords': len(keywords),
        'is_relevant': is_relevant,
        'confidence': confidence
    }


def run_analysis():
    """執行分析"""

    print("="*80)
    print("Markdown 格式化對 File Search 查詢效果影響分析")
    print("="*80)
    print()
    print(f"Store ID: {MARKDOWN_STORE_ID}")
    print(f"測試查詢數: {len(TEST_QUERIES)}")
    print()

    results = []

    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"測試 {i}/{len(TEST_QUERIES)}: {test['name']}")
        print(f"{'='*80}")
        print(f"查詢: {test['query']}")
        print(f"預期: {test['expected']}")
        print(f"關鍵字: {', '.join(test['keywords'])}")
        print()

        # 執行查詢
        print("🔍 查詢中...")
        result = query_file_search_store(MARKDOWN_STORE_ID, test['query'])

        if result['success']:
            print(f"✓ 查詢成功")
            print(f"  來源數量: {result['sources_count']}")
            print(f"  回答長度: {result['answer_length']} 字元")
            print(f"  有引用來源: {'是' if result['has_grounding'] else '否'}")

            if result['citations']:
                print(f"  引用檔案 (前3個):")
                for j, citation in enumerate(result['citations'][:3], 1):
                    print(f"    {j}. {citation['title'][:80]}")

            # 分析回答品質
            quality = analyze_answer_quality(result, test)
            print(f"\n  📊 品質分析:")
            print(f"    關鍵字匹配: {quality['keyword_count']}/{quality['total_keywords']}")
            print(f"    相關性: {'是' if quality['is_relevant'] else '否'}")
            print(f"    信心程度: {quality['confidence']}")

            # 顯示回答片段
            if result['answer']:
                preview = result['answer'][:200] + '...' if len(result['answer']) > 200 else result['answer']
                print(f"\n  💬 回答片段:")
                print(f"    {preview}")
        else:
            print(f"✗ 查詢失敗")
            print(f"  錯誤: {result['error']}")
            quality = {'confidence': 'error'}

        # 儲存結果
        result_record = {
            'test_name': test['name'],
            'query': test['query'],
            'expected': test['expected'],
            'keywords': test['keywords'],
            'result': result,
            'quality': quality if result['success'] else None
        }
        results.append(result_record)

        # 避免 rate limit
        time.sleep(3)

    # 儲存結果到檔案
    output_file = Path('data/test_results/markdown_query_analysis.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n\n{'='*80}")
    print(f"分析完成! 結果已儲存到: {output_file}")
    print(f"{'='*80}")

    # 顯示摘要統計
    print("\n📊 測試摘要:")
    print(f"  總測試數: {len(results)}")

    successful = [r for r in results if r['result']['success']]
    print(f"  成功查詢: {len(successful)}/{len(results)}")

    if successful:
        avg_sources = sum(r['result']['sources_count'] for r in successful) / len(successful)
        print(f"  平均來源數: {avg_sources:.1f}")

        with_grounding = [r for r in successful if r['result']['has_grounding']]
        print(f"  有引用來源: {len(with_grounding)}/{len(successful)} ({100*len(with_grounding)/len(successful):.0f}%)")

        # 品質統計
        high_confidence = [r for r in successful if r['quality'] and r['quality']['confidence'] == 'high']
        medium_confidence = [r for r in successful if r['quality'] and r['quality']['confidence'] == 'medium']
        low_confidence = [r for r in successful if r['quality'] and r['quality']['confidence'] == 'low']
        none_confidence = [r for r in successful if r['quality'] and r['quality']['confidence'] == 'none']

        print(f"\n  信心程度分布:")
        print(f"    高: {len(high_confidence)} ({100*len(high_confidence)/len(successful):.0f}%)")
        print(f"    中: {len(medium_confidence)} ({100*len(medium_confidence)/len(successful):.0f}%)")
        print(f"    低: {len(low_confidence)} ({100*len(low_confidence)/len(successful):.0f}%)")
        print(f"    無來源(可能編造): {len(none_confidence)} ({100*len(none_confidence)/len(successful):.0f}%)")

    return results


if __name__ == '__main__':
    try:
        results = run_analysis()
    except KeyboardInterrupt:
        print("\n\n測試中斷")
    except Exception as e:
        print(f"\n\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
