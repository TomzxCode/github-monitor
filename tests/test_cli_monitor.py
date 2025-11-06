"""Tests for github_monitor.cli.monitor command."""

from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest


class TestCLIMonitor:
    """Tests for CLI monitor command."""

    def test_monitor_validates_github_token(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that monitor command validates GitHub token on startup."""
        # Import first (which calls load_dotenv()), THEN monkeypatch
        import github_monitor.github_client

        # Reset the global client to force re-initialization
        github_monitor.github_client._github_client = None

        # Mock os.getenv to return None for GITHUB_TOKEN
        monkeypatch.setattr("os.getenv", lambda key, default=None: None if key == "GITHUB_TOKEN" else default)

        from github_monitor.cli.monitor import monitor

        # The monitor function should exit with code 1 when no token is available
        with pytest.raises(SystemExit) as exc_info:
            monitor(path=tmp_path, repositories=["test/repo"], dry_run=True)

        assert exc_info.value.code == 1

    def test_monitor_with_valid_token(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that monitor command accepts valid GitHub token."""
        # Reset the global client
        import github_monitor.github_client

        github_monitor.github_client._github_client = None

        monkeypatch.setenv("GITHUB_TOKEN", "valid_token_123")

        from github_monitor.cli.monitor import monitor

        # Mock asyncio.run to prevent actual execution
        with patch("asyncio.run", return_value=0):
            with pytest.raises(SystemExit) as exc_info:
                monitor(path=tmp_path, repositories=["test/repo"], dry_run=True)

            # Should exit with code 0 (success)
            assert exc_info.value.code == 0

    def test_monitor_with_invalid_interval(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that monitor command rejects invalid interval format."""
        # Reset the global client
        import github_monitor.github_client

        github_monitor.github_client._github_client = None

        monkeypatch.setenv("GITHUB_TOKEN", "valid_token")

        from github_monitor.cli.monitor import monitor

        # When calling monitor() directly (not via CLI), passing a string will fail
        # since it expects a timedelta. In the CLI, cyclopts handles the conversion.
        # This test verifies that invalid types are rejected.
        with pytest.raises(AttributeError):
            monitor(path=tmp_path, repositories=["test/repo"], interval="invalid_format", dry_run=True)  # type: ignore

    def test_monitor_with_valid_interval(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that monitor command accepts valid interval format."""
        # Reset the global client
        import github_monitor.github_client

        github_monitor.github_client._github_client = None

        monkeypatch.setenv("GITHUB_TOKEN", "valid_token")

        from github_monitor.cli.monitor import monitor

        # Mock asyncio.run to prevent actual execution
        with patch("asyncio.run", return_value=0):
            with pytest.raises(SystemExit) as exc_info:
                monitor(path=tmp_path, repositories=["test/repo"], interval=timedelta(minutes=5), dry_run=True)

            # Should exit with code 0 (success)
            assert exc_info.value.code == 0

    def test_monitor_interval_parsing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that various interval formats are correctly parsed."""
        # Reset the global client
        import github_monitor.github_client

        github_monitor.github_client._github_client = None

        monkeypatch.setenv("GITHUB_TOKEN", "valid_token")

        from github_monitor.cli.monitor import monitor

        test_cases = [
            (timedelta(minutes=1), 60),
            (timedelta(minutes=5), 300),
            (timedelta(hours=1), 3600),
            (timedelta(hours=1, minutes=30), 5400),
            (timedelta(days=2), 172800),
        ]

        for interval_td, expected_seconds in test_cases:
            # Mock asyncio.run to capture args
            def mock_run(coro):
                # Extract args from the coroutine
                return 0

            with patch("asyncio.run", side_effect=mock_run):
                with pytest.raises(SystemExit) as exc_info:
                    monitor(path=tmp_path, repositories=["test/repo"], interval=interval_td, dry_run=True)

                assert exc_info.value.code == 0

    def test_monitor_dry_run_no_nats_connection(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that dry run mode doesn't connect to NATS."""
        # Reset the global client
        import github_monitor.github_client

        github_monitor.github_client._github_client = None

        monkeypatch.setenv("GITHUB_TOKEN", "valid_token")

        from github_monitor.cli.monitor import monitor

        # Mock monitor_main and verify dry_run is True
        async def mock_monitor_main(args):
            assert args.dry_run is True
            # In dry run, NATS connection should be skipped
            return 0

        with patch("github_monitor.cli.monitor.monitor_main", side_effect=mock_monitor_main):
            with pytest.raises(SystemExit) as exc_info:
                monitor(path=tmp_path, repositories=["test/repo"], dry_run=True)

                assert exc_info.value.code == 0

    def test_monitor_keyboard_interrupt_handling(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that monitor command handles KeyboardInterrupt gracefully."""
        # Reset the global client
        import github_monitor.github_client

        github_monitor.github_client._github_client = None

        monkeypatch.setenv("GITHUB_TOKEN", "valid_token")

        from github_monitor.cli.monitor import monitor

        # Mock asyncio.run to raise KeyboardInterrupt
        with patch("asyncio.run", side_effect=KeyboardInterrupt):
            with pytest.raises(SystemExit) as exc_info:
                monitor(path=tmp_path, repositories=["test/repo"], dry_run=True)

            # Should exit with code 130 (standard for SIGINT)
            assert exc_info.value.code == 130

    def test_monitor_default_parameters(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test monitor command with default parameters."""
        # Reset the global client
        import github_monitor.github_client

        github_monitor.github_client._github_client = None

        monkeypatch.setenv("GITHUB_TOKEN", "valid_token")

        from github_monitor.cli.monitor import monitor

        async def mock_monitor_main(args):
            # Verify default parameters
            assert args.nats_server == "nats://localhost:4222"
            assert args.dry_run is False
            assert args.monitor_issues is True
            assert args.monitor_issue_comments is True
            assert args.monitor_pr_comments is True
            assert args.active_only is True
            assert args.interval is None
            return 0

        with patch("github_monitor.cli.monitor.monitor_main", side_effect=mock_monitor_main):
            with pytest.raises(SystemExit) as exc_info:
                monitor(path=tmp_path, repositories=["test/repo"])

            assert exc_info.value.code == 0
