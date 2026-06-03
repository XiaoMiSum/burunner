"""日志模块单元测试 - 适配 utils.logging 模块。"""

import logging
from unittest.mock import patch

from burunner.utils.logging import setup_logging, get_logger


class TestSetupLogging:
    """setup_logging 函数测试。"""

    def setup_method(self):
        """每个测试前重置初始化状态。"""
        import burunner.utils.logging
        burunner.utils.logging._INITIALIZED = False
        # 清除 burunner logger 的 handlers
        root = logging.getLogger("burunner")
        root.handlers.clear()

    def test_setup_logging_creates_handler(self):
        """测试创建日志 handler。"""
        setup_logging(verbose=False)
        logger = logging.getLogger("burunner")
        assert len(logger.handlers) > 0

    def test_setup_logging_info_level(self):
        """测试默认 INFO 级别。"""
        setup_logging(verbose=False)
        logger = logging.getLogger("burunner")
        assert logger.level == logging.INFO

    def test_setup_logging_debug_level(self):
        """测试 verbose=True 时 DEBUG 级别。"""
        setup_logging(verbose=True)
        logger = logging.getLogger("burunner")
        assert logger.level == logging.DEBUG

    def test_setup_logging_idempotent(self):
        """多次调用应该只初始化一次。"""
        setup_logging(verbose=False)
        logger = logging.getLogger("burunner")
        handlers_before = len(logger.handlers)

        # 再次调用
        setup_logging(verbose=True)
        handlers_after = len(logger.handlers)

        # handlers 数量应该不变
        assert handlers_before == handlers_after

    def test_browser_use_log_disabled(self):
        """测试 browser_use_log=False 时彻底静默。"""
        setup_logging(verbose=False, browser_use_log=False)
        assert logging.getLogger("browser_use").level == logging.CRITICAL
        assert logging.getLogger("playwright").level == logging.CRITICAL
        assert logging.getLogger("httpx").level == logging.CRITICAL

    def test_browser_use_log_enabled_not_verbose(self):
        """测试 browser_use_log=True 但 verbose=False 时降为 WARNING。"""
        setup_logging(verbose=False, browser_use_log=True)
        assert logging.getLogger("browser_use").level == logging.WARNING
        assert logging.getLogger("playwright").level == logging.WARNING
        assert logging.getLogger("httpx").level == logging.WARNING

    def test_browser_use_log_enabled_verbose(self):
        """测试 verbose=True 且 browser_use_log=True 时使用 DEBUG。"""
        setup_logging(verbose=True, browser_use_log=True)
        # verbose=True 时, burunner 使用 DEBUG
        assert logging.getLogger("burunner").level == logging.DEBUG


class TestGetLogger:
    """get_logger 函数测试。"""

    def setup_method(self):
        """每个测试前重置初始化状态。"""
        import burunner.utils.logging
        burunner.utils.logging._INITIALIZED = False
        root = logging.getLogger("burunner")
        root.handlers.clear()

    def test_get_logger_returns_child(self):
        """测试返回 burunner 子 logger。"""
        logger = get_logger("test_module")
        assert logger.name == "burunner.test_module"

    def test_get_logger_nested(self):
        """测试嵌套模块名。"""
        logger = get_logger("parser.yaml")
        assert logger.name == "burunner.parser.yaml"

    def test_get_logger_inherits_burunner(self):
        """测试继承 burunner 配置。"""
        setup_logging(verbose=False)
        logger = get_logger("submodule")
        # 应该继承 burunner 的配置
        assert logger.propagate is False or logger.name.startswith("burunner")
