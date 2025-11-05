"""Tests for the pr-comment CLI command."""

from unittest.mock import Mock, patch

import pytest

from github_monitor.cli.pr_comment import pr_comment


class TestPrCommentCommand:
    """Tests for the pr-comment CLI command."""

    def test_pr_comment_list_files(self):
        """Test listing files in a PR."""
        mock_client = Mock()
        mock_files = [
            {
                "filename": "src/main.py",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
                "changes": 15,
            },
            {
                "filename": "tests/test_main.py",
                "status": "added",
                "additions": 50,
                "deletions": 0,
                "changes": 50,
            },
        ]

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            patch("github_monitor.pr_comment.list_pr_files", return_value=mock_files),
        ):
            # Should not raise an exception
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                list_files=True,
            )

    def test_pr_comment_create_general_comment(self):
        """Test creating a general PR comment."""
        mock_client = Mock()
        mock_comment = Mock()
        mock_comment.html_url = "https://github.com/owner/repo/pull/123#issuecomment-123456"

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            patch("github_monitor.pr_comment.create_pr_comment", return_value=mock_comment) as mock_create,
        ):
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                comment="Looks good to me!",
            )
            mock_create.assert_called_once_with(mock_client, "owner/repo", 123, "Looks good to me!")

    def test_pr_comment_create_line_comment(self):
        """Test creating a line-specific PR comment."""
        mock_client = Mock()
        mock_comment = Mock()
        mock_comment.html_url = "https://github.com/owner/repo/pull/123#discussion_r123456"

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            patch("github_monitor.pr_comment.create_pr_review_comment", return_value=mock_comment) as mock_create,
        ):
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                file="src/main.py",
                line=42,
                comment="This needs refactoring",
            )
            mock_create.assert_called_once_with(
                mock_client,
                "owner/repo",
                123,
                "src/main.py",
                42,
                "This needs refactoring",
                None,
            )

    def test_pr_comment_create_line_comment_with_commit(self):
        """Test creating a line-specific PR comment with commit SHA."""
        mock_client = Mock()
        mock_comment = Mock()
        mock_comment.html_url = "https://github.com/owner/repo/pull/123#discussion_r123456"

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            patch("github_monitor.pr_comment.create_pr_review_comment", return_value=mock_comment) as mock_create,
        ):
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                file="src/main.py",
                line=42,
                comment="Fix this",
                commit="abc123",
            )
            mock_create.assert_called_once_with(
                mock_client,
                "owner/repo",
                123,
                "src/main.py",
                42,
                "Fix this",
                "abc123",
            )

    def test_pr_comment_with_custom_token(self):
        """Test pr_comment with custom GitHub token."""
        mock_client = Mock()
        mock_comment = Mock()
        mock_comment.html_url = "https://github.com/owner/repo/pull/123#issuecomment-123456"

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client) as mock_get_client,
            patch("github_monitor.pr_comment.create_pr_comment", return_value=mock_comment),
        ):
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                comment="Test",
                token="custom_token_123",
            )
            mock_get_client.assert_called_once_with("custom_token_123")

    def test_pr_comment_missing_required_params(self):
        """Test that pr_comment raises error when missing required parameters."""
        mock_client = Mock()

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            pytest.raises(SystemExit) as exc_info,
        ):
            # No list_files, no comment - should fail validation
            pr_comment(
                repo="owner/repo",
                pr_number=123,
            )

        assert exc_info.value.code == 1

    def test_pr_comment_file_without_line(self):
        """Test that providing file without line creates a general comment."""
        mock_client = Mock()
        mock_comment = Mock()
        mock_comment.html_url = "https://github.com/owner/repo/pull/123#issuecomment-123456"

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            patch("github_monitor.pr_comment.create_pr_comment", return_value=mock_comment) as mock_create,
        ):
            # File specified but no line - creates general comment
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                file="src/main.py",
                comment="Test",
            )
            # Should create a general comment, ignoring the file parameter
            mock_create.assert_called_once_with(mock_client, "owner/repo", 123, "Test")

    def test_pr_comment_line_without_file(self):
        """Test that providing line without file creates a general comment."""
        mock_client = Mock()
        mock_comment = Mock()
        mock_comment.html_url = "https://github.com/owner/repo/pull/123#issuecomment-123456"

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            patch("github_monitor.pr_comment.create_pr_comment", return_value=mock_comment) as mock_create,
        ):
            # Line specified but no file - creates general comment
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                line=42,
                comment="Test",
            )
            # Should create a general comment, ignoring the line parameter
            mock_create.assert_called_once_with(mock_client, "owner/repo", 123, "Test")

    def test_pr_comment_github_api_error(self):
        """Test handling of GitHub API errors."""
        mock_client = Mock()

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            patch(
                "github_monitor.pr_comment.create_pr_comment",
                side_effect=Exception("GitHub API error"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                comment="Test",
            )

        assert exc_info.value.code == 1

    def test_pr_comment_authentication_error(self):
        """Test handling of authentication errors."""
        with (
            patch(
                "github_monitor.pr_comment.get_github_client",
                side_effect=ValueError("GITHUB_TOKEN not found"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                comment="Test",
            )

        assert exc_info.value.code == 1

    def test_pr_comment_list_files_empty(self):
        """Test listing files when PR has no files."""
        mock_client = Mock()

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            patch("github_monitor.pr_comment.list_pr_files", return_value=[]),
        ):
            # Should not raise an exception
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                list_files=True,
            )

    def test_pr_comment_invalid_repo_format(self):
        """Test with invalid repository format."""
        mock_client = Mock()

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            patch(
                "github_monitor.pr_comment.create_pr_comment",
                side_effect=Exception("Invalid repository format"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            pr_comment(
                repo="invalid-repo-format",
                pr_number=123,
                comment="Test",
            )

        assert exc_info.value.code == 1

    def test_pr_comment_invalid_pr_number(self):
        """Test with invalid PR number."""
        mock_client = Mock()

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            patch(
                "github_monitor.pr_comment.create_pr_comment",
                side_effect=Exception("PR not found"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            pr_comment(
                repo="owner/repo",
                pr_number=999999,
                comment="Test",
            )

        assert exc_info.value.code == 1

    def test_pr_comment_multiple_files_listed(self):
        """Test listing multiple files in a PR."""
        mock_client = Mock()
        mock_files = [
            {
                "filename": "src/file1.py",
                "status": "modified",
                "additions": 5,
                "deletions": 2,
                "changes": 7,
            },
            {
                "filename": "src/file2.py",
                "status": "added",
                "additions": 100,
                "deletions": 0,
                "changes": 100,
            },
            {
                "filename": "src/file3.py",
                "status": "deleted",
                "additions": 0,
                "deletions": 50,
                "changes": 50,
            },
        ]

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            patch("github_monitor.pr_comment.list_pr_files", return_value=mock_files) as mock_list,
        ):
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                list_files=True,
            )
            mock_list.assert_called_once_with(mock_client, "owner/repo", 123)

    def test_pr_comment_line_comment_without_comment_text(self):
        """Test that line comment requires comment text."""
        mock_client = Mock()

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            pytest.raises(SystemExit) as exc_info,
        ):
            # File and line specified but no comment text
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                file="src/main.py",
                line=42,
            )

        assert exc_info.value.code == 1

    def test_pr_comment_environment_token_fallback(self):
        """Test that pr_comment falls back to environment token when not provided."""
        mock_client = Mock()
        mock_comment = Mock()
        mock_comment.html_url = "https://github.com/owner/repo/pull/123#issuecomment-123456"

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client) as mock_get_client,
            patch("github_monitor.pr_comment.create_pr_comment", return_value=mock_comment),
        ):
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                comment="Test",
                token=None,  # Explicitly None to test fallback
            )
            # Should be called with None to trigger environment lookup
            mock_get_client.assert_called_once_with(None)

    def test_pr_comment_with_all_file_statuses(self):
        """Test listing files with all possible statuses."""
        mock_client = Mock()
        mock_files = [
            {
                "filename": "modified.py",
                "status": "modified",
                "additions": 5,
                "deletions": 2,
                "changes": 7,
            },
            {
                "filename": "added.py",
                "status": "added",
                "additions": 100,
                "deletions": 0,
                "changes": 100,
            },
            {
                "filename": "deleted.py",
                "status": "removed",
                "additions": 0,
                "deletions": 50,
                "changes": 50,
            },
            {
                "filename": "renamed.py",
                "status": "renamed",
                "additions": 10,
                "deletions": 8,
                "changes": 18,
            },
        ]

        with (
            patch("github_monitor.pr_comment.get_github_client", return_value=mock_client),
            patch("github_monitor.pr_comment.list_pr_files", return_value=mock_files),
        ):
            # Should handle all file statuses without error
            pr_comment(
                repo="owner/repo",
                pr_number=123,
                list_files=True,
            )
