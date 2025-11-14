"""裁罰案件爬蟲 - 使用 POST 請求處理分頁"""

from typing import List, Dict, Any, Optional
import time
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseFSCCrawler
from ..utils.helpers import (
    clean_text,
    parse_date,
    normalize_url,
    generate_id,
    extract_penalty_amount,
    extract_legal_basis,
    extract_inspection_report_number,
    detect_penalty_category,
    extract_penalized_entity_type
)


class PenaltyCrawler(BaseFSCCrawler):
    """裁罰案件爬蟲 (使用 POST 表單)"""

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
            'id': '131',  # 裁罰案件的 ID
            'contentid': '131',
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

        logger.info("PenaltyCrawler 初始化成功")

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

        # 選擇所有裁罰列（與公告結構相同）
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

            # 過濾掉不相關的通用附件（金管會網頁側邊欄/頁尾的通用連結）
            irrelevant_attachment_keywords = [
                '失智者經濟安全保障推動計畫',
                '金管會永續發展目標自願檢視報告',
                '永續發展目標',
                '經濟安全保障'
            ]

            # 只從內容區域抓取附件（避免抓到側邊欄/頁尾的連結）
            attachment_links = []
            if content_div:
                attachment_links = content_div.select('a')
            else:
                # 如果沒有找到內容區域，仍然從整個頁面抓取，但會過濾
                attachment_links = soup.select('a')

            for link in attachment_links:
                href = link.get('href', '')
                link_text = clean_text(link.get_text())

                # 檢查是否為文件連結
                if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.odt']):
                    # 過濾掉不相關的附件
                    if any(keyword in link_text for keyword in irrelevant_attachment_keywords):
                        logger.debug(f"過濾掉不相關附件: {link_text}")
                        continue

                    # 提取檔案類型（處理 URL 參數如 .pdf&flag=doc）
                    file_type = 'unknown'
                    if '.' in href:
                        # 取得副檔名部分
                        ext_part = href.split('.')[-1].lower()
                        # 如果有 URL 參數（&），只取第一部分
                        if '&' in ext_part:
                            file_type = ext_part.split('&')[0]
                        elif '?' in ext_part:
                            file_type = ext_part.split('?')[0]
                        else:
                            file_type = ext_part

                    attachments.append({
                        'name': link_text,
                        'url': urljoin(self.base_url, href),
                        'type': file_type
                    })

            detail['attachments'] = attachments

            # 下載附件（如果配置啟用）
            if attachments and self.config.get('attachments', {}).get('download', False):
                self._download_attachments(detail)

            # 提取 metadata（裁罰案件特有）
            from ..utils.config_loader import ConfigLoader

            config_loader = ConfigLoader()
            penalty_category_mapping = config_loader.get_penalty_category_mapping()
            source_mapping = config_loader.get_source_unit_mapping()

            # 完整文字（用於提取）
            full_text = soup.get_text()

            # 發文字號（與公告相同的邏輯）
            doc_number = None
            for text in soup.stripped_strings:
                if '字第' in text and '號' in text:
                    doc_number = text.strip()
                    break

            # 處分金額
            penalty_amount, penalty_amount_text = extract_penalty_amount(full_text)

            # 法條依據
            legal_basis = extract_legal_basis(full_text)

            # 檢查報告編號
            inspection_report = extract_inspection_report_number(full_text)

            # 違規類型
            category = detect_penalty_category(detail['title'], full_text, penalty_category_mapping)

            # 被處分人資訊
            penalized_entity = {
                'name': None,
                'type': extract_penalized_entity_type(detail['source_raw'], detail['title']),
                'tax_id': None
            }

            # 從標題或內容提取被處分人名稱
            # 通常格式為：「XXX股份有限公司...」或「XXX銀行...」
            company_patterns = [
                r'([^\s，。]+(?:股份有限公司|有限公司|商業銀行|銀行|保險|證券|投信|投顧))',
            ]

            for pattern in company_patterns:
                match = re.search(pattern, detail['title'])
                if match:
                    penalized_entity['name'] = match.group(1)
                    break

            # 提取統一編號（通常在詳細頁中）
            tax_id_match = re.search(r'統一編號[：:]\s*(\d{8}|略)', full_text)
            if tax_id_match:
                penalized_entity['tax_id'] = tax_id_match.group(1)

            # 違規事實摘要（從標題提取）
            violation_summary = detail['title']
            if '所列' in violation_summary:
                # 提取「所列」之後的部分作為摘要
                parts = violation_summary.split('所列')
                if len(parts) > 1:
                    violation_summary = parts[1].split('，')[0].split('。')[0]

            # 來源單位標準化
            source = source_mapping.get(detail['source_raw'], 'unknown')

            detail['metadata'] = {
                'doc_number': doc_number,
                'penalized_entity': penalized_entity,
                'penalty_amount': penalty_amount,
                'penalty_amount_text': penalty_amount_text,
                'violation': {
                    'summary': violation_summary,
                    'details': content_text[:1000] if content_text else ''  # 前1000字元作為詳情
                },
                'legal_basis': legal_basis,
                'inspection_report': inspection_report,
                'source': source,
                'category': category
            }

        except Exception as e:
            logger.error(f"解析詳細頁失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())

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

    def _download_attachments(self, detail: Dict[str, Any]) -> None:
        """
        下載附件（與 AnnouncementCrawler 相同的邏輯）

        Args:
            detail: 裁罰案件詳細資料（會直接修改其中的 attachments）
        """
        from pathlib import Path
        import time

        att_config = self.config.get('attachments', {})
        allowed_types = att_config.get('types', ['pdf', 'doc', 'docx'])
        max_size_mb = att_config.get('max_size_mb', 50)
        save_path = Path(att_config.get('save_path', 'data/attachments'))
        max_retries = att_config.get('max_retries', 3)

        # 建立附件目錄
        doc_id = detail.get('id', 'unknown')
        att_dir = save_path / 'penalties' / doc_id
        att_dir.mkdir(parents=True, exist_ok=True)

        for i, att in enumerate(detail.get('attachments', []), 1):
            att_type = att.get('type', 'unknown')
            att_url = att.get('url', '')
            att_name = att.get('name', 'unknown')

            # 檢查是否為允許的類型
            if att_type not in allowed_types:
                logger.debug(f"跳過不支援的附件類型: {att_type} - {att_name}")
                continue

            # 檔名
            safe_filename = f"attachment_{i}.{att_type}"
            filepath = att_dir / safe_filename

            # 重試下載
            for retry in range(max_retries):
                try:
                    if retry > 0:
                        logger.info(f"重試下載 ({retry}/{max_retries}): {att_name}")
                        time.sleep(2 ** retry)  # Exponential backoff

                    # 下載
                    response = self.session.get(
                        att_url,
                        verify=False,
                        timeout=self.config['http']['timeout'],
                        stream=True
                    )
                    response.raise_for_status()

                    # 檢查檔案大小
                    content_length = response.headers.get('content-length')
                    if content_length:
                        size_mb = int(content_length) / (1024 * 1024)
                        if size_mb > max_size_mb:
                            logger.warning(f"附件超過大小限制 ({size_mb:.1f} MB > {max_size_mb} MB): {att_name}")
                            att['download_error'] = f'檔案過大 ({size_mb:.1f} MB)'
                            break

                    # 儲存
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    # 記錄下載資訊
                    file_size = filepath.stat().st_size
                    att['local_path'] = str(filepath)
                    att['size_bytes'] = file_size
                    att['downloaded'] = True

                    logger.info(f"✓ 下載附件 [{i}]: {att_name} ({file_size / 1024:.1f} KB)")
                    break  # 成功，跳出重試迴圈

                except Exception as e:
                    if retry == max_retries - 1:
                        # 最後一次重試也失敗
                        logger.error(f"✗ 下載附件失敗 [{i}]: {att_name} - {e}")
                        att['download_error'] = str(e)
                        att['downloaded'] = False
                    else:
                        logger.warning(f"下載失敗 (重試 {retry + 1}/{max_retries}): {att_name} - {e}")
