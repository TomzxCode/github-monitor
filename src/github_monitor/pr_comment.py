"""Submit comments on GitHub Pull Requests at specific lines in files.

This module uses the PyGithub library to interact with the GitHub API.
It can create both general PR comments and line-specific review comments.
"""

import os
from typing import Optional

import structlog
from dotenv import load_dotenv
from github import Auth, Github
from github.GithubException import GithubException
from github.IssueComment import IssueComment
from github.PullRequestComment import PullRequestComment


logger = structlog.get_logger()


def get_github_client(token: Optional[str] = None) -> Github:
    """Initialize and return a GitHub client with authentication.

    Args:
        token: GitHub token. If not provided, loads from GITHUB_TOKEN environment variable.

    Returns:
        Authenticated Github client instance

    Raises:
        ValueError: If no token is provided and GITHUB_TOKEN is not set
    """
    if token is None:
        # Load environment variables if not already loaded
        load_dotenv()
        token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is not set or token not provided")

    auth = Auth.Token(token)
    return Github(auth=auth)


def create_pr_review_comment(
    github_client: Github,
    repo_name: str,
    pr_number: int,
    file_path: str,
    line_number: int,
    comment_body: str,
    commit_id: Optional[str] = None,
) -> PullRequestComment:
    """Create a review comment on a specific line of a file in a PR.

    Args:
        github_client: Authenticated Github client instance
        repo_name: Repository name in format "owner/repo"
        pr_number: Pull request number
        file_path: Path to the file relative to repository root
        line_number: Line number to comment on
        comment_body: The comment text
        commit_id: Optional specific commit SHA. If not provided, uses the latest commit in the PR.

    Returns:
        The created comment object

    Raises:
        GithubException: If the GitHub API returns an error
    """
    try:
        # Get the repository
        repo = github_client.get_repo(repo_name)

        # Get the pull request
        pr = repo.get_pull(pr_number)

        # If no commit_id provided, use the latest commit in the PR
        if not commit_id:
            commits = list(pr.get_commits())
            commit_id = commits[-1].sha
            logger.info("using_latest_commit", commit_id=commit_id)

        # Create a review comment on the specific line
        # Note: GitHub API requires the comment to be on a line that was changed in the PR
        comment = pr.create_review_comment(
            body=comment_body, commit=repo.get_commit(commit_id), path=file_path, line=line_number
        )

        logger.info("comment_created", url=comment.html_url)
        return comment

    except GithubException as e:
        logger.error(
            "github_api_error",
            status=e.status,
            message=e.data.get("message", "Unknown error"),
            errors=e.data.get("errors"),
        )
        raise
    except Exception as e:
        logger.error("unexpected_error", error=str(e))
        raise


def create_pr_comment(
    github_client: Github,
    repo_name: str,
    pr_number: int,
    comment_body: str,
) -> IssueComment:
    """Create a general comment on a PR (not tied to a specific line).

    Args:
        github_client: Authenticated Github client instance
        repo_name: Repository name in format "owner/repo"
        pr_number: Pull request number
        comment_body: The comment text

    Returns:
        The created comment object

    Raises:
        GithubException: If the GitHub API returns an error
    """
    try:
        # Get the repository
        repo = github_client.get_repo(repo_name)

        # Get the pull request
        pr = repo.get_pull(pr_number)

        # Create a general comment
        comment = pr.create_issue_comment(comment_body)

        logger.info("comment_created", url=comment.html_url)
        return comment

    except GithubException as e:
        logger.error("github_api_error", status=e.status, message=e.data.get("message", "Unknown error"))
        raise
    except Exception as e:
        logger.error("unexpected_error", error=str(e))
        raise


def list_pr_files(github_client: Github, repo_name: str, pr_number: int) -> list[dict[str, str | int]]:
    """List all files changed in a PR.

    Args:
        github_client: Authenticated Github client instance
        repo_name: Repository name in format "owner/repo"
        pr_number: Pull request number

    Returns:
        List of dictionaries containing file information with keys:
        - filename: str
        - status: str
        - additions: int
        - deletions: int
        - changes: int

    Raises:
        GithubException: If the GitHub API returns an error
    """
    try:
        repo = github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        files = []
        for file in pr.get_files():
            files.append(
                {
                    "filename": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                }
            )

        logger.info("files_listed", pr_number=pr_number, file_count=len(files))
        return files

    except GithubException as e:
        logger.error("github_api_error", status=e.status, message=e.data.get("message", "Unknown error"))
        raise
