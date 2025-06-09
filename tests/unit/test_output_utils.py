import pytest
from unittest.mock import AsyncMock, Mock, patch

from kodx.tools import clean_pty_output, strip_ansi_codes, strip_carriage_returns, DockerCodexTools


@pytest.mark.unit
class TestOutputCleaning:
    """Tests for PTY output cleaning utilities."""

    @pytest.fixture(autouse=True)
    def _mock_docker(self):
        with patch("kodx.tools.docker") as mock_docker:
            mock_docker.from_env.return_value = Mock()
            yield

    def test_strip_ansi_codes(self):
        text = "\x1b[31mred\x1b[0m normal"
        assert strip_ansi_codes(text) == "red normal"

    def test_strip_carriage_returns(self):
        text = "line1\r\nline2\rline3"
        assert strip_carriage_returns(text) == "line1\nline2\nline3"

    def test_clean_pty_output(self):
        raw = "\x1b[32mgreen\x1b[0m\r\nnext"
        assert clean_pty_output(raw) == "green\nnext"

    @pytest.mark.asyncio
    async def test_feed_chars_cleans_output(self):
        tools = DockerCodexTools()
        mock_shell = AsyncMock()
        mock_shell.run.return_value = "\x1b[33myellow\x1b[0m\routput"
        tools.shell = mock_shell
        tools.shells["default"] = mock_shell

        result = await tools.feed_chars("echo test")
        assert result == "yellow\noutput"
