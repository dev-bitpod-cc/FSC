"""配置載入模組"""

import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
import os

class ConfigLoader:
    """配置載入器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._configs = {}

        # 載入環境變數
        load_dotenv()

    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        載入 YAML 配置檔

        Args:
            filename: 配置檔名 (例如: "sources.yaml")

        Returns:
            配置字典
        """
        if filename in self._configs:
            return self._configs[filename]

        config_path = self.config_dir / filename

        if not config_path.exists():
            raise FileNotFoundError(f"配置檔不存在: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self._configs[filename] = config
        return config

    def get_env(self, key: str, default: Any = None) -> Any:
        """
        取得環境變數

        Args:
            key: 環境變數名稱
            default: 預設值

        Returns:
            環境變數值
        """
        return os.getenv(key, default)

    def get_data_source_config(self, source_name: str) -> Dict[str, Any]:
        """
        取得特定資料源的配置

        Args:
            source_name: 資料源名稱 (announcements, laws, penalties)

        Returns:
            資料源配置
        """
        sources_config = self.load_yaml("sources.yaml")

        if source_name not in sources_config['sources']:
            raise ValueError(f"未知的資料源: {source_name}")

        return sources_config['sources'][source_name]

    def get_crawler_config(self) -> Dict[str, Any]:
        """取得爬蟲配置"""
        return self.load_yaml("crawler.yaml")

    def get_source_unit_mapping(self) -> Dict[str, str]:
        """取得資料來源單位對應表"""
        sources_config = self.load_yaml("sources.yaml")
        return sources_config.get('source_units', {})

    def get_category_mapping(self) -> Dict[str, str]:
        """取得公告類型對應表"""
        sources_config = self.load_yaml("sources.yaml")
        return sources_config.get('announcement_categories', {})

    def get_penalty_category_mapping(self) -> Dict[str, str]:
        """取得裁罰案件違規類型對應表"""
        sources_config = self.load_yaml("sources.yaml")
        return sources_config.get('penalty_categories', {})
