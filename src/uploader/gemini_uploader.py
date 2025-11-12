"""Gemini File Search 上傳器"""

import os
import time
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

    def __init__(self, api_key: Optional[str] = None, store_name: Optional[str] = None):
        """
        初始化上傳器

        Args:
            api_key: Gemini API Key (預設從環境變數讀取)
            store_name: File Search Store 名稱
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

        # 統計資訊
        self.stats = {
            'total_files': 0,
            'uploaded_files': 0,
            'failed_files': 0,
            'total_bytes': 0,
        }

        logger.info(f"GeminiUploader 初始化成功: Store名稱={self.store_name}")

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
        上傳單一檔案到 Gemini

        Args:
            filepath: 檔案路徑
            display_name: 顯示名稱 (預設使用檔名)

        Returns:
            File ID 或 None (失敗時)
        """
        try:
            filepath_obj = Path(filepath)

            if not filepath_obj.exists():
                logger.error(f"檔案不存在: {filepath}")
                self.stats['failed_files'] += 1
                return None

            # 顯示名稱
            if not display_name:
                display_name = filepath_obj.name

            # 上傳檔案
            logger.info(f"上傳檔案: {display_name}")

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

            return file_obj.name

        except Exception as e:
            logger.error(f"上傳檔案失敗: {filepath} - {e}")
            self.stats['failed_files'] += 1
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
        上傳檔案並加入 Store

        Args:
            filepath: 檔案路徑
            display_name: 顯示名稱
            delay: 延遲秒數 (避免 API 限制)

        Returns:
            是否成功
        """
        try:
            # 上傳檔案
            file_id = self.upload_file(filepath, display_name)

            if not file_id:
                return False

            # 延遲 (等待檔案處理)
            time.sleep(delay)

            # 加入 Store
            self.add_file_to_store(file_id)

            return True

        except Exception as e:
            logger.error(f"上傳並加入 Store 失敗: {filepath} - {e}")
            return False

    def upload_batch(
        self,
        filepaths: List[str],
        delay: float = 1.0,
        skip_existing: bool = True
    ) -> Dict[str, Any]:
        """
        批次上傳多個檔案

        Args:
            filepaths: 檔案路徑列表
            delay: 每次上傳間隔秒數
            skip_existing: 是否跳過已存在的檔案

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

        # 逐一上傳
        for i, filepath in enumerate(filepaths, 1):
            logger.info(f"處理 [{i}/{len(filepaths)}]: {filepath}")

            # 生成顯示名稱
            display_name = Path(filepath).name

            # 上傳並加入 Store
            success = self.upload_and_add(filepath, display_name, delay)

            if success:
                logger.info(f"✓ 成功 [{i}/{len(filepaths)}]")
            else:
                logger.warning(f"✗ 失敗 [{i}/{len(filepaths)}]")

            # 間隔
            if i < len(filepaths):
                time.sleep(delay)

        logger.info(f"批次上傳完成!")
        logger.info(f"統計: {self.stats}")

        return self.stats

    def upload_directory(
        self,
        directory: str,
        pattern: str = "*.md",
        delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        上傳目錄中的所有 Markdown 檔案

        Args:
            directory: 目錄路徑
            pattern: 檔案模式 (glob)
            delay: 每次上傳間隔秒數

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
        return self.upload_batch(filepaths_str, delay=delay)

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
