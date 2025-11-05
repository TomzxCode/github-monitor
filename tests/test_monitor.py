"""Tests for github_monitor.monitor module."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from github_monitor.monitor import (
    find_active_issues,
    get_last_checked,
    get_last_comment_check,
    get_tracked_repositories,
    get_type_from_file,
    parse_duration,
    save_last_checked,
    save_last_comment_check,
    save_type_to_file,
)


class TestParseDuration:
    """Tests for parse_duration function."""

    def test_parse_seconds(self) -> None:
        """Test parsing seconds."""
        assert parse_duration("30s") == 30
        assert parse_duration("1s") == 1

    def test_parse_minutes(self) -> None:
        """Test parsing minutes."""
        assert parse_duration("5m") == 300
        assert parse_duration("1m") == 60

    def test_parse_hours(self) -> None:
        """Test parsing hours."""
        assert parse_duration("1h") == 3600
        assert parse_duration("2h") == 7200

    def test_parse_days(self) -> None:
        """Test parsing days."""
        assert parse_duration("1d") == 86400
        assert parse_duration("2d") == 172800

    def test_parse_combined(self) -> None:
        """Test parsing combined duration strings."""
        assert parse_duration("1h30m") == 5400
        assert parse_duration("1d12h") == 129600
        assert parse_duration("2d5h30m15s") == 192615

    def test_parse_empty_string(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Duration string cannot be empty"):
            parse_duration("")

    def test_parse_invalid_format(self) -> None:
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("abc")
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("5")
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("5x")

    def test_parse_partial_invalid(self) -> None:
        """Test that partially invalid strings raise ValueError."""
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("5m abc")


class TestFindActiveIssues:
    """Tests for find_active_issues function."""

    def test_find_active_issues_empty_directory(self, tmp_path: Path) -> None:
        """Test finding active issues in empty directory."""
        result = find_active_issues(tmp_path)
        assert result == []

    def test_find_active_issues_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test finding active issues in nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        result = find_active_issues(nonexistent)
        assert result == []

    def test_find_active_issues_with_active_flag(self, tmp_path: Path) -> None:
        """Test finding issues with .active flag."""
        # Create directory structure: owner/repo/123/.active
        issue_dir = tmp_path / "owner1" / "repo1" / "123"
        issue_dir.mkdir(parents=True)
        (issue_dir / ".active").touch()

        # Create another issue without .active flag
        issue_dir2 = tmp_path / "owner1" / "repo1" / "456"
        issue_dir2.mkdir(parents=True)

        result = find_active_issues(tmp_path, active_only=True)
        assert result == [("owner1/repo1", "123")]

    def test_find_active_issues_all(self, tmp_path: Path) -> None:
        """Test finding all issues regardless of .active flag."""
        # Create two issues, only one with .active flag
        issue_dir1 = tmp_path / "owner1" / "repo1" / "123"
        issue_dir1.mkdir(parents=True)
        (issue_dir1 / ".active").touch()

        issue_dir2 = tmp_path / "owner1" / "repo1" / "456"
        issue_dir2.mkdir(parents=True)

        result = find_active_issues(tmp_path, active_only=False)
        assert sorted(result) == [("owner1/repo1", "123"), ("owner1/repo1", "456")]

    def test_find_active_issues_multiple_repos(self, tmp_path: Path) -> None:
        """Test finding issues across multiple repositories."""
        # Create issues in different repos
        issue1 = tmp_path / "owner1" / "repo1" / "123"
        issue1.mkdir(parents=True)
        (issue1 / ".active").touch()

        issue2 = tmp_path / "owner2" / "repo2" / "456"
        issue2.mkdir(parents=True)
        (issue2 / ".active").touch()

        result = find_active_issues(tmp_path, active_only=True)
        assert sorted(result) == [("owner1/repo1", "123"), ("owner2/repo2", "456")]

    def test_find_active_issues_with_repository_filter(self, tmp_path: Path) -> None:
        """Test finding issues with repository filter."""
        # Create issues in different repos
        issue1 = tmp_path / "owner1" / "repo1" / "123"
        issue1.mkdir(parents=True)
        (issue1 / ".active").touch()

        issue2 = tmp_path / "owner2" / "repo2" / "456"
        issue2.mkdir(parents=True)
        (issue2 / ".active").touch()

        result = find_active_issues(tmp_path, active_only=True, repositories=["owner1/repo1"])
        assert result == [("owner1/repo1", "123")]


class TestGetTrackedRepositories:
    """Tests for get_tracked_repositories function."""

    def test_get_tracked_repositories_empty(self, tmp_path: Path) -> None:
        """Test getting tracked repositories from empty directory."""
        result = get_tracked_repositories(tmp_path)
        assert result == []

    def test_get_tracked_repositories_nonexistent(self, tmp_path: Path) -> None:
        """Test getting tracked repositories from nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        result = get_tracked_repositories(nonexistent)
        assert result == []

    def test_get_tracked_repositories_single_repo(self, tmp_path: Path) -> None:
        """Test getting single tracked repository."""
        repo_dir = tmp_path / "owner1" / "repo1"
        repo_dir.mkdir(parents=True)

        result = get_tracked_repositories(tmp_path)
        assert result == ["owner1/repo1"]

    def test_get_tracked_repositories_multiple_repos(self, tmp_path: Path) -> None:
        """Test getting multiple tracked repositories."""
        repo1 = tmp_path / "owner1" / "repo1"
        repo1.mkdir(parents=True)

        repo2 = tmp_path / "owner2" / "repo2"
        repo2.mkdir(parents=True)

        result = get_tracked_repositories(tmp_path)
        assert sorted(result) == ["owner1/repo1", "owner2/repo2"]


class TestLastCheckedTimestamp:
    """Tests for last checked timestamp functions."""

    def test_get_last_checked_nonexistent(self, tmp_path: Path) -> None:
        """Test getting last checked timestamp when file doesn't exist."""
        result = get_last_checked(tmp_path, "owner1/repo1", "123")
        assert result is None

    def test_save_and_get_last_checked(self, tmp_path: Path) -> None:
        """Test saving and retrieving last checked timestamp."""
        timestamp = datetime.now(timezone.utc).isoformat()
        save_last_checked(tmp_path, "owner1/repo1", "123", timestamp)

        result = get_last_checked(tmp_path, "owner1/repo1", "123")
        assert result == timestamp

    def test_save_last_checked_creates_directory(self, tmp_path: Path) -> None:
        """Test that saving creates directory structure."""
        timestamp = datetime.now(timezone.utc).isoformat()
        save_last_checked(tmp_path, "owner1/repo1", "123", timestamp)

        issue_dir = tmp_path / "owner1" / "repo1" / "123"
        assert issue_dir.exists()
        assert (issue_dir / ".last_checked").exists()


class TestLastCommentCheckTimestamp:
    """Tests for last comment check timestamp functions."""

    def test_get_last_comment_check_nonexistent(self, tmp_path: Path) -> None:
        """Test getting last comment check when file doesn't exist."""
        result = get_last_comment_check(tmp_path, "owner1/repo1", "123")
        assert result is None

    def test_save_and_get_last_comment_check(self, tmp_path: Path) -> None:
        """Test saving and retrieving last comment check."""
        # Create directory first
        issue_dir = tmp_path / "owner1" / "repo1" / "123"
        issue_dir.mkdir(parents=True)

        timestamp = datetime.now(timezone.utc).isoformat()
        save_last_comment_check(tmp_path, "owner1/repo1", "123", timestamp)

        result = get_last_comment_check(tmp_path, "owner1/repo1", "123")
        assert result == timestamp

    def test_unified_comment_check_for_issues_and_prs(self, tmp_path: Path) -> None:
        """Test that issues and PRs use the same unified comment check timestamp."""
        issue_dir = tmp_path / "owner1" / "repo1" / "123"
        issue_dir.mkdir(parents=True)

        timestamp = "2024-01-01T00:00:00Z"
        save_last_comment_check(tmp_path, "owner1/repo1", "123", timestamp)

        result = get_last_comment_check(tmp_path, "owner1/repo1", "123")
        assert result == timestamp

        # Verify only one file exists
        assert (issue_dir / ".last_comment_check").exists()
        assert not (issue_dir / ".last_issue_comment_check").exists()
        assert not (issue_dir / ".last_pr_comment_check").exists()


class TestTypeFile:
    """Tests for type file functions."""

    def test_get_type_from_file_nonexistent(self, tmp_path: Path) -> None:
        """Test getting type when file doesn't exist."""
        result = get_type_from_file(tmp_path, "owner1/repo1", "123")
        assert result is None

    def test_save_and_get_type_issue(self, tmp_path: Path) -> None:
        """Test saving and retrieving issue type."""
        save_type_to_file(tmp_path, "owner1/repo1", "123", "issue")

        result = get_type_from_file(tmp_path, "owner1/repo1", "123")
        assert result == "issue"

    def test_save_and_get_type_pr(self, tmp_path: Path) -> None:
        """Test saving and retrieving PR type."""
        save_type_to_file(tmp_path, "owner1/repo1", "123", "pr")

        result = get_type_from_file(tmp_path, "owner1/repo1", "123")
        assert result == "pr"

    def test_save_type_creates_directory(self, tmp_path: Path) -> None:
        """Test that saving type creates directory structure."""
        save_type_to_file(tmp_path, "owner1/repo1", "123", "issue")

        issue_dir = tmp_path / "owner1" / "repo1" / "123"
        assert issue_dir.exists()
        assert (issue_dir / ".type").exists()

    def test_get_type_invalid_content(self, tmp_path: Path) -> None:
        """Test that invalid type content returns None."""
        issue_dir = tmp_path / "owner1" / "repo1" / "123"
        issue_dir.mkdir(parents=True)
        (issue_dir / ".type").write_text("invalid")

        result = get_type_from_file(tmp_path, "owner1/repo1", "123")
        assert result is None
