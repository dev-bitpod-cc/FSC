"""重要公告爬蟲 - 使用 POST 請求處理分頁"""

from typing import List, Dict, Any, Optional
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseFSCCrawler
from ..utils.helpers import clean_text, parse_date, normalize_url, generate_id


class AnnouncementCrawler(BaseFSCCrawler):
    """重要公告爬蟲 (使用 POST 表單)"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化爬蟲

        Args:
            config: 配置字典
        """
        super().__init__(config)

        self.base_url = "https://www.fsc.gov.tw/ch/"
        self.list_url = "https://www.fsc.gov.tw/ch/home.jsp"

        # POST 表單參數
        self.form_data = {
            'id': '97',
            'contentid': '97',
            'parentpath': '0,2',
            'mcustomize': 'multimessage_list.jsp',
            'page': '1',
            'pagesize': '15',  # 每頁15筆
        }

        # 禁用 SSL 驗證 (金管會憑證問題)
        self.session.verify = False

        # 禁用警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        logger.info("AnnouncementCrawler 初始化成功")

    def get_list_url(self, page: int, **kwargs) -> str:
        """
        生成列表頁 URL

        Args:
            page: 頁碼

        Returns:
            列表頁 URL
        """
        return self.list_url

    def parse_list_page(self, html: str) -> List[Dict[str, Any]]:
        """
        解析列表頁

        Args:
            html: HTML 內容

        Returns:
            資料列表
        """
        soup = BeautifulSoup(html, 'html.parser')
        items = []

        # 選擇所有公告列
        rows = soup.select('li[role="row"]')

        logger.debug(f"找到 {len(rows)} 個 li[role='row'], 跳過表頭後: {len(rows[1:])}")

        # 跳過第一個 (表頭)
        for row in rows[1:]:
            try:
                # 提取欄位
                no_elem = row.select_one('span.no')
                date_elem = row.select_one('span.date')
                unit_elem = row.select_one('span.unit')
                link_elem = row.select_one('span.title > a')

                if not link_elem:
                    logger.debug(f"跳過: 無 link_elem")
                    continue

                # 編號
                no = clean_text(no_elem.get_text()) if no_elem else None

                # 日期
                date_str = clean_text(date_elem.get_text()) if date_elem else None
                date = parse_date(date_str) if date_str else None

                # 來源單位
                unit = clean_text(unit_elem.get_text()) if unit_elem else None

                # 標題與連結
                title = link_elem.get('title') or clean_text(link_elem.get_text())
                href = link_elem.get('href')

                # 完整 URL
                detail_url = urljoin(self.base_url, href) if href else None

                item = {
                    'list_index': no,
                    'date': date,
                    'source_raw': unit,  # 原始來源名稱
                    'title': title,
                    'detail_url': detail_url,
                    'list_url': self.list_url
                }

                items.append(item)

            except Exception as e:
                logger.error(f"解析列表項失敗: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        return items

    def parse_detail_page(self, html: str, list_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析詳細頁

        Args:
            html: HTML 內容
            list_item: 列表頁的項目資料

        Returns:
            完整的資料
        """
        soup = BeautifulSoup(html, 'html.parser')

        # 基本資料
        detail = list_item.copy()

        try:
            # 提取內容 - 嘗試多種選擇器
            content_div = None

            # 嘗試常見的內容容器
            for selector in [
                'div.page_content',
                'div.content',
                'div.article',
                'div#content',
                'div.main-content',
                'div.zbox'
            ]:
                content_div = soup.select_one(selector)
                if content_div:
                    break

            if content_div:
                # 提取純文字
                content_text = content_div.get_text(separator='\n', strip=True)

                # 保留 HTML (截短以節省空間)
                content_html = str(content_div)[:5000]  # 只保留前5000字元

                detail['content'] = {
                    'text': content_text,
                    'html': content_html
                }
            else:
                logger.warning(f"未找到內容區域: {list_item.get('detail_url', 'N/A')}")
                detail['content'] = {
                    'text': '',
                    'html': ''
                }

            # 提取附件
            attachments = []
            for link in soup.select('a'):
                href = link.get('href', '')
                if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.odt']):
                    attachments.append({
                        'name': clean_text(link.get_text()),
                        'url': urljoin(self.base_url, href),
                        'type': href.split('.')[-1].lower() if '.' in href else 'unknown'
                    })

            detail['attachments'] = attachments

            # 提取 metadata
            from ..utils.helpers import extract_announcement_number, detect_category
            from ..utils.config_loader import ConfigLoader

            config_loader = ConfigLoader()
            category_mapping = config_loader.get_category_mapping()

            # 公告文號
            full_text = soup.get_text()
            announcement_number = extract_announcement_number(full_text)

            # 公告類型
            category = detect_category(detail['title'], category_mapping)

            # 來源單位標準化
            source_mapping = config_loader.get_source_unit_mapping()
            source = source_mapping.get(detail['source_raw'], 'unknown')

            detail['metadata'] = {
                'announcement_number': announcement_number,
                'category': category,
                'source': source  # 標準化後的來源
            }

        except Exception as e:
            logger.error(f"解析詳細頁失敗: {e}")

        return detail

    def crawl_page(self, page: int, **kwargs) -> List[Dict[str, Any]]:
        """
        爬取單頁列表 (使用 POST 請求)

        Args:
            page: 頁碼
            **kwargs: 其他參數

        Returns:
            該頁的資料列表
        """
        logger.info(f"爬取列表頁: Page {page}")

        # 準備 POST 資料
        form_data = self.form_data.copy()
        form_data['page'] = str(page)

        # 發送 POST 請求
        response = self.fetch_with_retry(
            self.list_url,
            method='POST',
            data=form_data
        )

        if not response:
            logger.error(f"列表頁請求失敗: Page {page}")
            return []

        # 解析
        try:
            items = self.parse_list_page(response.text)
            logger.info(f"列表頁解析成功: Page {page} - 找到 {len(items)} 筆資料")

            # 添加頁碼資訊
            for item in items:
                item['page'] = page

            return items

        except Exception as e:
            logger.error(f"列表頁解析失敗: Page {page} - {e}")
            return []
