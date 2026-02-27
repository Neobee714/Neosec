"""
日志模块 (Logger Module)

提供统一的彩色分级日志系统，支持控制台和文件双重输出。
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import colorlog


class NeoSecLogger:
    """
    NeoSec 日志管理器 (NeoSec Logger Manager)

    提供统一的日志接口，支持彩色输出和文件记录。
    """

    _instance: Optional['NeoSecLogger'] = None
    _initialized: bool = False

    def __new__(cls) -> 'NeoSecLogger':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化日志系统"""
        if self._initialized:
            return

        self.logger = logging.getLogger("neosec")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        # 清除已有的处理器
        self.logger.handlers.clear()

        self._initialized = True

    def setup(
        self,
        log_level: str = "INFO",
        log_file: Optional[Path] = None,
        enable_color: bool = True
    ) -> None:
        """
        配置日志系统 (Setup Logger)

        Args:
            log_level: 日志级别（TRACE/DEBUG/INFO/WARNING/ERROR/CRITICAL）
            log_file: 日志文件路径（可选）
            enable_color: 是否启用彩色输出
        """
        # 设置日志级别
        level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger.setLevel(level)

        # 清除已有的处理器
        self.logger.handlers.clear()

        # 控制台处理器（彩色输出）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        if enable_color:
            # 彩色日志格式
            color_formatter = colorlog.ColoredFormatter(
                fmt="%(log_color)s[%(asctime)s] [%(levelname)-8s]%(reset)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                log_colors={
                    'TRACE': 'cyan',
                    'DEBUG': 'blue',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            console_handler.setFormatter(color_formatter)
        else:
            # 普通日志格式
            plain_formatter = logging.Formatter(
                fmt="[%(asctime)s] [%(levelname)-8s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            console_handler.setFormatter(plain_formatter)

        self.logger.addHandler(console_handler)

        # 文件处理器（如果指定了日志文件）
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(
                log_file,
                mode='a',
                encoding='utf-8'
            )
            file_handler.setLevel(level)

            file_formatter = logging.Formatter(
                fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)

            self.logger.addHandler(file_handler)

    def trace(self, message: str, *args, **kwargs) -> None:
        """TRACE 级别日志（最详细）"""
        self.logger.log(5, message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs) -> None:
        """DEBUG 级别日志"""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """INFO 级别日志"""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """WARNING 级别日志"""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """ERROR 级别日志"""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """CRITICAL 级别日志"""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        """记录异常信息（包含堆栈跟踪）"""
        self.logger.exception(message, *args, **kwargs)


# 全局日志实例
_logger: Optional[NeoSecLogger] = None


def get_logger() -> NeoSecLogger:
    """
    获取全局日志实例 (Get Global Logger Instance)

    Returns:
        NeoSecLogger 单例实例
    """
    global _logger
    if _logger is None:
        _logger = NeoSecLogger()
    return _logger


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_color: bool = True
) -> NeoSecLogger:
    """
    配置并获取日志实例 (Setup and Get Logger)

    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        enable_color: 是否启用彩色输出

    Returns:
        配置好的 NeoSecLogger 实例
    """
    logger = get_logger()
    logger.setup(log_level, log_file, enable_color)
    return logger
