"""Tests for github_monitor.event_handler module."""

import re
from pathlib import Path

import pytest

from github_monitor.event_handler import (
    EventHandler,
    create_issue_directory,
    find_template,
    remove_active_file,
    should_skip_repository,
    should_skip_user,
)


class TestCreateIssueDirectory:
    """Tests for create_issue_directory function."""

    def test_create_issue_directory(self, tmp_path: Path) -> None:
        """Test creating an issue directory."""
        result = create_issue_directory(tmp_path, "owner1/repo1", 123)

        expected_path = tmp_path / "owner1" / "repo1" / "123"
        assert result == expected_path
        assert result.exists()
        assert result.is_dir()

    def test_create_issue_directory_string_number(self, tmp_path: Path) -> None:
        """Test creating an issue directory with string number."""
        result = create_issue_directory(tmp_path, "owner1/repo1", "456")

        expected_path = tmp_path / "owner1" / "repo1" / "456"
        assert result == expected_path
        assert result.exists()

    def test_create_issue_directory_already_exists(self, tmp_path: Path) -> None:
        """Test creating an issue directory that already exists."""
        # Create directory first
        issue_dir = tmp_path / "owner1" / "repo1" / "123"
        issue_dir.mkdir(parents=True)

        # Should not raise error
        result = create_issue_directory(tmp_path, "owner1/repo1", 123)
        assert result == issue_dir
        assert result.exists()


class TestRemoveActiveFile:
    """Tests for remove_active_file function."""

    def test_remove_active_file_success(self, tmp_path: Path) -> None:
        """Test successfully removing .active file."""
        issue_dir = tmp_path / "owner1" / "repo1" / "123"
        issue_dir.mkdir(parents=True)
        active_file = issue_dir / ".active"
        active_file.touch()

        result = remove_active_file(tmp_path, "owner1/repo1", 123)
        assert result is True
        assert not active_file.exists()

    def test_remove_active_file_nonexistent(self, tmp_path: Path) -> None:
        """Test removing .active file that doesn't exist."""
        issue_dir = tmp_path / "owner1" / "repo1" / "123"
        issue_dir.mkdir(parents=True)

        result = remove_active_file(tmp_path, "owner1/repo1", 123)
        assert result is False

    def test_remove_active_file_string_number(self, tmp_path: Path) -> None:
        """Test removing .active file with string number."""
        issue_dir = tmp_path / "owner1" / "repo1" / "456"
        issue_dir.mkdir(parents=True)
        active_file = issue_dir / ".active"
        active_file.touch()

        result = remove_active_file(tmp_path, "owner1/repo1", "456")
        assert result is True
        assert not active_file.exists()


class TestFindTemplate:
    """Tests for find_template function."""

    def test_find_template_repo_specific(self, tmp_path: Path) -> None:
        """Test finding repository-specific template."""
        template_dir = tmp_path / "owner1" / "repo1"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "github.issue.new.md"
        template_file.write_text("Repo-specific template")

        result = find_template(tmp_path, "owner1/repo1", "github.issue.new")
        assert result == template_file

    def test_find_template_owner_default(self, tmp_path: Path) -> None:
        """Test finding owner default template."""
        template_dir = tmp_path / "owner1" / ".default"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "github.issue.new.md"
        template_file.write_text("Owner default template")

        result = find_template(tmp_path, "owner1/repo1", "github.issue.new")
        assert result == template_file

    def test_find_template_global_default(self, tmp_path: Path) -> None:
        """Test finding global default template."""
        template_dir = tmp_path / ".default"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "github.issue.new.md"
        template_file.write_text("Global default template")

        result = find_template(tmp_path, "owner1/repo1", "github.issue.new")
        assert result == template_file

    def test_find_template_hierarchy(self, tmp_path: Path) -> None:
        """Test template hierarchy - repo-specific takes precedence."""
        # Create all three levels
        global_dir = tmp_path / ".default"
        global_dir.mkdir(parents=True)
        (global_dir / "github.issue.new.md").write_text("Global")

        owner_dir = tmp_path / "owner1" / ".default"
        owner_dir.mkdir(parents=True)
        (owner_dir / "github.issue.new.md").write_text("Owner")

        repo_dir = tmp_path / "owner1" / "repo1"
        repo_dir.mkdir(parents=True)
        repo_template = repo_dir / "github.issue.new.md"
        repo_template.write_text("Repo")

        result = find_template(tmp_path, "owner1/repo1", "github.issue.new")
        assert result == repo_template

    def test_find_template_not_found(self, tmp_path: Path) -> None:
        """Test when no template is found."""
        result = find_template(tmp_path, "owner1/repo1", "github.issue.new")
        assert result is None

    def test_find_template_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test finding template when templates directory doesn't exist."""
        nonexistent = tmp_path / "nonexistent"
        result = find_template(nonexistent, "owner1/repo1", "github.issue.new")
        assert result is None

    def test_find_template_none_directory(self) -> None:
        """Test finding template when templates_dir is None."""
        result = find_template(None, "owner1/repo1", "github.issue.new")
        assert result is None


class TestEventHandler:
    """Tests for EventHandler class."""

    @pytest.fixture
    def handler(self, tmp_path: Path) -> EventHandler:
        """Create an EventHandler for testing."""
        return EventHandler(base_path=tmp_path, claude_available=False)

    @pytest.fixture
    def handler_with_templates(self, tmp_path: Path) -> EventHandler:
        """Create an EventHandler with templates directory."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        return EventHandler(base_path=tmp_path, claude_available=False, templates_dir=templates_dir)

    async def test_handle_new_issue(self, handler: EventHandler, tmp_path: Path) -> None:
        """Test handling new issue event."""
        data = {"repository": "owner1/repo1", "number": 123, "author": "user1"}

        await handler.handle_new_issue(data)

        issue_dir = tmp_path / "owner1" / "repo1" / "123"
        assert issue_dir.exists()

    async def test_handle_closed_issue(self, handler: EventHandler, tmp_path: Path) -> None:
        """Test handling closed issue event."""
        # Setup: create issue directory with .active file
        issue_dir = tmp_path / "owner1" / "repo1" / "123"
        issue_dir.mkdir(parents=True)
        active_file = issue_dir / ".active"
        active_file.touch()

        data = {"repository": "owner1/repo1", "number": 123, "author": "user1"}

        await handler.handle_closed_issue(data)

        assert not active_file.exists()

    async def test_handle_new_pr(self, handler: EventHandler, tmp_path: Path) -> None:
        """Test handling new PR event."""
        data = {"repository": "owner1/repo1", "number": 456, "author": "user1"}

        await handler.handle_new_pr(data)

        pr_dir = tmp_path / "owner1" / "repo1" / "456"
        assert pr_dir.exists()

    async def test_handle_closed_pr(self, handler: EventHandler, tmp_path: Path) -> None:
        """Test handling closed PR event."""
        # Setup: create PR directory with .active file
        pr_dir = tmp_path / "owner1" / "repo1" / "456"
        pr_dir.mkdir(parents=True)
        active_file = pr_dir / ".active"
        active_file.touch()

        data = {"repository": "owner1/repo1", "number": 456, "author": "user1"}

        await handler.handle_closed_pr(data)

        assert not active_file.exists()

    async def test_handle_updated_issue(self, handler: EventHandler) -> None:
        """Test handling updated issue event."""
        data = {"repository": "owner1/repo1", "number": 123, "author": "user1"}

        # Should not raise error even without Claude
        await handler.handle_updated_issue(data)

    async def test_handle_updated_pr(self, handler: EventHandler) -> None:
        """Test handling updated PR event."""
        data = {"repository": "owner1/repo1", "number": 456, "author": "user1"}

        # Should not raise error even without Claude
        await handler.handle_updated_pr(data)

    async def test_handle_issue_comment(self, handler: EventHandler) -> None:
        """Test handling issue comment event."""
        data = {
            "repository": "owner1/repo1",
            "number": 123,
            "comment": {
                "author": "user1",
                "created_at": "2024-01-01T00:00:00Z",
                "url": "https://github.com/owner1/repo1/issues/123#issuecomment-1",
            },
        }

        # Should not raise error
        await handler.handle_issue_comment(data)

    async def test_handle_pr_comment(self, handler: EventHandler) -> None:
        """Test handling PR comment event."""
        data = {
            "repository": "owner1/repo1",
            "number": 456,
            "comment": {
                "author": "user1",
                "created_at": "2024-01-01T00:00:00Z",
                "url": "https://github.com/owner1/repo1/pull/456#issuecomment-1",
            },
        }

        # Should not raise error
        await handler.handle_pr_comment(data)


class TestShouldSkipUser:
    """Tests for should_skip_user function."""

    def test_should_skip_user_matches_pattern(self) -> None:
        """Test skipping user that matches pattern."""
        pattern = re.compile(r"^bot[12]$")
        assert should_skip_user("bot1", pattern) is True
        assert should_skip_user("bot2", pattern) is True

    def test_should_skip_user_no_match(self) -> None:
        """Test not skipping user that doesn't match pattern."""
        pattern = re.compile(r"^bot[12]$")
        assert should_skip_user("user1", pattern) is False
        assert should_skip_user("random", pattern) is False
        assert should_skip_user("bot3", pattern) is False

    def test_should_skip_user_prefix_pattern(self) -> None:
        """Test skipping user with prefix pattern."""
        pattern = re.compile(r"^bot-")
        assert should_skip_user("bot-user", pattern) is True
        assert should_skip_user("bot-123", pattern) is True
        assert should_skip_user("user-bot", pattern) is False

    def test_should_skip_user_no_pattern(self) -> None:
        """Test when no skip pattern is configured."""
        assert should_skip_user("anyone", None) is False
        assert should_skip_user("bot1", None) is False


class TestShouldSkipRepository:
    """Tests for should_skip_repository function."""

    def test_should_skip_repository_matches_pattern(self) -> None:
        """Test not skipping repository that matches pattern."""
        pattern = re.compile(r"^owner1/")
        assert should_skip_repository("owner1/repo1", pattern) is False
        assert should_skip_repository("owner1/repo2", pattern) is False

    def test_should_skip_repository_no_match(self) -> None:
        """Test skipping repository that doesn't match pattern."""
        pattern = re.compile(r"^owner1/")
        assert should_skip_repository("owner2/repo1", pattern) is True
        assert should_skip_repository("other/repo", pattern) is True

    def test_should_skip_repository_specific_repo(self) -> None:
        """Test with specific repository pattern."""
        pattern = re.compile(r"^owner1/repo1$")
        assert should_skip_repository("owner1/repo1", pattern) is False
        assert should_skip_repository("owner1/repo2", pattern) is True
        assert should_skip_repository("owner2/repo1", pattern) is True

    def test_should_skip_repository_no_pattern(self) -> None:
        """Test when no repository filter is configured."""
        assert should_skip_repository("any/repo", None) is False
        assert should_skip_repository("owner/project", None) is False
