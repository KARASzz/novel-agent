import json
import logging
import os
import sys
from datetime import datetime

from core_engine.config_loader import load_config


def _resolve_log_level() -> int:
    cfg = load_config()
    configured = cfg.get("logging", {}).get("log_level", "INFO")
    level_name = os.getenv("LOG_LEVEL", configured).upper()
    return getattr(logging, level_name, logging.INFO)


class JsonFormatter(logging.Formatter):
    """自定义 JSON 格式化器，用于结构化日志输出，方便 ELK 或云端日志系统解析"""
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        cfg = load_config()
        log_cfg = cfg.get("logging", {})
        use_json = bool(log_cfg.get("use_json", False))
        log_to_file = bool(log_cfg.get("log_to_file", True))

        # 控制台 (Console) 处理
        stream_handler = logging.StreamHandler(sys.stdout)
        if use_json:
            stream_handler.setFormatter(JsonFormatter())
        else:
            stream_handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                datefmt="%H:%M:%S",
            ))
        logger.addHandler(stream_handler)

        # 文件 (File) 处理
        if log_to_file:
            workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_dir = os.path.join(workspace, "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"workflow_{datetime.now().strftime('%Y%m%d')}.log")
            
            # 强制使用 utf-8 编码，防止 Windows 环境下日志乱码
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            if use_json:
                file_handler.setFormatter(JsonFormatter())
            else:
                file_handler.setFormatter(logging.Formatter(
                    "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
                ))
            logger.addHandler(file_handler)

    logger.setLevel(_resolve_log_level())
    logger.propagate = False
    return logger
