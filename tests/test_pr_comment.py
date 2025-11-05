"""Tests for PR comment functionality."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from github_monitor.pr_comment import create_pr_comment, create_pr_review_comment, get_github_token


def test_get_github_token_with_token() -> None:
    """Test creating GitHub token with provided token."""
    token = get_github_token(token="test_token")
    assert token == "test_token"


def test_get_github_token_without_token_raises() -> None:
    """Test that missing token raises ValueError."""
    with patch("github_monitor.pr_comment.get_github_client") as mock_get_client:
        mock_client = Mock()
        mock_client.token = None
        mock_get_client.return_value = mock_client

        with pytest.raises(ValueError, match="GitHub token is required"):
            get_github_token()


def test_get_github_token_from_env() -> None:
    """Test creating GitHub token from environment variable via client."""
    with patch("github_monitor.pr_comment.get_github_client") as mock_get_client:
        mock_client = Mock()
        mock_client.token = "env_token"
        mock_get_client.return_value = mock_client

        token = get_github_token()
        assert token == "env_token"


def test_create_pr_review_comment_success() -> None:
    """Test successful creation of PR review comment."""
    mock_response_pr_id = {
        "data": {"repository": {"pullRequest": {"id": "PR_kwDOABCDEF4"}}}
    }
    mock_response_comment = {
        "data": {
            "addPullRequestReviewThread": {
                "thread": {
                    "comments": {
                        "nodes": [
                            {"id": "comment123", "url": "https://github.com/owner/repo/pull/1#discussion_r123", "body": "Test comment"}
                        ]
                    }
                }
            }
        }
    }

    with patch("github_monitor.pr_comment.get_github_client") as mock_get_client:
        mock_client = Mock()
        mock_client.execute.side_effect = [mock_response_pr_id, mock_response_comment]
        mock_get_client.return_value = mock_client

        result = create_pr_review_comment(
            github_client="test_token",
            repo_name="owner/repo",
            pr_number=1,
            file_path="src/main.py",
            line_number=42,
            comment_body="Test comment",
        )

        assert result["html_url"] == "https://github.com/owner/repo/pull/1#discussion_r123"
        assert result["id"] == "comment123"
        assert result["body"] == "Test comment"


def test_create_pr_review_comment_with_commit_id() -> None:
    """Test PR review comment (commit parameter no longer used)."""
    mock_response_pr_id = {
        "data": {"repository": {"pullRequest": {"id": "PR_kwDOABCDEF4"}}}
    }
    mock_response_comment = {
        "data": {
            "addPullRequestReviewThread": {
                "thread": {
                    "comments": {
                        "nodes": [
                            {"id": "comment123", "url": "https://github.com/owner/repo/pull/1#discussion_r123", "body": "Test comment"}
                        ]
                    }
                }
            }
        }
    }

    with patch("github_monitor.pr_comment.get_github_client") as mock_get_client:
        mock_client = Mock()
        mock_client.execute.side_effect = [mock_response_pr_id, mock_response_comment]
        mock_get_client.return_value = mock_client

        result = create_pr_review_comment(
            github_client="test_token",
            repo_name="owner/repo",
            pr_number=1,
            file_path="src/main.py",
            line_number=42,
            comment_body="Test comment",
        )

        assert result["html_url"] == "https://github.com/owner/repo/pull/1#discussion_r123"
        # Should only query PR ID once
        assert mock_client.execute.call_count == 2


def test_create_pr_review_comment_github_error() -> None:
    """Test that GitHub API errors are properly raised."""
    with patch("github_monitor.pr_comment.get_github_client") as mock_get_client:
        mock_client = Mock()
        mock_client.execute.side_effect = ValueError("GraphQL errors: Not Found")
        mock_get_client.return_value = mock_client

        with pytest.raises(ValueError, match="Not Found"):
            create_pr_review_comment(
                github_client="test_token",
                repo_name="owner/repo",
                pr_number=1,
                file_path="src/main.py",
                line_number=42,
                comment_body="Test comment",
            )


def test_create_pr_comment_success() -> None:
    """Test successful creation of general PR comment."""
    mock_response_pr_id = {
        "data": {"repository": {"pullRequest": {"id": "PR_kwDOABCDEF4"}}}
    }
    mock_response_comment = {
        "data": {
            "addComment": {
                "commentEdge": {
                    "node": {"id": "comment123", "url": "https://github.com/owner/repo/pull/1#issuecomment-123", "body": "Test comment"}
                }
            }
        }
    }

    with patch("github_monitor.pr_comment.get_github_client") as mock_get_client:
        mock_client = Mock()
        mock_client.execute.side_effect = [mock_response_pr_id, mock_response_comment]
        mock_get_client.return_value = mock_client

        result = create_pr_comment(
            github_client="test_token", repo_name="owner/repo", pr_number=1, comment_body="Test comment"
        )

        assert result["html_url"] == "https://github.com/owner/repo/pull/1#issuecomment-123"
        assert result["id"] == "comment123"
        assert result["body"] == "Test comment"


def test_create_pr_comment_github_error() -> None:
    """Test that GitHub API errors are properly raised for general comments."""
    with patch("github_monitor.pr_comment.get_github_client") as mock_get_client:
        mock_client = Mock()
        mock_client.execute.side_effect = ValueError("GraphQL errors: Forbidden")
        mock_get_client.return_value = mock_client

        with pytest.raises(ValueError, match="Forbidden"):
            create_pr_comment(github_client="test_token", repo_name="owner/repo", pr_number=1, comment_body="Test comment")
