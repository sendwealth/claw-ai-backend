"""
日志配置
使用 python-json-logger 实现 JSON 格式日志
"""

import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger
from app.core.config import settings


def setup_logger():
    """设置日志器"""

    # 创建日志目录
    log_file = Path(settings.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # 创建 logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # 清除已有的 handlers
    logger.handlers = []

    # JSON 格式化器
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器
    file_handler = logging.FileHandler(settings.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# 创建全局 logger
logger = setup_logger()
