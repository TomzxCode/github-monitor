"""Tests for the event-handler CLI command."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from github_monitor.cli.event_handler import event_handler, event_handler_main


class TestEventHandlerCommand:
    """Tests for the event-handler CLI command."""

    @pytest.fixture
    def mock_args(self, tmp_path: Path):
        """Create mock args for testing."""
        args = Mock()
        args.path = tmp_path
        args.templates_dir = None
        args.nats_server = "nats://localhost:4222"
        args.stream = "GITHUB_EVENTS"
        args.consumer = "github-event-handler"
        args.batch_size = 10
        args.fetch_timeout = 5.0
        args.skip_users = []
        args.recreate_consumer = False
        args.claude_verbose = False
        args.auto_confirm = False
        return args

    @pytest.mark.asyncio
    async def test_event_handler_main_connects_to_nats(self, mock_args):
        """Test that event_handler_main connects to NATS."""
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connect = AsyncMock()
        mock_nc.close = AsyncMock()
        mock_js = MagicMock()
        mock_psub = MagicMock()
        mock_psub.fetch = AsyncMock(side_effect=KeyboardInterrupt)
        mock_consumer_info = Mock()
        mock_consumer_info.num_pending = 0

        with (
            patch("github_monitor.cli.event_handler.NATS", return_value=mock_nc),
            patch("github_monitor.cli.event_handler.check_claude_installed", return_value=True),
            patch("github_monitor.cli.event_handler.EventHandler") as mock_handler_class,
        ):
            mock_nc.jetstream.return_value = mock_js
            # First call fails (consumer doesn't exist), second call succeeds (after creation)
            mock_js.consumer_info = AsyncMock(side_effect=[Exception("Not found"), mock_consumer_info])
            mock_js.add_consumer = AsyncMock()
            mock_js.pull_subscribe = AsyncMock(return_value=mock_psub)

            result = await event_handler_main(mock_args)
            assert result == 0
            mock_nc.connect.assert_called_once_with(mock_args.nats_server)
            mock_nc.close.assert_called_once()
            mock_handler_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_handler_main_creates_consumer(self, mock_args):
        """Test that event_handler_main creates a new consumer."""
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connect = AsyncMock()
        mock_nc.close = AsyncMock()
        mock_js = MagicMock()
        mock_psub = MagicMock()
        mock_psub.fetch = AsyncMock(side_effect=KeyboardInterrupt)
        mock_consumer_info = Mock()
        mock_consumer_info.num_pending = 5

        with (
            patch("github_monitor.cli.event_handler.NATS", return_value=mock_nc),
            patch("github_monitor.cli.event_handler.check_claude_installed", return_value=True),
            patch("github_monitor.cli.event_handler.EventHandler"),
        ):
            mock_nc.jetstream.return_value = mock_js
            # First call fails (consumer doesn't exist), second call succeeds (after creation)
            mock_js.consumer_info = AsyncMock(side_effect=[Exception("Not found"), mock_consumer_info])
            mock_js.add_consumer = AsyncMock()
            mock_js.pull_subscribe = AsyncMock(return_value=mock_psub)

            result = await event_handler_main(mock_args)
            assert result == 0
            mock_js.add_consumer.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_handler_main_uses_existing_consumer(self, mock_args):
        """Test that event_handler_main uses existing consumer."""
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connect = AsyncMock()
        mock_nc.close = AsyncMock()
        mock_js = MagicMock()
        mock_psub = MagicMock()
        mock_psub.fetch = AsyncMock(side_effect=KeyboardInterrupt)
        mock_consumer_info = Mock()
        mock_consumer_info.num_pending = 10

        with (
            patch("github_monitor.cli.event_handler.NATS", return_value=mock_nc),
            patch("github_monitor.cli.event_handler.check_claude_installed", return_value=True),
            patch("github_monitor.cli.event_handler.EventHandler"),
        ):
            mock_nc.jetstream.return_value = mock_js
            mock_js.consumer_info = AsyncMock(return_value=mock_consumer_info)
            mock_js.add_consumer = AsyncMock()
            mock_js.pull_subscribe = AsyncMock(return_value=mock_psub)

            result = await event_handler_main(mock_args)
            assert result == 0
            # Should not create a new consumer
            mock_js.add_consumer.assert_not_called()

    @pytest.mark.asyncio
    async def test_event_handler_main_recreates_consumer(self, mock_args):
        """Test that event_handler_main recreates consumer when flag is set."""
        mock_args.recreate_consumer = True
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connect = AsyncMock()
        mock_nc.close = AsyncMock()
        mock_js = MagicMock()
        mock_psub = MagicMock()
        mock_psub.fetch = AsyncMock(side_effect=KeyboardInterrupt)
        mock_consumer_info = Mock()
        mock_consumer_info.num_pending = 10

        with (
            patch("github_monitor.cli.event_handler.NATS", return_value=mock_nc),
            patch("github_monitor.cli.event_handler.check_claude_installed", return_value=True),
            patch("github_monitor.cli.event_handler.EventHandler"),
        ):
            mock_nc.jetstream.return_value = mock_js
            mock_js.consumer_info = AsyncMock(return_value=mock_consumer_info)
            mock_js.delete_consumer = AsyncMock()
            mock_js.add_consumer = AsyncMock()
            mock_js.pull_subscribe = AsyncMock(return_value=mock_psub)

            result = await event_handler_main(mock_args)
            assert result == 0
            mock_js.delete_consumer.assert_called_once_with(mock_args.stream, mock_args.consumer)
            mock_js.add_consumer.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_handler_main_processes_messages(self, mock_args):
        """Test that event_handler_main processes messages."""
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connect = AsyncMock()
        mock_nc.close = AsyncMock()
        mock_js = MagicMock()
        mock_psub = MagicMock()
        mock_msg = MagicMock()

        call_count = 0

        async def fetch_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [mock_msg]
            raise KeyboardInterrupt

        mock_psub.fetch = AsyncMock(side_effect=fetch_side_effect)
        mock_consumer_info = Mock()
        mock_consumer_info.num_pending = 1

        with (
            patch("github_monitor.cli.event_handler.NATS", return_value=mock_nc),
            patch("github_monitor.cli.event_handler.check_claude_installed", return_value=True),
            patch("github_monitor.cli.event_handler.EventHandler"),
            patch("github_monitor.cli.event_handler.message_handler", new_callable=AsyncMock) as mock_handler,
        ):
            mock_nc.jetstream.return_value = mock_js
            mock_js.consumer_info = AsyncMock(return_value=mock_consumer_info)
            mock_js.pull_subscribe = AsyncMock(return_value=mock_psub)

            result = await event_handler_main(mock_args)
            assert result == 0
            mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_handler_main_handles_timeout(self, mock_args):
        """Test that event_handler_main handles fetch timeout."""
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connect = AsyncMock()
        mock_nc.close = AsyncMock()
        mock_js = MagicMock()
        mock_psub = MagicMock()

        call_count = 0

        async def fetch_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError
            raise KeyboardInterrupt

        mock_psub.fetch = AsyncMock(side_effect=fetch_side_effect)
        mock_consumer_info = Mock()
        mock_consumer_info.num_pending = 0

        with (
            patch("github_monitor.cli.event_handler.NATS", return_value=mock_nc),
            patch("github_monitor.cli.event_handler.check_claude_installed", return_value=True),
            patch("github_monitor.cli.event_handler.EventHandler"),
        ):
            mock_nc.jetstream.return_value = mock_js
            mock_js.consumer_info = AsyncMock(return_value=mock_consumer_info)
            mock_js.pull_subscribe = AsyncMock(return_value=mock_psub)

            result = await event_handler_main(mock_args)
            assert result == 0
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_event_handler_main_handles_fetch_error(self, mock_args):
        """Test that event_handler_main handles fetch errors gracefully."""
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connect = AsyncMock()
        mock_nc.close = AsyncMock()
        mock_js = MagicMock()
        mock_psub = MagicMock()

        call_count = 0

        async def fetch_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Fetch error")
            raise KeyboardInterrupt

        mock_psub.fetch = AsyncMock(side_effect=fetch_side_effect)
        mock_consumer_info = Mock()
        mock_consumer_info.num_pending = 1

        with (
            patch("github_monitor.cli.event_handler.NATS", return_value=mock_nc),
            patch("github_monitor.cli.event_handler.check_claude_installed", return_value=True),
            patch("github_monitor.cli.event_handler.EventHandler"),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_nc.jetstream.return_value = mock_js
            mock_js.consumer_info = AsyncMock(return_value=mock_consumer_info)
            mock_js.pull_subscribe = AsyncMock(return_value=mock_psub)

            result = await event_handler_main(mock_args)
            assert result == 0

    @pytest.mark.asyncio
    async def test_event_handler_main_without_claude(self, mock_args):
        """Test event_handler_main when Claude is not installed."""
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connect = AsyncMock()
        mock_nc.close = AsyncMock()
        mock_js = MagicMock()
        mock_psub = MagicMock()
        mock_psub.fetch = AsyncMock(side_effect=KeyboardInterrupt)
        mock_consumer_info = Mock()
        mock_consumer_info.num_pending = 0

        with (
            patch("github_monitor.cli.event_handler.NATS", return_value=mock_nc),
            patch("github_monitor.cli.event_handler.check_claude_installed", return_value=False),
            patch("github_monitor.cli.event_handler.EventHandler") as mock_handler_class,
        ):
            mock_nc.jetstream.return_value = mock_js
            mock_js.consumer_info = AsyncMock(return_value=mock_consumer_info)
            mock_js.pull_subscribe = AsyncMock(return_value=mock_psub)

            result = await event_handler_main(mock_args)
            assert result == 0
            # EventHandler should be created with claude_available=False
            mock_handler_class.assert_called_once()
            assert mock_handler_class.call_args[1]["claude_available"] is False

    @pytest.mark.asyncio
    async def test_event_handler_main_with_skip_users(self, mock_args):
        """Test event_handler_main with skip_users parameter."""
        mock_args.skip_users = ["user1", "user2"]
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connect = AsyncMock()
        mock_nc.close = AsyncMock()
        mock_js = MagicMock()
        mock_psub = MagicMock()
        mock_psub.fetch = AsyncMock(side_effect=KeyboardInterrupt)
        mock_consumer_info = Mock()
        mock_consumer_info.num_pending = 0

        with (
            patch("github_monitor.cli.event_handler.NATS", return_value=mock_nc),
            patch("github_monitor.cli.event_handler.check_claude_installed", return_value=True),
            patch("github_monitor.cli.event_handler.EventHandler") as mock_handler_class,
        ):
            mock_nc.jetstream.return_value = mock_js
            mock_js.consumer_info = AsyncMock(return_value=mock_consumer_info)
            mock_js.pull_subscribe = AsyncMock(return_value=mock_psub)

            result = await event_handler_main(mock_args)
            assert result == 0
            # EventHandler should be created with skip_users
            mock_handler_class.assert_called_once()
            assert mock_handler_class.call_args[1]["skip_users"] == ["user1", "user2"]

    @pytest.mark.asyncio
    async def test_event_handler_main_with_templates_dir(self, mock_args, tmp_path: Path):
        """Test event_handler_main with custom templates directory."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        mock_args.templates_dir = templates_dir

        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connect = AsyncMock()
        mock_nc.close = AsyncMock()
        mock_js = MagicMock()
        mock_psub = MagicMock()
        mock_psub.fetch = AsyncMock(side_effect=KeyboardInterrupt)
        mock_consumer_info = Mock()
        mock_consumer_info.num_pending = 0

        with (
            patch("github_monitor.cli.event_handler.NATS", return_value=mock_nc),
            patch("github_monitor.cli.event_handler.check_claude_installed", return_value=True),
            patch("github_monitor.cli.event_handler.EventHandler") as mock_handler_class,
        ):
            mock_nc.jetstream.return_value = mock_js
            mock_js.consumer_info = AsyncMock(return_value=mock_consumer_info)
            mock_js.pull_subscribe = AsyncMock(return_value=mock_psub)

            result = await event_handler_main(mock_args)
            assert result == 0
            # EventHandler should be created with templates_dir
            mock_handler_class.assert_called_once()
            assert mock_handler_class.call_args[1]["templates_dir"] == templates_dir

    @pytest.mark.asyncio
    async def test_event_handler_main_connection_error(self, mock_args):
        """Test event_handler_main handles connection errors."""
        mock_nc = MagicMock()
        mock_nc.is_connected = False
        mock_nc.connect = AsyncMock(side_effect=Exception("Connection failed"))

        with (
            patch("github_monitor.cli.event_handler.NATS", return_value=mock_nc),
            patch("github_monitor.cli.event_handler.check_claude_installed", return_value=True),
            patch("github_monitor.cli.event_handler.EventHandler"),
        ):
            result = await event_handler_main(mock_args)
            assert result == 1

    def test_event_handler_function_with_valid_params(self, tmp_path: Path):
        """Test event_handler function with valid parameters."""
        with (
            patch("github_monitor.cli.event_handler.asyncio.run", return_value=0),
            patch("sys.exit") as mock_exit,
        ):
            event_handler(path=tmp_path)
            mock_exit.assert_called_once_with(0)

    def test_event_handler_function_keyboard_interrupt(self, tmp_path: Path):
        """Test event_handler function handles keyboard interrupt."""
        with (
            patch("github_monitor.cli.event_handler.asyncio.run", side_effect=KeyboardInterrupt),
            patch("sys.exit") as mock_exit,
        ):
            event_handler(path=tmp_path)
            mock_exit.assert_called_once_with(0)

    def test_event_handler_function_with_custom_nats_server(self, tmp_path: Path):
        """Test event_handler function with custom NATS server."""
        with (
            patch(
                "github_monitor.cli.event_handler.event_handler_main", new_callable=AsyncMock, return_value=0
            ) as mock_main,
            patch("sys.exit"),
        ):
            event_handler(path=tmp_path, nats_server="nats://custom:4222")
            # Extract the args passed to event_handler_main
            assert mock_main.call_count == 1
            args = mock_main.call_args[0][0]
            assert args.nats_server == "nats://custom:4222"

    def test_event_handler_function_with_custom_stream_and_consumer(self, tmp_path: Path):
        """Test event_handler function with custom stream and consumer names."""
        with (
            patch(
                "github_monitor.cli.event_handler.event_handler_main", new_callable=AsyncMock, return_value=0
            ) as mock_main,
            patch("sys.exit"),
        ):
            event_handler(
                path=tmp_path,
                stream="CUSTOM_STREAM",
                consumer="custom-consumer",
            )
            args = mock_main.call_args[0][0]
            assert args.stream == "CUSTOM_STREAM"
            assert args.consumer == "custom-consumer"

    def test_event_handler_function_with_batch_and_timeout(self, tmp_path: Path):
        """Test event_handler function with custom batch size and timeout."""
        with (
            patch(
                "github_monitor.cli.event_handler.event_handler_main", new_callable=AsyncMock, return_value=0
            ) as mock_main,
            patch("sys.exit"),
        ):
            event_handler(
                path=tmp_path,
                batch_size=20,
                fetch_timeout=10.0,
            )
            args = mock_main.call_args[0][0]
            assert args.batch_size == 20
            assert args.fetch_timeout == 10.0

    def test_event_handler_function_with_skip_users(self, tmp_path: Path):
        """Test event_handler function with skip_users list."""
        with (
            patch(
                "github_monitor.cli.event_handler.event_handler_main", new_callable=AsyncMock, return_value=0
            ) as mock_main,
            patch("sys.exit"),
        ):
            event_handler(
                path=tmp_path,
                skip_users=["bot1", "bot2"],
            )
            args = mock_main.call_args[0][0]
            assert args.skip_users == ["bot1", "bot2"]

    def test_event_handler_function_with_recreate_consumer(self, tmp_path: Path):
        """Test event_handler function with recreate_consumer flag."""
        with (
            patch(
                "github_monitor.cli.event_handler.event_handler_main", new_callable=AsyncMock, return_value=0
            ) as mock_main,
            patch("sys.exit"),
        ):
            event_handler(
                path=tmp_path,
                recreate_consumer=True,
            )
            args = mock_main.call_args[0][0]
            assert args.recreate_consumer is True

    def test_event_handler_function_with_claude_verbose(self, tmp_path: Path):
        """Test event_handler function with claude_verbose flag."""
        with (
            patch(
                "github_monitor.cli.event_handler.event_handler_main", new_callable=AsyncMock, return_value=0
            ) as mock_main,
            patch("sys.exit"),
        ):
            event_handler(
                path=tmp_path,
                claude_verbose=True,
            )
            args = mock_main.call_args[0][0]
            assert args.claude_verbose is True

    def test_event_handler_function_with_auto_confirm(self, tmp_path: Path):
        """Test event_handler function with auto_confirm flag."""
        with (
            patch(
                "github_monitor.cli.event_handler.event_handler_main", new_callable=AsyncMock, return_value=0
            ) as mock_main,
            patch("sys.exit"),
        ):
            event_handler(
                path=tmp_path,
                auto_confirm=True,
            )
            args = mock_main.call_args[0][0]
            assert args.auto_confirm is True
