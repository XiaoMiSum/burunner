"""截图工具模块单元测试。"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from burunner.utils.screenshot import (
    _decode_b64,
    _from_session,
    _from_history,
    capture_failure_screenshot,
)


class TestDecodeB64:
    """_decode_b64 函数测试。"""

    def test_empty_string(self):
        assert _decode_b64("") is None

    def test_none_string(self):
        assert _decode_b64(None) is None

    def test_valid_base64(self):
        import base64
        original = b"test image data"
        encoded = base64.b64encode(original).decode()
        result = _decode_b64(encoded)
        assert result == original

    def test_base64_with_data_prefix(self):
        import base64
        original = b"test image"
        encoded = base64.b64encode(original).decode()
        data_uri = f"data:image/png;base64,{encoded}"
        result = _decode_b64(data_uri)
        assert result == original

    def test_invalid_base64(self):
        result = _decode_b64("!!!invalid!!!")
        assert result is None


class TestFromSession:
    """_from_session 函数测试。"""

    @pytest.mark.asyncio
    async def test_none_session(self):
        result = await _from_session(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_session_no_method(self):
        """session 没有截图方法。"""
        session = object()
        result = await _from_session(session)
        assert result is None

    @pytest.mark.asyncio
    async def test_session_returns_bytes(self):
        """session 返回 bytes。"""
        session = MagicMock()
        session.take_screenshot.return_value = b"image data"

        result = await _from_session(session)
        assert result == b"image data"

    @pytest.mark.asyncio
    async def test_session_returns_base64_string(self):
        """session 返回 base64 字符串。"""
        import base64
        session = MagicMock()
        original = b"image data"
        encoded = base64.b64encode(original).decode()
        session.take_screenshot.return_value = encoded

        result = await _from_session(session)
        assert result == original

    @pytest.mark.asyncio
    async def test_async_screenshot_method(self):
        """异步截图方法。"""
        session = MagicMock()

        async def async_screenshot():
            return b"async image"

        session.take_screenshot = async_screenshot
        result = await _from_session(session)
        assert result == b"async image"

    @pytest.mark.asyncio
    async def test_screenshot_exception(self):
        """截图方法抛出异常。"""
        session = MagicMock()
        session.take_screenshot.side_effect = RuntimeError("失败")

        result = await _from_session(session)
        assert result is None

    @pytest.mark.asyncio
    async def test_fallback_to_screenshot_method(self):
        """fallback 到 screenshot 方法。"""
        session = MagicMock()
        del session.take_screenshot
        session.screenshot.return_value = b"fallback image"

        result = await _from_session(session)
        assert result == b"fallback image"


class TestFromHistory:
    """_from_history 函数测试。"""

    def test_none_history(self):
        result = _from_history(None)
        assert result is None

    def test_history_with_screenshots_method(self):
        """history 有 screenshots() 方法。"""
        import base64
        history = MagicMock()
        original = b"screenshot data"
        encoded = base64.b64encode(original).decode()
        history.screenshots.return_value = [encoded]

        result = _from_history(history)
        assert result == original

    def test_history_screenshots_exception(self):
        """screenshots() 方法抛出异常。"""
        history = MagicMock()
        history.screenshots.side_effect = RuntimeError("失败")

        result = _from_history(history)
        assert result is None

    def test_history_from_history_list(self):
        """从 history.history 列表中提取截图。"""
        import base64
        original = b"history screenshot"
        encoded = base64.b64encode(original).decode()

        class HistoryItem:
            def __init__(self):
                self.state = MagicMock()
                self.state.screenshot = encoded

        history = MagicMock()
        history.screenshots.return_value = []
        history.history = [HistoryItem()]

        result = _from_history(history)
        assert result == original

    def test_history_returns_bytes_directly(self):
        """history 直接返回 bytes。"""
        history = MagicMock()
        history.screenshots.return_value = [b"raw image"]

        result = _from_history(history)
        assert result == b"raw image"

    def test_history_no_screenshots(self):
        """history 没有截图。"""
        history = MagicMock()
        history.screenshots.return_value = []
        history.history = []

        result = _from_history(history)
        assert result is None


class TestCaptureFailureScreenshot:
    """capture_failure_screenshot 函数测试。"""

    @pytest.mark.asyncio
    async def test_capture_from_session(self, tmp_path):
        """从 session 抓取截图。"""
        session = MagicMock()
        session.take_screenshot.return_value = b"session image"
        history = MagicMock()
        history.screenshots.return_value = []

        result = await capture_failure_screenshot(
            session=session,
            history=history,
            output_dir=tmp_path,
            case_name="测试用例",
        )

        assert result is not None
        assert result.exists()
        assert result.read_bytes() == b"session image"

    @pytest.mark.asyncio
    async def test_capture_fallback_to_history(self, tmp_path):
        """session 失败,回退到 history。"""
        session = MagicMock()
        session.take_screenshot.side_effect = RuntimeError("失败")

        import base64
        history = MagicMock()
        original = b"history image"
        encoded = base64.b64encode(original).decode()
        history.screenshots.return_value = [encoded]

        result = await capture_failure_screenshot(
            session=session,
            history=history,
            output_dir=tmp_path,
            case_name="测试用例",
        )

        assert result is not None
        assert result.exists()
        assert result.read_bytes() == original

    @pytest.mark.asyncio
    async def test_capture_both_fail(self, tmp_path):
        """session 和 history 都失败。"""
        session = MagicMock()
        session.take_screenshot.side_effect = RuntimeError("失败")
        history = MagicMock()
        history.screenshots.return_value = []
        history.history = []

        result = await capture_failure_screenshot(
            session=session,
            history=history,
            output_dir=tmp_path,
            case_name="测试用例",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_output_filename_safe(self, tmp_path):
        """输出文件名应该安全。"""
        session = MagicMock()
        session.take_screenshot.return_value = b"image"
        history = MagicMock()
        history.screenshots.return_value = []

        result = await capture_failure_screenshot(
            session=session,
            history=history,
            output_dir=tmp_path,
            case_name="测试用例/特殊字符!@#",
        )

        assert result is not None
        # 文件名应该被清理
        assert result.name.startswith("测试用例_特殊字符___")
        assert result.name.endswith(".png")

    @pytest.mark.asyncio
    async def test_creates_output_dir(self, tmp_path):
        """应该创建输出目录。"""
        output_dir = tmp_path / "subdir" / "screenshots"

        session = MagicMock()
        session.take_screenshot.return_value = b"image"
        history = MagicMock()
        history.screenshots.return_value = []

        result = await capture_failure_screenshot(
            session=session,
            history=history,
            output_dir=output_dir,
            case_name="test",
        )

        assert output_dir.exists()
        assert result is not None
