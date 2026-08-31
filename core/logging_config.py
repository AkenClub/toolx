import logging
import os
from logging.handlers import RotatingFileHandler

from .app_paths import get_app_data_dir


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging():
    """Configure console and rotating file logs for the desktop application."""
    try:
        log_dir = os.path.join(get_app_data_dir(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "toolx.log")
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        logging.basicConfig(
            level=logging.INFO,
            format=LOG_FORMAT,
            handlers=[file_handler, logging.StreamHandler()],
            force=True,
        )
        return log_file
    except Exception:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, force=True)
        logging.getLogger(__name__).exception("无法创建 ToolX 文件日志，将只写入标准输出")
        return None
