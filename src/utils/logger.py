"""日誌設定模組"""

import sys
from pathlib import Path
from loguru import logger

def setup_logger(
    log_dir: str = "logs",
    level: str = "INFO",
    rotation: str = "100 MB",
    retention: str = "30 days"
):
    """
    設定全局日誌

    Args:
        log_dir: 日誌目錄
        level: 日誌等級 (DEBUG, INFO, WARNING, ERROR)
        rotation: 日誌切割大小
        retention: 日誌保留時間
    """
    # 建立日誌目錄
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 移除預設 handler
    logger.remove()

    # 添加 console handler (彩色輸出)
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        colorize=True
    )

    # 添加 file handler
    logger.add(
        log_path / "fsc_crawler.log",
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation=rotation,
        retention=retention,
        encoding="utf-8"
    )

    logger.info(f"日誌系統已初始化: {log_path.absolute()}")

    return logger

# 預設 logger 實例
default_logger = logger
