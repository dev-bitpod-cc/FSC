"""探索裁罰案件頁面結構"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json

# 禁用 SSL 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def explore_list_page():
    """探索列表頁結構"""

    print("=" * 70)
    print("探索裁罰案件列表頁")
    print("=" * 70)

    # 列表頁 URL
    url = "https://www.fsc.gov.tw/ch/home.jsp"

    # POST 表單參數
    form_data = {
        'id': '131',
        'contentid': '131',
        'parentpath': '0,2',
        'mcustomize': 'multimessage_list.jsp',
        'page': '1',
        'pagesize': '15',
    }

    # 發送請求
    response = requests.post(url, data=form_data, verify=False, timeout=30)
    response.encoding = 'utf-8'

    soup = BeautifulSoup(response.text, 'html.parser')

    # 1. 檢查是否使用 <table> 結構
    print("\n1. 列表結構分析")
    tables = soup.find_all('table')
    print(f"找到 {len(tables)} 個 <table>")

    # 檢查是否使用 <li role="row"> 結構（像公告一樣）
    li_rows = soup.select('li[role="row"]')
    print(f"找到 {len(li_rows)} 個 li[role='row']")

    # 2. 解析列表項目
    if li_rows:
        print("\n使用 li[role='row'] 結構（與公告相同）")
        print(f"\n前 3 筆資料範例:")

        for i, row in enumerate(li_rows[:3], 1):
            print(f"\n--- 第 {i} 筆 ---")

            # 提取欄位
            no = row.select_one('span.no')
            date = row.select_one('span.date')
            source = row.select_one('span.unit')
            link = row.select_one('span.title > a')

            print(f"編號: {no.get_text(strip=True) if no else 'N/A'}")
            print(f"日期: {date.get_text(strip=True) if date else 'N/A'}")
            print(f"來源: {source.get_text(strip=True) if source else 'N/A'}")
            print(f"標題: {link.get_text(strip=True) if link else 'N/A'}")
            print(f"連結: {link.get('href') if link else 'N/A'}")

    elif tables:
        print("\n使用 <table> 結構")
        # 解析 table
        for table in tables:
            rows = table.find_all('tr')
            print(f"\n找到 {len(rows)} 行")

            if len(rows) > 1:
                print("\n前 3 筆資料範例:")
                for i, row in enumerate(rows[1:4], 1):  # 跳過表頭
                    cells = row.find_all('td')
                    print(f"\n--- 第 {i} 筆 ---")
                    print(f"欄位數: {len(cells)}")
                    for j, cell in enumerate(cells):
                        print(f"  欄位 {j}: {cell.get_text(strip=True)[:50]}")

    # 3. 檢查分頁
    print("\n3. 分頁資訊")
    page_info = soup.find(string=lambda text: '共有' in text if text else False)
    if page_info:
        print(f"分頁資訊: {page_info.strip()}")

    return response.text


def explore_detail_page():
    """探索詳細頁結構"""

    print("\n" + "=" * 70)
    print("探索裁罰案件詳細頁")
    print("=" * 70)

    # 詳細頁 URL（使用 WebFetch 找到的範例）
    url = "https://www.fsc.gov.tw/ch/home.jsp?id=131&parentpath=0,2&mcustomize=multimessages_view.jsp&dataserno=202509300001&dtable=Penalty"

    response = requests.get(url, verify=False, timeout=30)
    response.encoding = 'utf-8'

    soup = BeautifulSoup(response.text, 'html.parser')

    # 1. 內容區域
    print("\n1. 內容區域")
    content_selectors = [
        'div.page_content',
        'div.content',
        'div.maincontent',
        'div#inbody',
        'div.zbox'
    ]

    content_div = None
    for selector in content_selectors:
        content_div = soup.select_one(selector)
        if content_div:
            print(f"✓ 找到內容區域: {selector}")
            break

    if content_div:
        content_text = content_div.get_text(separator='\n', strip=True)
        print(f"\n內容長度: {len(content_text)} 字元")
        print(f"\n內容預覽（前 500 字元）:")
        print(content_text[:500])

    # 2. 檢查附件
    print("\n2. 附件資訊")
    attachments = []
    for link in soup.select('a'):
        href = link.get('href', '')
        if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx']):
            attachments.append({
                'name': link.get_text(strip=True),
                'url': urljoin(url, href),
                'type': href.split('.')[-1].split('&')[0].split('?')[0].lower()
            })

    print(f"找到 {len(attachments)} 個附件")
    for i, att in enumerate(attachments[:5], 1):
        print(f"\n附件 {i}:")
        print(f"  名稱: {att['name'][:50]}")
        print(f"  類型: {att['type']}")
        print(f"  URL: {att['url'][:80]}...")

    # 3. 結構化資料提取
    print("\n3. 結構化資料提取")

    # 提取發文字號
    doc_number = None
    for text in soup.stripped_strings:
        if '字第' in text and '號' in text:
            doc_number = text
            break

    print(f"發文字號: {doc_number if doc_number else '未找到'}")

    # 提取日期
    date_pattern = soup.find(string=lambda text: '中華民國' in text if text else False)
    print(f"發文日期: {date_pattern.strip() if date_pattern else '未找到'}")

    # 提取被處分人
    company_name = None
    for h3 in soup.find_all(['h2', 'h3', 'h4']):
        text = h3.get_text(strip=True)
        if '股份有限公司' in text or '有限公司' in text:
            company_name = text
            break

    print(f"被處分人: {company_name if company_name else '未找到'}")

    return response.text


def main():
    """主函數"""

    print("金管會裁罰案件頁面探索")
    print("=" * 70)

    # 探索列表頁
    list_html = explore_list_page()

    # 探索詳細頁
    detail_html = explore_detail_page()

    # 儲存 HTML 供檢查
    print("\n" + "=" * 70)
    print("儲存 HTML 檔案")
    print("=" * 70)

    with open('data/penalties_list_sample.html', 'w', encoding='utf-8') as f:
        f.write(list_html)
    print("✓ 列表頁: data/penalties_list_sample.html")

    with open('data/penalties_detail_sample.html', 'w', encoding='utf-8') as f:
        f.write(detail_html)
    print("✓ 詳細頁: data/penalties_detail_sample.html")

    print("\n完成！請檢查輸出的 HTML 檔案來確認結構")


if __name__ == '__main__':
    main()
