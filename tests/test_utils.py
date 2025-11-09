"""Tests for github_monitor.utils module."""

from datetime import timedelta

from github_monitor.utils import parse_duration_to_timedelta


class TestParseDurationToTimedelta:
    """Tests for parse_duration_to_timedelta function."""

    def test_parse_seconds(self) -> None:
        """Test parsing seconds."""
        assert parse_duration_to_timedelta("30s") == timedelta(seconds=30)
        assert parse_duration_to_timedelta("1s") == timedelta(seconds=1)

    def test_parse_minutes(self) -> None:
        """Test parsing minutes."""
        assert parse_duration_to_timedelta("5m") == timedelta(seconds=300)
        assert parse_duration_to_timedelta("1m") == timedelta(seconds=60)

    def test_parse_hours(self) -> None:
        """Test parsing hours."""
        assert parse_duration_to_timedelta("1h") == timedelta(seconds=3600)
        assert parse_duration_to_timedelta("2h") == timedelta(seconds=7200)

    def test_parse_days(self) -> None:
        """Test parsing days."""
        assert parse_duration_to_timedelta("1d") == timedelta(seconds=86400)
        assert parse_duration_to_timedelta("2d") == timedelta(seconds=172800)

    def test_parse_combined(self) -> None:
        """Test parsing combined duration strings."""
        assert parse_duration_to_timedelta("1h30m") == timedelta(seconds=5400)
        assert parse_duration_to_timedelta("1d12h") == timedelta(seconds=129600)
        assert parse_duration_to_timedelta("2d5h30m15s") == timedelta(seconds=192615)

    def test_parse_empty_string(self) -> None:
        """Test that empty string returns default."""
        assert parse_duration_to_timedelta("") == timedelta(seconds=5)

    def test_parse_invalid_format(self) -> None:
        """Test that invalid format returns default."""
        assert parse_duration_to_timedelta("abc") == timedelta(seconds=5)
        assert parse_duration_to_timedelta("5") == timedelta(seconds=5)
        assert parse_duration_to_timedelta("5x") == timedelta(seconds=5)
