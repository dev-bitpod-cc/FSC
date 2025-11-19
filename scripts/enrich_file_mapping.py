"""
增強 file_mapping.json - 提取機構名稱、罰款金額、來源單位中文名稱
"""

import json
import re
from pathlib import Path

# 來源單位代碼轉中文映射表
SOURCE_UNIT_MAPPING = {
    'bank_bureau': '銀行局',
    'insurance_bureau': '保險局',
    'securities_bureau': '證券期貨局',
    'aml_office': '洗錢防制辦公室',
    'fsc': '金管會'
}

def extract_institution_name(title: str, raw_institution: str) -> str:
    """
    三層策略提取機構名稱
    """
    institution = None
    
    # 策略 1: 從 title 開頭提取（最常見）
    match = re.match(
        r'^([^違與因未涉經辦就依查核獲對於關於自]+?(?:股份有限公司|商業銀行|銀行|證券|保險|投信|投顧|期貨|金控|人壽|產險|證券投資信託|證券投資顧問))',
        title
    )
    if match:
        institution = match.group(1).strip()
    
    # 策略 2: 在整個 title 中搜索
    if not institution:
        search = re.search(
            r'((?:[^\s，。、；：於]{1,20})(?:股份有限公司|商業銀行|銀行|證券|保險|投信|投顧|期貨|金控|人壽|產險))',
            title
        )
        if search:
            candidate = search.group(1).strip()
            # 過濾不合理結果
            if not any(word in candidate for word in ['停止', '處分', '送達', '起', '下稱']):
                institution = candidate
    
    # 策略 3: 從 raw_institution 提取或直接使用
    if not institution:
        if len(raw_institution) > 30:
            clean_match = re.search(
                r'((?:[^\s，。、；：於]{1,20})(?:股份有限公司|商業銀行|銀行|證券|保險|投信|投顧|期貨|金控|人壽|產險))',
                raw_institution
            )
            if clean_match:
                institution = clean_match.group(1).strip()
                # 移除「(下稱...」等後綴
                institution = re.sub(r'\s*[（\(].*$', '', institution)
            else:
                institution = raw_institution
        else:
            institution = raw_institution
    
    return institution or 'N/A'

def extract_penalty_amount(title: str) -> str:
    """
    從 title 提取罰款金額
    """
    # 支援多種格式
    match = re.search(
        r'(?:新臺幣|新台幣|罰鍰|罰緩|核處|處)?[\s\(（]*(?:下同)?[\s\)）]*(\d+(?:,\d+)*(?:\.\d+)?)\s*(萬|億)?元(?:罰鍰|罰緩)?',
        title
    )
    if match:
        amount = match.group(1).replace(',', '')
        unit_char = match.group(2) or ''
        unit = f"{unit_char}元" if unit_char else "元"
        return f"新臺幣 {amount} {unit}"
    
    return 'N/A'

def main():
    # 載入 file_mapping.json
    mapping_file = Path('data/penalties/file_mapping.json')
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    print(f"開始增強 file_mapping.json ({len(mapping)} 筆資料)")
    print("=" * 80)
    
    updated_count = 0
    
    for file_id, info in mapping.items():
        title = info.get('title', '')
        raw_institution = info.get('institution', '')
        source_code = info.get('source', '')
        
        # 提取機構名稱
        institution_name_clean = extract_institution_name(title, raw_institution)
        
        # 提取罰款金額
        penalty_amount_formatted = extract_penalty_amount(title)
        
        # 來源單位中文名稱
        source_display = SOURCE_UNIT_MAPPING.get(source_code, source_code)
        
        # 更新欄位
        info['institution_name_clean'] = institution_name_clean
        info['penalty_amount_formatted'] = penalty_amount_formatted
        info['source_display'] = source_display
        
        updated_count += 1
        
        if updated_count % 100 == 0:
            print(f"已處理 {updated_count} 筆...")
    
    # 儲存更新後的 mapping
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成！共更新 {updated_count} 筆資料")
    print(f"新增欄位:")
    print(f"  - institution_name_clean: 清理後的機構名稱")
    print(f"  - penalty_amount_formatted: 格式化的罰款金額")
    print(f"  - source_display: 來源單位中文名稱")
    
    # 顯示範例
    print("\n範例資料:")
    sample = list(mapping.values())[0]
    print(f"  institution_name_clean: {sample.get('institution_name_clean')}")
    print(f"  penalty_amount_formatted: {sample.get('penalty_amount_formatted')}")
    print(f"  source_display: {sample.get('source_display')}")

if __name__ == '__main__':
    main()
