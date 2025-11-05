"""Tests for PR comment functionality."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from github import GithubException

from github_monitor.pr_comment import create_pr_comment, create_pr_review_comment, get_github_client, list_pr_files


def test_get_github_client_with_token() -> None:
    """Test creating GitHub client with provided token."""
    with patch("github_monitor.pr_comment.Github") as mock_github:
        client = get_github_client(token="test_token")
        assert client is not None
        mock_github.assert_called_once()


def test_get_github_client_without_token_raises() -> None:
    """Test that missing token raises ValueError."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="GITHUB_TOKEN"):
            get_github_client()


def test_get_github_client_from_env() -> None:
    """Test creating GitHub client from environment variable."""
    with patch.dict("os.environ", {"GITHUB_TOKEN": "env_token"}):
        with patch("github_monitor.pr_comment.Github") as mock_github:
            client = get_github_client()
            assert client is not None
            mock_github.assert_called_once()


def test_create_pr_review_comment_success() -> None:
    """Test successful creation of PR review comment."""
    mock_client = Mock()
    mock_repo = Mock()
    mock_pr = Mock()
    mock_commit = Mock()
    mock_commit.sha = "abc123"
    mock_comment = Mock()
    mock_comment.html_url = "https://github.com/owner/repo/pull/1#discussion_r123"

    mock_client.get_repo.return_value = mock_repo
    mock_repo.get_pull.return_value = mock_pr
    mock_pr.get_commits.return_value = [mock_commit]
    mock_repo.get_commit.return_value = mock_commit
    mock_pr.create_review_comment.return_value = mock_comment

    result = create_pr_review_comment(
        github_client=mock_client,
        repo_name="owner/repo",
        pr_number=1,
        file_path="src/main.py",
        line_number=42,
        comment_body="Test comment",
    )

    assert result == mock_comment
    mock_client.get_repo.assert_called_once_with("owner/repo")
    mock_repo.get_pull.assert_called_once_with(1)
    mock_pr.create_review_comment.assert_called_once()


def test_create_pr_review_comment_with_commit_id() -> None:
    """Test PR review comment with specific commit ID."""
    mock_client = Mock()
    mock_repo = Mock()
    mock_pr = Mock()
    mock_commit = Mock()
    mock_comment = Mock()

    mock_client.get_repo.return_value = mock_repo
    mock_repo.get_pull.return_value = mock_pr
    mock_repo.get_commit.return_value = mock_commit
    mock_pr.create_review_comment.return_value = mock_comment

    result = create_pr_review_comment(
        github_client=mock_client,
        repo_name="owner/repo",
        pr_number=1,
        file_path="src/main.py",
        line_number=42,
        comment_body="Test comment",
        commit_id="specific123",
    )

    assert result == mock_comment
    mock_repo.get_commit.assert_called_once_with("specific123")
    # Should not call get_commits when commit_id is provided
    mock_pr.get_commits.assert_not_called()


def test_create_pr_review_comment_github_error() -> None:
    """Test that GitHub API errors are properly raised."""
    mock_client = Mock()
    mock_repo = Mock()
    mock_pr = Mock()

    mock_client.get_repo.return_value = mock_repo
    mock_repo.get_pull.return_value = mock_pr

    github_error = GithubException(404, {"message": "Not Found"})
    mock_pr.get_commits.side_effect = github_error

    with pytest.raises(GithubException):
        create_pr_review_comment(
            github_client=mock_client,
            repo_name="owner/repo",
            pr_number=1,
            file_path="src/main.py",
            line_number=42,
            comment_body="Test comment",
        )


def test_create_pr_comment_success() -> None:
    """Test successful creation of general PR comment."""
    mock_client = Mock()
    mock_repo = Mock()
    mock_pr = Mock()
    mock_comment = Mock()
    mock_comment.html_url = "https://github.com/owner/repo/pull/1#issuecomment-123"

    mock_client.get_repo.return_value = mock_repo
    mock_repo.get_pull.return_value = mock_pr
    mock_pr.create_issue_comment.return_value = mock_comment

    result = create_pr_comment(
        github_client=mock_client, repo_name="owner/repo", pr_number=1, comment_body="Test comment"
    )

    assert result == mock_comment
    mock_client.get_repo.assert_called_once_with("owner/repo")
    mock_repo.get_pull.assert_called_once_with(1)
    mock_pr.create_issue_comment.assert_called_once_with("Test comment")


def test_create_pr_comment_github_error() -> None:
    """Test that GitHub API errors are properly raised for general comments."""
    mock_client = Mock()
    mock_repo = Mock()
    mock_pr = Mock()

    mock_client.get_repo.return_value = mock_repo
    mock_repo.get_pull.return_value = mock_pr

    github_error = GithubException(403, {"message": "Forbidden"})
    mock_pr.create_issue_comment.side_effect = github_error

    with pytest.raises(GithubException):
        create_pr_comment(github_client=mock_client, repo_name="owner/repo", pr_number=1, comment_body="Test comment")


def test_list_pr_files_success() -> None:
    """Test successful listing of PR files."""
    mock_client = Mock()
    mock_repo = Mock()
    mock_pr = Mock()

    mock_file1 = MagicMock()
    mock_file1.filename = "src/main.py"
    mock_file1.status = "modified"
    mock_file1.additions = 10
    mock_file1.deletions = 5
    mock_file1.changes = 15

    mock_file2 = MagicMock()
    mock_file2.filename = "tests/test_main.py"
    mock_file2.status = "added"
    mock_file2.additions = 20
    mock_file2.deletions = 0
    mock_file2.changes = 20

    mock_client.get_repo.return_value = mock_repo
    mock_repo.get_pull.return_value = mock_pr
    mock_pr.get_files.return_value = [mock_file1, mock_file2]

    result = list_pr_files(github_client=mock_client, repo_name="owner/repo", pr_number=1)

    assert len(result) == 2
    assert result[0]["filename"] == "src/main.py"
    assert result[0]["status"] == "modified"
    assert result[0]["additions"] == 10
    assert result[0]["deletions"] == 5
    assert result[0]["changes"] == 15

    assert result[1]["filename"] == "tests/test_main.py"
    assert result[1]["status"] == "added"
    assert result[1]["additions"] == 20
    assert result[1]["deletions"] == 0
    assert result[1]["changes"] == 20


def test_list_pr_files_github_error() -> None:
    """Test that GitHub API errors are properly raised when listing files."""
    mock_client = Mock()
    mock_repo = Mock()

    mock_client.get_repo.return_value = mock_repo

    github_error = GithubException(404, {"message": "Not Found"})
    mock_repo.get_pull.side_effect = github_error

    with pytest.raises(GithubException):
        list_pr_files(github_client=mock_client, repo_name="owner/repo", pr_number=1)
