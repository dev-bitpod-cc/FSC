"""法令函釋爬蟲 - 使用 POST 請求處理分頁"""

from typing import List, Dict, Any, Optional
import time
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseFSCCrawler
from ..utils.helpers import (
    clean_text,
    parse_date,
    normalize_url,
    generate_id
)


class LawInterpretationsCrawler(BaseFSCCrawler):
    """法令函釋爬蟲 (使用 POST 表單)"""

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
            'id': '128',  # 法令函釋的 ID
            'contentid': '128',
            'parentpath': '0,3',
            'mcustomize': 'lawnew_list.jsp',
            'page': '1',
            'pagesize': '15',  # 每頁15筆
        }

        # 附件下載配置
        self.attachments_config = config.get('attachments', {})
        self.download_attachments = self.attachments_config.get('download', True)
        self.attachment_types = self.attachments_config.get('types', ['pdf', 'odt', 'doc', 'docx'])
        self.attachment_base_path = Path(self.attachments_config.get('save_path', 'data/attachments'))
        self.max_attachment_size = self.attachments_config.get('max_size_mb', 50) * 1024 * 1024  # 轉換為 bytes

        # 禁用 SSL 驗證 (金管會憑證問題)
        self.session.verify = False

        # 禁用警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        logger.info("LawInterpretationsCrawler 初始化成功")

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

        # 選擇所有函釋列
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

                # 從 URL 提取 dataserno
                dataserno = self._extract_dataserno(detail_url)

                item = {
                    'list_index': no,
                    'date': date,
                    'source_raw': unit,  # 原始來源名稱
                    'title': title,
                    'detail_url': detail_url,
                    'dataserno': dataserno,
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
        data = {
            **list_item,  # 包含列表頁資料
        }

        # 識別函釋類型
        category = self._identify_category(data['title'])

        # 提取 metadata
        data['metadata'] = self._extract_metadata(soup, data['title'])

        # 將 category 存入 metadata
        data['metadata']['category'] = category

        # 標準化來源單位
        data['metadata']['source'] = self._standardize_source(data.get('source_raw', ''))

        # 提取正文內容
        content_div = soup.select_one('div.zbox') or soup.select_one('div.page-edit') or soup.select_one('div.ap')
        if content_div:
            # 移除社群分享按鈕、友善列印等雜訊
            for noise in content_div.select('.shares, .social-share, script, style'):
                noise.decompose()

            # 提取純文字和 HTML
            text_content = clean_text(content_div.get_text())
            html_content = str(content_div)[:10000]  # 限制長度

            data['content'] = {
                'text': text_content,
                'html': html_content
            }
        else:
            logger.warning(f"未找到內容區域: {data['title']}")
            data['content'] = {'text': '', 'html': ''}

        # 提取附件
        data['attachments'] = self._extract_attachments(soup, data)

        # 生成 ID
        dataserno = data.get('dataserno')
        if dataserno:
            data['id'] = f"fsc_law_{dataserno}"
        else:
            data['id'] = generate_id('fsc_law', data['date'])

        return data

    def _extract_dataserno(self, url: str) -> Optional[str]:
        """從 URL 提取 dataserno"""
        if not url:
            return None

        try:
            # 解析 URL 參數
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            dataserno = params.get('dataserno', [None])[0]
            return dataserno
        except Exception as e:
            logger.error(f"提取 dataserno 失敗: {e}")
            return None

    def _identify_category(self, title: str) -> str:
        """
        識別函釋類型

        Args:
            title: 標題

        Returns:
            類型代碼
        """
        if not title:
            return 'unknown'

        # 優先匹配（避免誤判）
        if title.startswith('修正'):
            return 'amendment'  # 修正型
        elif title.startswith('訂定'):
            if '解釋令' in title:
                return 'interpretation_decree'  # 解釋令（訂定型子類）
            return 'enactment'  # 訂定型
        elif title.startswith('有關'):
            return 'clarification'  # 函釋型（有關）
        elif title.startswith('廢止'):
            return 'repeal'  # 廢止型
        elif title.startswith('發布') or title.startswith('公布'):
            return 'announcement'  # 發布/公布型
        elif title.startswith('指定') or title.startswith('核准'):
            return 'approval'  # 核准/指定型
        elif title.startswith('調降') or title.startswith('調整'):
            return 'adjustment'  # 調整型
        elif title.startswith('公告'):
            return 'notice'  # 公告型
        else:
            return 'other'

    def _extract_metadata(self, soup: BeautifulSoup, title: str) -> Dict[str, Any]:
        """
        提取 metadata

        Args:
            soup: BeautifulSoup 物件
            title: 標題

        Returns:
            metadata 字典
        """
        metadata = {}

        # 提取發文字號（從標題或正文）
        # 格式：(金管X字第XXXXXXXX號)
        doc_number_match = re.search(r'\(([^)]+字第[^)]+號)\)', title)
        if doc_number_match:
            metadata['document_number'] = doc_number_match.group(1)
        else:
            # 從正文中找
            content = soup.get_text()
            doc_number_match = re.search(r'發文字號[：:]\s*([^\n]+)', content)
            if doc_number_match:
                metadata['document_number'] = clean_text(doc_number_match.group(1))

        # 提取法規名稱（從標題）
        # 格式：修正「法規名稱」第X條
        law_name_match = re.search(r'[「《]([^」》]+)[」》]', title)
        if law_name_match:
            metadata['law_name'] = law_name_match.group(1)

        # 提取修正條文（修正型）
        if title.startswith('修正'):
            articles_match = re.findall(r'第([零一二三四五六七八九十百千\d]+(?:之\d+)?)條', title)
            if articles_match:
                metadata['amended_articles'] = self._normalize_articles(articles_match)

        # 提取法條引用（函釋型）
        if title.startswith('有關'):
            law_ref_match = re.search(r'([^「]*?)第([零一二三四五六七八九十百千\d]+(?:之\d+)?)條', title)
            if law_ref_match:
                metadata['law_reference'] = f"{law_ref_match.group(1).strip()}第{law_ref_match.group(2)}條"

        return metadata

    def _standardize_source(self, source_raw: str) -> str:
        """
        標準化來源單位

        Args:
            source_raw: 原始來源名稱

        Returns:
            標準化代碼
        """
        from ..utils.config_loader import ConfigLoader

        config_loader = ConfigLoader()
        source_mapping = config_loader.get_source_unit_mapping()

        return source_mapping.get(source_raw, 'unknown')

    def _normalize_articles(self, articles: List[str]) -> List[int]:
        """
        標準化條文編號（將中文數字轉換為阿拉伯數字）

        Args:
            articles: 條文編號列表（可能包含中文數字）

        Returns:
            標準化的條文編號列表
        """
        chinese_to_arabic = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '十': 10, '百': 100, '千': 1000
        }

        normalized = []
        for article in articles:
            try:
                # 如果已經是數字（或包含 "之"），直接處理
                if re.match(r'^\d+(?:之\d+)?$', article):
                    # 提取數字部分（忽略 "之X"）
                    main_num = re.match(r'^(\d+)', article).group(1)
                    normalized.append(int(main_num))
                else:
                    # 簡單的中文數字轉換（只處理常見情況）
                    if article in chinese_to_arabic:
                        normalized.append(chinese_to_arabic[article])
            except Exception as e:
                logger.warning(f"無法標準化條文編號: {article} - {e}")

        return sorted(list(set(normalized)))  # 去重並排序

    def _extract_attachments(self, soup: BeautifulSoup, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        提取附件資訊

        Args:
            soup: BeautifulSoup 物件
            data: 函釋資料

        Returns:
            附件列表
        """
        attachments = []

        # 尋找附件連結（通常在 ul > li > a 中）
        # 路徑：/uploaddowndoc?file=newslaw/...
        attachment_links = soup.select('a[href*="uploaddowndoc"]')

        for link in attachment_links:
            try:
                href = link.get('href')
                if not href:
                    continue

                # 完整 URL
                full_url = urljoin(self.base_url, href)

                # 提取檔案名稱（從 filedisplay 參數或連結文字）
                params = parse_qs(urlparse(full_url).query)
                display_name = params.get('filedisplay', [None])[0]

                if display_name:
                    # URL decode
                    from urllib.parse import unquote
                    display_name = unquote(display_name)
                else:
                    # 從連結文字取得
                    display_name = clean_text(link.get_text())

                if not display_name:
                    continue

                # 判斷檔案類型
                file_ext = self._get_file_extension(display_name, href)

                if file_ext not in self.attachment_types:
                    logger.debug(f"跳過不支援的附件類型: {file_ext} - {display_name}")
                    continue

                # 判斷附件類別（對照表、修正條文等）
                attachment_classification = self._classify_attachment(display_name, data.get('metadata', {}).get('category', 'unknown'))

                attachment = {
                    'name': display_name,
                    'url': full_url,
                    'type': file_ext,
                    'classification': attachment_classification
                }

                attachments.append(attachment)

            except Exception as e:
                logger.error(f"提取附件失敗: {e}")
                import traceback
                logger.error(traceback.format_exc())

        logger.info(f"找到 {len(attachments)} 個附件")
        return attachments

    def _get_file_extension(self, filename: str, url: str) -> str:
        """
        取得檔案副檔名

        Args:
            filename: 檔案名稱
            url: URL

        Returns:
            副檔名（小寫，不含點）
        """
        # 從檔案名稱提取
        if '.' in filename:
            ext = filename.rsplit('.', 1)[1].lower()
            return ext

        # 從 URL 提取
        # 格式：file=newslaw/202511141711260.odt
        match = re.search(r'\.(\w+)', url)
        if match:
            return match.group(1).lower()

        return 'unknown'

    def _classify_attachment(self, filename: str, law_interpretation_category: str) -> str:
        """
        分類附件

        Args:
            filename: 檔案名稱
            category: 函釋類型

        Returns:
            附件類別
        """
        filename_lower = filename.lower()

        if '對照表' in filename or 'comparison' in filename_lower:
            return 'comparison_table'
        elif '總說明' in filename or 'explanation' in filename_lower:
            return 'explanation'
        elif '修正條文' in filename and '對照表' not in filename:
            return 'amended_text'
        elif '訂定條文' in filename or '新訂' in filename:
            return 'enacted_text'
        elif '解釋令' in filename:
            return 'interpretation'
        else:
            return 'other'

    def download_attachment(self, attachment: Dict[str, Any], save_dir: Path) -> Optional[Path]:
        """
        下載附件

        Args:
            attachment: 附件資訊
            save_dir: 儲存目錄

        Returns:
            檔案路徑或 None
        """
        if not self.download_attachments:
            return None

        try:
            url = attachment['url']
            filename = attachment['name']

            # 建立儲存目錄
            save_dir.mkdir(parents=True, exist_ok=True)

            # 生成檔案路徑
            # 清理檔案名稱（移除非法字元）
            safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            file_path = save_dir / safe_filename

            # 如果檔案已存在且大小合理，跳過
            if file_path.exists() and file_path.stat().st_size > 0:
                logger.debug(f"附件已存在，跳過下載: {file_path.name}")
                return file_path

            # 下載檔案
            logger.info(f"下載附件: {filename}")
            response = self.fetch_with_retry(url, method='GET', stream=True)

            if not response:
                logger.error(f"下載附件失敗: {filename}")
                return None

            # 檢查檔案大小
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.max_attachment_size:
                logger.warning(f"附件過大，跳過: {filename} ({int(content_length) / 1024 / 1024:.2f} MB)")
                return None

            # 儲存檔案
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"附件下載完成: {file_path.name} ({file_path.stat().st_size / 1024:.2f} KB)")
            return file_path

        except Exception as e:
            logger.error(f"下載附件失敗: {attachment.get('name', 'unknown')} - {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def crawl_page(self, page: int, **kwargs) -> List[Dict[str, Any]]:
        """
        爬取單頁

        Args:
            page: 頁碼

        Returns:
            資料列表
        """
        logger.info(f"爬取第 {page} 頁...")

        # 更新表單頁碼
        form_data = self.form_data.copy()
        form_data['page'] = str(page)

        # 發送 POST 請求
        response = self.fetch_with_retry(
            self.list_url,
            method='POST',
            data=form_data
        )

        if not response:
            logger.error(f"爬取第 {page} 頁失敗")
            return []

        # 解析列表頁
        list_items = self.parse_list_page(response.text)

        if not list_items:
            logger.warning(f"第 {page} 頁無資料")
            return []

        # 爬取詳細頁
        results = []
        for item in list_items:
            try:
                detail_url = item.get('detail_url')
                if not detail_url:
                    continue

                logger.info(f"爬取詳細頁: {item['title'][:50]}...")

                # 請求延遲
                time.sleep(self.request_interval)

                # 發送請求
                detail_response = self.fetch_with_retry(detail_url, method='GET')
                if not detail_response:
                    continue

                # 解析詳細頁
                detail_data = self.parse_detail_page(detail_response.text, item)

                # 下載附件
                if detail_data.get('attachments'):
                    attachment_dir = self.attachment_base_path / 'law_interpretations' / detail_data['id']
                    for attachment in detail_data['attachments']:
                        file_path = self.download_attachment(attachment, attachment_dir)
                        if file_path:
                            attachment['local_path'] = str(file_path)

                results.append(detail_data)

            except Exception as e:
                logger.error(f"處理詳細頁失敗: {item.get('title', 'unknown')} - {e}")
                import traceback
                logger.error(traceback.format_exc())

        return results

    def crawl_all(self, max_pages: Optional[int] = None, start_page: int = 1) -> List[Dict[str, Any]]:
        """
        爬取所有頁面

        Args:
            max_pages: 最大頁數（None 表示爬取所有）
            start_page: 起始頁碼

        Returns:
            所有資料
        """
        all_data = []
        page = start_page

        while True:
            if max_pages and page >= start_page + max_pages:
                break

            try:
                page_data = self.crawl_page(page)

                if not page_data:
                    logger.info("無更多資料，停止爬取")
                    break

                all_data.extend(page_data)
                logger.info(f"已爬取 {len(all_data)} 筆資料")

                page += 1

            except Exception as e:
                logger.error(f"爬取第 {page} 頁時發生錯誤: {e}")
                break

        logger.info(f"爬取完成！總共 {len(all_data)} 筆資料")
        return all_data
