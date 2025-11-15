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
from src.utils.law_link_generator import generate_law_urls_from_list, generate_law_url, parse_law_article
import google.generativeai as genai
import os
import time


def clean_content_text(text: str) -> str:
    """
    清理內容文字，移除網頁雜訊

    移除的雜訊包括：
    - 社群分享按鈕（FACEBOOK、Line、Twitter）
    - 導航元素（友善列印、回上頁）
    - 頁面標題重複（裁罰案件）

    Args:
        text: 原始內容文字

    Returns:
        清理後的文字
    """
    if not text:
        return ''

    # 移除開頭的雜訊行
    noise_patterns = [
        '裁罰案件',
        '_',
        'FACEBOOK',
        'Line',
        'Twitter',
        '友善列印',
        '回上頁',
    ]

    lines = text.split('\n')
    cleaned_lines = []

    # 跳過開頭的雜訊行
    skip_lines = 0
    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # 如果是雜訊行，標記跳過
        if line_stripped in noise_patterns:
            skip_lines = i + 1
        # 如果已經看到非雜訊的實質內容，停止跳過
        elif line_stripped and len(line_stripped) > 10:
            break

    # 從第一個非雜訊行開始保留
    cleaned_lines = lines[skip_lines:]

    return '\n'.join(cleaned_lines).strip()


def extract_applicable_laws(content_text: str) -> List[str]:
    """
    從內容中提取適用法條（僅提取核心違規法規）

    常見法條格式：
    - 銀行法第61條
    - 保險法第149條第1項
    - 證券交易法第66條之1
    - 金融控股公司法第57條第2項第1款
    - 同法第149條（引用前文法律）

    優化策略：
    1. 只提取違規相關法條（有「違反」等關鍵字）
    2. 過濾程序性法規（訴願法、行政執行法）
    3. 處理「同法」引用（替換為前文法律名稱）
    4. 去重（避免同一法條重複出現）

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
    last_law_name = None  # 追蹤最近一次提到的法律名稱（用於處理「同法」）

    # 策略1: 優先提取明確標示違反的法條
    # 例如：「違反銀行法第45條」、「核有違反保險法第149條」
    violation_patterns = [
        r'違反.*?([a-zA-Z\u4e00-\u9fff]{2,15}法)第(\d+)條(?:之(\d+))?(?:第(\d+)項)?(?:第(\d+)款)?(?:第(\d+)目)?',
        r'核.*?違反.*?([a-zA-Z\u4e00-\u9fff]{2,15}法)第(\d+)條(?:之(\d+))?(?:第(\d+)項)?(?:第(\d+)款)?(?:第(\d+)目)?',
        # 處理「並依」結構（例如：「並依同法第149條」）
        r'並依.*?([a-zA-Z\u4e00-\u9fff]{2,15}法)第(\d+)條(?:之(\d+))?(?:第(\d+)項)?(?:第(\d+)款)?(?:第(\d+)目)?',
    ]

    for pattern in violation_patterns:
        matches = re.finditer(pattern, content_text)
        for match in matches:
            law_name = match.group(1)

            # 過濾程序性法規
            if law_name in PROCEDURAL_LAWS:
                continue

            # 過濾掉以無效前綴開頭的法名（這些通常是誤匹配）
            # 例如：「與保險法」（原文是「核與保險法...不符」，「與」是連接詞）
            if law_name.startswith(('與', '及', '或', '和')):
                continue

            # 處理「同法」引用
            if law_name.startswith('同'):
                # 移除「同」前綴
                law_name = law_name[1:]
                # 如果有前文法律，替換為該法律名稱
                if last_law_name and last_law_name not in PROCEDURAL_LAWS:
                    law_name = last_law_name
                else:
                    # 沒有前文可以引用，跳過
                    continue

            # 移除法名中的前綴詞
            law_name = re.sub(r'^(依|核|核已|核有|已|有|分別為|應依|爰依|按|惟|並依|並依同|據)', '', law_name)

            # 過濾掉無效法名
            if law_name in ['法', '本法'] or len(law_name) < 3:
                continue

            # 重建法條文字（純淨格式）
            law_text = law_name + '第' + match.group(2) + '條'
            if match.group(3):  # 之X
                law_text += '之' + match.group(3)
            if match.group(4):  # 第X項
                law_text += '第' + match.group(4) + '項'
            if match.group(5):  # 第X款
                law_text += '第' + match.group(5) + '款'
            if match.group(6):  # 第X目
                law_text += '第' + match.group(6) + '目'

            laws.add(law_text)

            # 更新最近提到的法律名稱（用於後續「同法」引用）
            last_law_name = law_name

    # 策略2: 提取裁罰依據（無論策略1是否找到）
    # 例如：「依銀行法第129條」、「爰依保險法第171條」、「依...規定」
    # 注意：移除了 "if not laws:" 條件，讓違規法條和裁罰依據都被提取
    penalty_patterns = [
        r'依.*?([a-zA-Z\u4e00-\u9fff]{2,15}法)第(\d+)條(?:之(\d+))?(?:第(\d+)項)?(?:第(\d+)款)?(?:第(\d+)目)?.*?(?:處|核處|罰鍰|規定)',
        r'爰依.*?([a-zA-Z\u4e00-\u9fff]{2,15}法)第(\d+)條(?:之(\d+))?(?:第(\d+)項)?(?:第(\d+)款)?(?:第(\d+)目)?',
    ]

    for pattern in penalty_patterns:
        matches = re.finditer(pattern, content_text)
        for match in matches:
            law_name = match.group(1)

            # 過濾程序性法規
            if law_name in PROCEDURAL_LAWS:
                continue

            # 過濾掉以無效前綴開頭的法名（這些通常是誤匹配）
            if law_name.startswith(('與', '及', '或', '和')):
                continue

            # 處理「同法」引用
            if law_name.startswith('同'):
                # 移除「同」前綴
                law_name = law_name[1:]
                # 如果有前文法律，替換為該法律名稱
                if last_law_name and last_law_name not in PROCEDURAL_LAWS:
                    law_name = last_law_name
                else:
                    # 沒有前文可以引用，跳過
                    continue

            # 移除法名中的前綴詞
            law_name = re.sub(r'^(依|核|核已|核有|已|有|分別為|應依|爰依|按|惟|並依|並依同|據)', '', law_name)

            # 過濾掉無效法名
            if law_name in ['法', '本法'] or len(law_name) < 3:
                continue

            # 重建法條文字（純淨格式）
            law_text = law_name + '第' + match.group(2) + '條'
            if match.group(3):  # 之X
                law_text += '之' + match.group(3)
            if match.group(4):  # 第X項
                law_text += '第' + match.group(4) + '項'
            if match.group(5):  # 第X款
                law_text += '第' + match.group(5) + '款'
            if match.group(6):  # 第X目
                law_text += '第' + match.group(6) + '目'

            laws.add(law_text)

            # 更新最近提到的法律名稱（用於後續「同法」引用）
            last_law_name = law_name

    # 排序並返回列表
    return sorted(list(laws))


def extract_applicable_laws_with_llm(content_text: str, api_key: str = None) -> List[str]:
    """
    使用 LLM 從內容中提取適用法條

    相比 regex 方法，LLM 可以：
    1. 正確理解「同法」等語義引用
    2. 過濾程序性法規
    3. 只提取核心違規法條

    Args:
        content_text: 裁罰案件內容文字
        api_key: Gemini API Key（若為 None 則從環境變數讀取）

    Returns:
        法條列表，格式如 ["保險法第171條之1第5項", "保險法第149條第1項"]
    """
    if not content_text or len(content_text.strip()) < 10:
        return []

    # 初始化 API
    if api_key is None:
        api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        logger.error("未設定 GEMINI_API_KEY")
        return []

    genai.configure(api_key=api_key)

    # 使用 2.5 Flash 模型（便宜且快速）
    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = f"""請從以下金管會裁罰案件內容中，提取**核心違規法條**。

要求：
1. 只提取機構實際違反的法條（不要包含程序性法規，如訴願法、行政執行法等）
2. 若出現「同法」，請替換為前文提到的法律名稱
3. 只提取到「條」、「項」、「款」、「目」層級，不要包含法條內容
4. 以 JSON 陣列格式回傳，每個元素是一個完整法條

範例輸出格式：
["保險法第171條之1第5項", "保險法第149條第1項"]

裁罰內容：
{content_text[:2000]}

請直接回傳 JSON 陣列，不要包含任何其他文字或解釋。"""

    try:
        # 調用 API
        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # 移除可能的 markdown 代碼塊標記
        if result_text.startswith('```'):
            lines = result_text.split('\n')
            result_text = '\n'.join(lines[1:-1])  # 移除第一行和最後一行

        # 解析 JSON
        laws = json.loads(result_text)

        if not isinstance(laws, list):
            logger.warning(f"LLM 回傳格式錯誤（非陣列）: {result_text}")
            return []

        # 過濾和標準化
        filtered_laws = []
        for law in laws:
            if not isinstance(law, str):
                continue
            law = law.strip()

            # 基本驗證：至少要有「法第X條」的格式
            if '法' not in law or '第' not in law or '條' not in law:
                continue

            filtered_laws.append(law)

        return filtered_laws

    except json.JSONDecodeError as e:
        logger.warning(f"LLM 回傳無法解析為 JSON: {result_text[:200]}")
        return []
    except Exception as e:
        logger.error(f"LLM 提取法條失敗: {e}")
        return []


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

    # 先移除常見的前綴
    prefixes_to_remove = [
        '有關本會對', '有關', '本會對', '經', '為',
        '停止受處分人', '對於'
    ]

    cleaned_title = title
    for prefix in prefixes_to_remove:
        if cleaned_title.startswith(prefix):
            cleaned_title = cleaned_title[len(prefix):]
            break

    # 分隔詞（機構名稱後通常接這些詞）
    # 按長度降序排列，避免短詞先匹配導致錯誤切分
    separators = [
        # 時間相關
        '103年度', '104年度', '105年度', '106年度', '107年度',
        '108年度', '109年度', '110年度', '111年度', '112年度', '113年度',
        '於民國', '前於', '於110年', '於111年', '於112年', '於113年',
        # 分行/分支機構
        '永和分行', '新生分行', '分行理專', '理財專員', '行員',
        # 檢查報告相關
        '一般業務檢查', '業務檢查', '檢查報告',
        # 處理動作
        '處理', '辦理', '經營', '從事', '受託', '送審', '持有',
        # 違規相關
        '涉及', '所涉', '違反', '核有',
        # 特定業務
        '客服', '催收',
        # 條件/原因
        '因', '對於',
        # 否定
        '未依', '未於', '未經', '未能', '未確實',
        # 時間
        '自', '前', '經',
        # 其他
        '及相關子公司', '執行董事', '之公司治理'
    ]

    # 找到第一個分隔詞的位置（使用清理後的標題）
    institution = cleaned_title
    min_pos = len(cleaned_title)

    for sep in separators:
        pos = cleaned_title.find(sep)
        if pos > 0 and pos < min_pos:  # 必須在開頭之後找到
            min_pos = pos

    if min_pos < len(cleaned_title):
        institution = cleaned_title[:min_pos]
    else:
        # 如果找不到分隔詞，嘗試找到第一個中文句號或逗號
        for punct in ['，', '。', '、']:
            pos = cleaned_title.find(punct)
            if pos > 0:
                institution = cleaned_title[:pos]
                break
        else:
            # 仍找不到，取前30個字（降低長度避免抓到太多內容）
            institution = cleaned_title[:30]

    # 簡化機構名稱（按順序處理，避免過度簡化）
    simplifications = [
        # 先處理完整後綴
        ('保險股份有限公司', ''),
        ('人壽保險股份有限公司', '人壽'),
        ('產物保險股份有限公司', '產險'),
        ('股份有限公司', ''),
        ('有限公司', ''),
        # 再處理銀行類
        ('商業銀行', '銀行'),
        # 證券類
        ('證券投資信託', '投信'),
        ('證券投資顧問', '投顧'),
        ('證券金融', '證金'),
        # 其他
        ('期貨', '期貨'),
    ]

    for old, new in simplifications:
        if old in institution:
            institution = institution.replace(old, new)
            break  # 只替換第一個匹配的，避免過度簡化

    # 移除可能重複的「公司」
    if institution.endswith('公司'):
        institution = institution[:-2]

    # 清理空白
    institution = institution.strip()

    # 如果太短或為空，返回未知
    if len(institution) < 2:
        return '未知機構'

    return institution


def generate_law_urls_with_abbreviations(law_texts: List[str]) -> Dict[str, str]:
    """
    生成法條連結字典，包含簡寫版本

    策略：為同一法律的多個條文生成簡寫版本，以支持法律文書中的簡寫引用
    例如："保險法第149條第1項、第171條之1第4項及第5項規定"

    Args:
        law_texts: 法條文字列表（完整版）

    Returns:
        {法條文字: URL} 的字典（包含完整版和簡寫版）
    """
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
            continue  # 只有一條法律，不需要簡寫

        # 按條文順序排序
        laws.sort(key=lambda x: (
            int(x['parsed']['article']),
            x['parsed']['sub_article'] or '',
            int(x['parsed']['paragraph'] or 0)
        ))

        # 為第2條及之後的法律生成簡寫
        for i in range(1, len(laws)):
            current = laws[i]['parsed']
            prev = laws[i-1]['parsed']
            url = laws[i]['url']

            # 策略 1: 省略法律名稱（如 "第171條之1第4項"）
            abbr_parts = [f"第{current['article']}條"]

            if current['sub_article']:
                abbr_parts.append(f"之{current['sub_article']}")

            if current['paragraph']:
                abbr_parts.append(f"第{current['paragraph']}項")

            if current['subparagraph']:
                abbr_parts.append(f"第{current['subparagraph']}款")

            if current['point']:
                abbr_parts.append(f"第{current['point']}目")

            abbr = ''.join(abbr_parts)
            if len(abbr) >= 5 and abbr not in result:  # 至少「第X條」
                result[abbr] = url

            # 策略 2: 如果條號相同，簡寫到項/款/目（如 "第5項"）
            if (prev['article'] == current['article'] and
                prev['sub_article'] == current['sub_article']):

                if current['paragraph'] and not current['subparagraph'] and not current['point']:
                    abbr = f"第{current['paragraph']}項"
                    # 「第X項」風險較高，但在特定上下文下可以接受
                    if abbr not in result:
                        result[abbr] = url

                if current['subparagraph'] and not current['point']:
                    abbr = f"第{current['subparagraph']}款"
                    if abbr not in result:
                        result[abbr] = url

                if current['point']:
                    abbr = f"第{current['point']}目"
                    if abbr not in result:
                        result[abbr] = url

    return result


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


def generate_file_mapping(source: str = 'penalties', use_llm: bool = False, api_key: str = None) -> Dict[str, Any]:
    """
    生成檔案映射

    Args:
        source: 資料源名稱（預設: penalties）
        use_llm: 是否使用 LLM 提取法條（預設: False，使用 regex）
        api_key: Gemini API Key（若為 None 則從環境變數讀取）

    Returns:
        檔案映射字典
    """
    logger.info("=" * 80)
    logger.info("生成增強型檔案映射")
    if use_llm:
        logger.info("使用 LLM 提取法條（Gemini Flash）")
    else:
        logger.info("使用 Regex 提取法條")
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
        content_text_raw = content.get('text', '')
        content_html = content.get('html', '')

        # 清理內容文字（移除網頁雜訊）
        content_text = clean_content_text(content_text_raw)

        # 提取適用法條
        if use_llm:
            if i % 10 == 1:  # 每 10 筆顯示進度
                logger.info(f"  處理中: {i}/{len(items)} (使用 LLM)")
            applicable_laws = extract_applicable_laws_with_llm(content_text, api_key)
            # 添加延遲避免 API 限流
            time.sleep(0.5)
        else:
            applicable_laws = extract_applicable_laws(content_text)

        # 生成法條連結（包含簡寫版本）
        law_links = generate_law_urls_with_abbreviations(applicable_laws)

        # 統計
        if applicable_laws:
            stats['with_laws'] += 1
            stats['law_count'] += len(applicable_laws)

        detail_url = item.get('detail_url', '')
        if detail_url:
            stats['with_original_url'] += 1

        # 提取機構名稱
        title = item.get('title', '')
        institution_name = extract_institution_from_title(title)

        # 建立映射
        mapping[file_id] = {
            'display_name': generate_display_name(item),
            'original_url': detail_url,
            'date': item.get('date', ''),
            'title': title,  # 新增：完整標題
            'institution': institution_name,  # 修正：使用提取的機構名稱
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

        # 顯示進度（LLM 模式每 10 筆，Regex 模式每 100 筆）
        progress_interval = 10 if use_llm else 100
        if i % progress_interval == 0:
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
    parser.add_argument('--use-llm', action='store_true', help='使用 LLM 提取法條（需要 GEMINI_API_KEY）')

    args = parser.parse_args()

    try:
        mapping = generate_file_mapping(args.source, use_llm=args.use_llm)

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
