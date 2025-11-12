"""Gemini File Search 上傳器"""

import os
import time
import json
import shutil
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

try:
    from google import genai
    from google.genai import types
except ImportError:
    logger.warning("google-genai 套件未安裝,請執行: pip install google-genai")
    genai = None
    types = None


class GeminiUploader:
    """Gemini File Search 上傳器"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        store_name: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        初始化上傳器

        Args:
            api_key: Gemini API Key (預設從環境變數讀取)
            store_name: File Search Store 名稱
            max_retries: 上傳失敗時最大重試次數
            retry_delay: 重試延遲基數 (秒),使用 exponential backoff
        """
        if genai is None:
            raise ImportError("請先安裝 google-genai: pip install google-genai")

        # 從環境變數或參數取得 API Key
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("未設定 GEMINI_API_KEY,請在 .env 檔案中設定或傳入參數")

        # Store 名稱
        self.store_name = store_name or os.getenv('FILE_SEARCH_STORE_NAME', 'fsc-announcements')

        # 初始化 Gemini 客戶端
        self.client = genai.Client(api_key=self.api_key)

        # Store ID (稍後建立或取得)
        self.store_id = None

        # 配置參數
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # 統計資訊
        self.stats = {
            'total_files': 0,
            'uploaded_files': 0,
            'failed_files': 0,
            'total_bytes': 0,
            'skipped_files': 0,
        }

        # 暫存目錄 (用於上傳狀態記錄)
        self.temp_dir = Path('data/temp_uploads')
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # 上傳狀態記錄
        self.manifest_file = self.temp_dir / 'upload_manifest.json'
        self.manifest = self._load_manifest()

        logger.info(f"GeminiUploader 初始化成功: Store名稱={self.store_name}")
        logger.info(f"配置: 最大重試{max_retries}次, 延遲基數{retry_delay}秒")

    def _load_manifest(self) -> Dict[str, Any]:
        """載入上傳狀態記錄"""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"載入 manifest 失敗: {e}")
        return {
            'uploaded': {},  # {filepath: {'file_id': ..., 'timestamp': ..., 'status': 'success/failed'}}
        }

    def _save_manifest(self):
        """儲存上傳狀態記錄"""
        try:
            with open(self.manifest_file, 'w', encoding='utf-8') as f:
                json.dump(self.manifest, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"儲存 manifest 失敗: {e}")

    def get_or_create_store(self) -> str:
        """
        取得或建立 File Search Store

        Returns:
            Store ID
        """
        try:
            # 列出現有 Stores
            logger.info("檢查現有 File Search Stores...")
            stores = list(self.client.file_search_stores.list())

            # 尋找同名 Store
            for store in stores:
                if store.display_name == self.store_name:
                    self.store_id = store.name
                    logger.info(f"找到現有 Store: {self.store_id}")
                    return self.store_id

            # 建立新 Store
            logger.info(f"建立新 Store: {self.store_name}")
            store = self.client.file_search_stores.create(
                config=types.CreateFileSearchStoreConfig(
                    display_name=self.store_name
                )
            )
            self.store_id = store.name
            logger.info(f"Store 建立成功: {self.store_id}")

            return self.store_id

        except Exception as e:
            logger.error(f"取得/建立 Store 失敗: {e}")
            raise

    def upload_file(self, filepath: str, display_name: Optional[str] = None) -> Optional[str]:
        """
        上傳單一檔案到 Gemini (帶自動重試)

        Args:
            filepath: 檔案路徑
            display_name: 顯示名稱 (預設使用檔名)

        Returns:
            File ID 或 None (失敗時)
        """
        filepath_obj = Path(filepath)

        if not filepath_obj.exists():
            logger.error(f"檔案不存在: {filepath}")
            self.stats['failed_files'] += 1
            return None

        # 顯示名稱
        if not display_name:
            display_name = filepath_obj.name

        # 重試機制
        for attempt in range(self.max_retries):
            try:
                # 上傳檔案
                if attempt == 0:
                    logger.info(f"上傳檔案: {display_name}")
                else:
                    logger.info(f"重試上傳 (第 {attempt + 1}/{self.max_retries} 次): {display_name}")

                with open(filepath, 'rb') as f:
                    file_obj = self.client.files.upload(
                        file=f,
                        config=types.UploadFileConfig(
                            display_name=display_name,
                            mime_type='text/markdown'
                        )
                    )

                logger.info(f"檔案上傳成功: {file_obj.name} (URI: {file_obj.uri})")

                # 更新統計
                self.stats['uploaded_files'] += 1
                self.stats['total_bytes'] += filepath_obj.stat().st_size

                # 記錄到 manifest
                self.manifest['uploaded'][str(filepath)] = {
                    'file_id': file_obj.name,
                    'timestamp': time.time(),
                    'status': 'success',
                    'display_name': display_name
                }
                self._save_manifest()

                return file_obj.name

            except Exception as e:
                logger.warning(f"上傳失敗 (嘗試 {attempt + 1}/{self.max_retries}): {e}")

                # 如果還有重試次數,等待後再試
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 2, 4, 8 秒...
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"等待 {delay:.1f} 秒後重試...")
                    time.sleep(delay)
                else:
                    # 已達最大重試次數
                    logger.error(f"上傳檔案失敗 (已重試 {self.max_retries} 次): {filepath} - {e}")
                    self.stats['failed_files'] += 1

                    # 記錄到 manifest
                    self.manifest['uploaded'][str(filepath)] = {
                        'file_id': None,
                        'timestamp': time.time(),
                        'status': 'failed',
                        'error': str(e),
                        'display_name': display_name
                    }
                    self._save_manifest()

                    return None

        return None

    def add_file_to_store(self, file_id: str):
        """
        將檔案加入 Store

        Args:
            file_id: 檔案 ID
        """
        try:
            if not self.store_id:
                self.get_or_create_store()

            logger.info(f"將檔案加入 Store: {file_id}")

            self.client.file_search_stores.import_file(
                file_search_store_name=self.store_id,
                file_name=file_id
            )

            logger.info(f"檔案已加入 Store")

        except Exception as e:
            logger.error(f"加入 Store 失敗: {file_id} - {e}")
            raise

    def upload_and_add(self, filepath: str, display_name: Optional[str] = None, delay: float = 1.0) -> bool:
        """
        上傳檔案並加入 Store (帶重試機制)

        Args:
            filepath: 檔案路徑
            display_name: 顯示名稱
            delay: 延遲秒數 (避免 API 限制)

        Returns:
            是否成功
        """
        # 重試機制 (整個 upload + add 流程)
        for attempt in range(self.max_retries):
            try:
                # 上傳檔案
                file_id = self.upload_file(filepath, display_name)

                if not file_id:
                    # upload_file 已經有重試機制,如果仍失敗則不再重試
                    return False

                # 延遲 (等待檔案處理,503 錯誤可能是檔案尚未就緒)
                time.sleep(delay)

                # 加入 Store (這裡可能會遇到 503)
                if attempt == 0:
                    logger.info(f"將檔案加入 Store: {file_id}")
                else:
                    logger.info(f"重試加入 Store (第 {attempt + 1}/{self.max_retries} 次): {file_id}")

                self.client.file_search_stores.import_file(
                    file_search_store_name=self.store_id,
                    file_name=file_id
                )

                logger.info(f"檔案已加入 Store")
                return True

            except Exception as e:
                logger.warning(f"加入 Store 失敗 (嘗試 {attempt + 1}/{self.max_retries}): {e}")

                # 如果還有重試次數,等待後再試
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 2, 4, 8 秒...
                    retry_delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"等待 {retry_delay:.1f} 秒後重試...")
                    time.sleep(retry_delay)
                else:
                    # 已達最大重試次數
                    logger.error(f"上傳並加入 Store 失敗 (已重試 {self.max_retries} 次): {filepath} - {e}")
                    return False

        return False

    def upload_batch(
        self,
        filepaths: List[str],
        delay: float = 1.0,
        skip_existing: bool = True
    ) -> Dict[str, Any]:
        """
        批次上傳多個檔案 (支援重試、驗證)

        Args:
            filepaths: 檔案路徑列表
            delay: 每次上傳間隔秒數
            skip_existing: 是否跳過已上傳的檔案

        Returns:
            統計資訊
        """
        logger.info(f"開始批次上傳: {len(filepaths)} 個檔案")

        # 確保 Store 存在
        if not self.store_id:
            self.get_or_create_store()

        # 重設統計
        self.stats['total_files'] = len(filepaths)
        self.stats['uploaded_files'] = 0
        self.stats['failed_files'] = 0
        self.stats['total_bytes'] = 0
        self.stats['skipped_files'] = 0

        # 處理每個檔案
        files_to_upload = []
        for filepath_str in filepaths:
            filepath = Path(filepath_str)

            # 檢查是否已上傳
            if skip_existing and str(filepath) in self.manifest['uploaded']:
                upload_info = self.manifest['uploaded'][str(filepath)]
                if upload_info['status'] == 'success':
                    logger.info(f"跳過已上傳的檔案: {filepath.name}")
                    self.stats['skipped_files'] += 1
                    continue

            files_to_upload.append(filepath)

        logger.info(f"共需上傳 {len(files_to_upload)} 個檔案")

        # 逐一上傳
        for i, filepath in enumerate(files_to_upload, 1):
            logger.info(f"處理 [{i}/{len(files_to_upload)}]: {filepath.name}")

            # 生成顯示名稱
            display_name = filepath.name

            # 上傳並加入 Store
            success = self.upload_and_add(str(filepath), display_name, delay)

            if success:
                logger.info(f"✓ 成功 [{i}/{len(files_to_upload)}]")
            else:
                logger.warning(f"✗ 失敗 [{i}/{len(files_to_upload)}]")

            # 間隔
            if i < len(files_to_upload):
                time.sleep(delay)

        logger.info(f"批次上傳完成!")
        logger.info(f"統計: {self.stats}")

        # 驗證完整性
        report = self.verify_upload_completeness()
        logger.info(f"上傳報告: 成功 {report['successful']}/{report['total']}, 失敗 {report['failed']}")

        return self.stats

    def upload_directory(
        self,
        directory: str,
        pattern: str = "*.md",
        delay: float = 1.0,
        skip_existing: bool = True
    ) -> Dict[str, Any]:
        """
        上傳目錄中的所有 Markdown 檔案 (支援重試、驗證)

        Args:
            directory: 目錄路徑
            pattern: 檔案模式 (glob)
            delay: 每次上傳間隔秒數
            skip_existing: 是否跳過已上傳的檔案

        Returns:
            統計資訊
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            raise FileNotFoundError(f"目錄不存在: {directory}")

        # 尋找所有符合的檔案
        filepaths = list(dir_path.glob(pattern))

        if not filepaths:
            logger.warning(f"目錄中沒有找到符合 '{pattern}' 的檔案: {directory}")
            return self.stats

        logger.info(f"找到 {len(filepaths)} 個檔案")

        # 轉為字串路徑
        filepaths_str = [str(fp) for fp in filepaths]

        # 批次上傳
        return self.upload_batch(
            filepaths_str,
            delay=delay,
            skip_existing=skip_existing
        )

    def list_store_files(self) -> List[Dict[str, Any]]:
        """
        列出 Store 中的所有檔案

        Returns:
            檔案列表
        """
        if not self.store_id:
            self.get_or_create_store()

        try:
            logger.info(f"列出 Store 中的檔案: {self.store_id}")

            store_info = self.client.file_search_stores.get(name=self.store_id)

            files = []
            if hasattr(store_info, 'files') and store_info.files:
                for file_ref in store_info.files:
                    files.append({
                        'name': file_ref,
                        'display_name': file_ref.split('/')[-1],
                    })

            logger.info(f"Store 中共有 {len(files)} 個檔案")
            return files

        except Exception as e:
            logger.error(f"列出檔案失敗: {e}")
            return []

    def delete_store(self):
        """刪除 Store (謹慎使用!)"""
        if not self.store_id:
            logger.warning("Store 尚未建立,無需刪除")
            return

        try:
            logger.warning(f"刪除 Store: {self.store_id}")
            self.client.file_search_stores.delete(name=self.store_id)
            logger.info("Store 已刪除")
            self.store_id = None

        except Exception as e:
            logger.error(f"刪除 Store 失敗: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """取得統計資訊"""
        return self.stats.copy()

    def verify_upload_completeness(self) -> Dict[str, Any]:
        """
        驗證上傳完整性

        Returns:
            驗證報告 (成功/失敗/待處理的檔案)
        """
        logger.info("驗證上傳完整性...")

        successful = []
        failed = []
        pending = []

        for filepath, info in self.manifest['uploaded'].items():
            if info['status'] == 'success':
                successful.append({
                    'filepath': filepath,
                    'file_id': info['file_id'],
                    'display_name': info.get('display_name', '')
                })
            elif info['status'] == 'failed':
                failed.append({
                    'filepath': filepath,
                    'error': info.get('error', 'Unknown error'),
                    'display_name': info.get('display_name', '')
                })

        report = {
            'total': len(self.manifest['uploaded']),
            'successful': len(successful),
            'failed': len(failed),
            'pending': len(pending),
            'successful_files': successful,
            'failed_files': failed,
            'pending_files': pending,
        }

        logger.info(f"驗證完成: 成功 {len(successful)}, 失敗 {len(failed)}, 待處理 {len(pending)}")

        return report

    def get_failed_uploads(self) -> List[Dict[str, Any]]:
        """
        取得上傳失敗的檔案列表

        Returns:
            失敗的檔案資訊
        """
        failed = []
        for filepath, info in self.manifest['uploaded'].items():
            if info['status'] == 'failed':
                failed.append({
                    'filepath': filepath,
                    'error': info.get('error', 'Unknown error'),
                    'timestamp': info.get('timestamp'),
                    'display_name': info.get('display_name', '')
                })

        return failed
