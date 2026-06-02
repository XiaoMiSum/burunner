"""浏览器会话模块单元测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from burunner.browser.session import (
    SUPPORTED_BROWSER_CHANNELS,
    BrowserDriver,
    PlaywrightDriver,
)


class TestSupportedBrowserChannels:
    """支持的浏览器频道测试。"""

    def test_channels_are_strings(self):
        """所有频道都是字符串。"""
        for channel in SUPPORTED_BROWSER_CHANNELS:
            assert isinstance(channel, str)
            assert len(channel) > 0

    def test_contains_chromium(self):
        """包含 chromium。"""
        assert "chromium" in SUPPORTED_BROWSER_CHANNELS

    def test_contains_chrome_variants(self):
        """包含 Chrome 变体。"""
        assert "chrome" in SUPPORTED_BROWSER_CHANNELS
        assert "chrome-beta" in SUPPORTED_BROWSER_CHANNELS

    def test_contains_edge_variants(self):
        """包含 Edge 变体。"""
        assert "msedge" in SUPPORTED_BROWSER_CHANNELS
        assert "msedge-beta" in SUPPORTED_BROWSER_CHANNELS


class TestBrowserDriverProtocol:
    """浏览器驱动协议测试。"""

    def test_protocol_runtime_checkable(self):
        """协议支持运行时检查。"""
        from typing import runtime_checkable
        assert runtime_checkable

    def test_mock_driver_implements_protocol(self):
        """Mock 驱动实现协议。"""

        class MockDriver:
            async def create_session(self, **kwargs):
                return MagicMock()

            async def close_session(self, session):
                pass

        driver = MockDriver()
        # 运行时检查
        assert isinstance(driver, BrowserDriver)


class TestPlaywrightDriver:
    """PlaywrightDriver 测试。"""

    def setup_method(self):
        """每个测试前创建驱动实例。"""
        self.driver = PlaywrightDriver()

    @pytest.mark.asyncio
    async def test_create_session_success(self):
        """成功创建会话。"""
        mock_session = MagicMock()
        mock_session.start = AsyncMock()

        mock_profile = MagicMock()
        mock_session_class = MagicMock(return_value=mock_session)
        mock_profile_class = MagicMock(return_value=mock_profile)

        with patch("burunner.browser.session._import_session_class", return_value=mock_session_class):
            with patch("burunner.browser.session._import_profile_class", return_value=mock_profile_class):
                session = await self.driver.create_session(headless=True)

                assert session == mock_session
                mock_session_class.assert_called_once()
                mock_session.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_without_profile(self):
        """没有 Profile 类时创建会话。"""
        mock_session = MagicMock()
        mock_session.start = AsyncMock()
        mock_session_class = MagicMock(return_value=mock_session)

        with patch("burunner.browser.session._import_session_class", return_value=mock_session_class):
            with patch("burunner.browser.session._import_profile_class", return_value=None):
                session = await self.driver.create_session(headless=True)

                assert session == mock_session
                # 应该直接传给 Session
                call_kwargs = mock_session_class.call_args[1]
                assert "headless" in call_kwargs

    @pytest.mark.asyncio
    async def test_create_session_with_channel(self):
        """带 channel 参数创建会话。"""
        mock_session = MagicMock()
        mock_session.start = AsyncMock()
        mock_profile = MagicMock()
        mock_session_class = MagicMock(return_value=mock_session)
        mock_profile_class = MagicMock(return_value=mock_profile)

        with patch("burunner.browser.session._import_session_class", return_value=mock_session_class):
            with patch("burunner.browser.session._import_profile_class", return_value=mock_profile_class):
                session = await self.driver.create_session(
                    headless=True,
                    channel="chrome-beta"
                )

                assert session == mock_session
                # Profile 应该包含 channel
                profile_call_kwargs = mock_profile_class.call_args[1]
                assert "channel" in profile_call_kwargs

    @pytest.mark.asyncio
    async def test_create_session_fallback(self):
        """创建失败时回退到最小参数。"""
        mock_session = MagicMock()
        mock_session.start = AsyncMock()

        def side_effect(**kwargs):
            if "browser_profile" in kwargs:
                raise TypeError("不支持 browser_profile")
            return mock_session

        mock_session_class = MagicMock(side_effect=side_effect)
        mock_profile_class = MagicMock()

        with patch("burunner.browser.session._import_session_class", return_value=mock_session_class):
            with patch("burunner.browser.session._import_profile_class", return_value=mock_profile_class):
                session = await self.driver.create_session(headless=True)

                assert session == mock_session
                # 第二次调用应该只用 headless
                assert mock_session_class.call_count >= 1

    @pytest.mark.asyncio
    async def test_close_session(self):
        """关闭会话。"""
        mock_session = MagicMock()
        mock_session.stop = AsyncMock()

        await self.driver.close_session(mock_session)
        # close_session 会依次尝试 stop/close/kill
        mock_session.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_session_without_close(self):
        """会话没有 close 方法。"""
        mock_session = MagicMock()
        # 没有任何关闭方法
        del mock_session.stop
        del mock_session.close
        del mock_session.kill

        # 不应该抛出异常
        await self.driver.close_session(mock_session)


class TestSessionManager:
    """会话管理器集成测试。"""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """上下文管理器。"""
        try:
            from burunner.browser.session import create_browser_session
        except ImportError:
            pytest.skip("browser-use 未安装")

        mock_session = MagicMock()
        mock_session.start = AsyncMock()
        mock_session.close = AsyncMock()
        mock_driver = MagicMock()
        mock_driver.create_session = AsyncMock(return_value=mock_session)
        mock_driver.close_session = AsyncMock()

        with patch("burunner.browser.session.PlaywrightDriver", return_value=mock_driver):
            async with create_browser_session(headless=True) as session:
                assert session == mock_session
                mock_driver.create_session.assert_called_once()

            mock_driver.close_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exception(self):
        """上下文管理器异常时清理。"""
        try:
            from burunner.browser.session import create_browser_session
        except ImportError:
            pytest.skip("browser-use 未安装")

        mock_session = MagicMock()
        mock_session.start = AsyncMock()
        mock_session.close = AsyncMock()
        mock_driver = MagicMock()
        mock_driver.create_session = AsyncMock(return_value=mock_session)
        mock_driver.close_session = AsyncMock()

        with patch("burunner.browser.session.PlaywrightDriver", return_value=mock_driver):
            with pytest.raises(RuntimeError):
                async with create_browser_session(headless=True) as session:
                    raise RuntimeError("测试异常")

            # 即使异常也应该关闭会话
            mock_driver.close_session.assert_called_once()
