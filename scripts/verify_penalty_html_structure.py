"""
驗證裁罰案件頁面的 HTML 結構
檢查內容選擇器和附件位置
"""

import requests
from bs4 import BeautifulSoup
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 測試 URL
TEST_URL = "https://www.fsc.gov.tw/ch/home.jsp?id=131&parentpath=0,2&mcustomize=multimessage_view.jsp&dataserno=202509300001&dtable=Penalty&aplistdn=ou=data,ou=penalty,ou=multisite,ou=chinese,ou=ap_root,o=fsc,c=tw"

def main():
    print("=" * 70)
    print("驗證裁罰案件頁面 HTML 結構")
    print("=" * 70)
    print(f"\n測試 URL: {TEST_URL}\n")

    # 抓取頁面
    print("正在抓取頁面...")
    response = requests.get(TEST_URL, verify=False)
    response.encoding = 'utf-8'
    html = response.text

    soup = BeautifulSoup(html, 'html.parser')

    # 測試各種內容選擇器
    print("\n1. 測試內容選擇器:")
    print("-" * 70)

    selectors = [
        'div.page_content',
        'div.content',
        'div.article',
        'div#content',
        'div.main-content',
        'div.zbox'
    ]

    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            text_preview = elem.get_text()[:200].replace('\n', ' ').strip()
            print(f"✓ {selector:20s} 找到! 內容預覽: {text_preview}...")
        else:
            print(f"✗ {selector:20s} 未找到")

    # 檢查附件連結位置
    print("\n\n2. 分析所有 PDF 連結的位置:")
    print("-" * 70)

    all_pdf_links = soup.select('a[href*=".pdf"]')
    print(f"總共找到 {len(all_pdf_links)} 個 PDF 連結\n")

    # 檢查每個連結是否在 div.zbox 內
    content_div = soup.select_one('div.zbox')

    if content_div:
        for i, link in enumerate(all_pdf_links, 1):
            link_text = link.get_text().strip()
            href = link.get('href', '')

            # 檢查是否在內容區域內
            is_inside = link in content_div.select('a')
            location = "內容區域內" if is_inside else "內容區域外（側邊欄/頁尾）"

            print(f"{i}. {location}")
            print(f"   文字: {link_text}")
            print(f"   URL:  {href[:80]}...")
            print()

    # 檢查內容區域內的所有連結
    print("\n3. 內容區域 (div.zbox) 內的所有文件連結:")
    print("-" * 70)

    if content_div:
        content_links = content_div.select('a')
        doc_links = [
            link for link in content_links
            if any(ext in link.get('href', '').lower()
                   for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx'])
        ]

        print(f"內容區域內共有 {len(doc_links)} 個文件連結\n")

        for i, link in enumerate(doc_links, 1):
            link_text = link.get_text().strip()
            href = link.get('href', '')
            print(f"{i}. {link_text}")
            print(f"   {href[:80]}...")
            print()

    # 保存 HTML 供檢查
    output_file = 'data/temp_penalty_page.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n完整 HTML 已保存到: {output_file}")
    print("=" * 70)

if __name__ == '__main__':
    main()
