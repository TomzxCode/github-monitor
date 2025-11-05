"""CLI command for submitting comments on GitHub Pull Requests."""

from typing import Annotated, Optional

import cyclopts
import structlog

from github_monitor import pr_comment as pr_comment_module


logger = structlog.get_logger()


def pr_comment(
    repo: Annotated[str, cyclopts.Parameter(help="Repository name in format 'owner/repo'")],
    pr_number: Annotated[int, cyclopts.Parameter(help="Pull request number")],
    *,
    comment: Annotated[Optional[str], cyclopts.Parameter(help="Comment body text")] = None,
    file: Annotated[Optional[str], cyclopts.Parameter(help="File path for line comment")] = None,
    line: Annotated[Optional[int], cyclopts.Parameter(help="Line number for line comment")] = None,
    commit: Annotated[
        Optional[str], cyclopts.Parameter(help="Commit SHA (optional, uses latest if not provided)")
    ] = None,
    list_files: Annotated[bool, cyclopts.Parameter(help="List files changed in the PR")] = False,
    token: Annotated[Optional[str], cyclopts.Parameter(help="GitHub token (or use GITHUB_TOKEN env var)")] = None,
) -> None:
    """Submit comments on GitHub Pull Requests.

    Examples:
        # Create a line comment on a specific file
        github-monitor pr-comment owner/repo 123 --file src/main.py --line 42 --comment "This needs refactoring"

        # Create a general PR comment
        github-monitor pr-comment owner/repo 123 --comment "Looks good to me!"

        # List files changed in a PR
        github-monitor pr-comment owner/repo 123 --list-files

        # Specify a commit SHA for the line comment
        github-monitor pr-comment owner/repo 123 --file src/main.py --line 42 --comment "Fix this" --commit abc123

    Note: Make sure GITHUB_TOKEN is set in your environment or .env file, or pass via --token
    """
    try:
        # Authenticate once
        github_client = pr_comment_module.get_github_client(token)

        if list_files:
            files = pr_comment_module.list_pr_files(github_client, repo, pr_number)
            print(f"\nFiles changed in PR #{pr_number}:")
            for file_info in files:
                print(f"  {file_info['filename']}")
                print(f"    Status: {file_info['status']}")
                print(f"    Additions: +{file_info['additions']}, Deletions: -{file_info['deletions']}")
                print(f"    Changes: {file_info['changes']}")
                print()
        elif file and line and comment:
            # Create a line-specific comment
            comment_obj = pr_comment_module.create_pr_review_comment(
                github_client, repo, pr_number, file, line, comment, commit
            )
            print("✓ Comment created successfully!")
            print(f"  URL: {comment_obj.html_url}")
        elif comment:
            # Create a general comment
            comment_obj = pr_comment_module.create_pr_comment(github_client, repo, pr_number, comment)
            print("✓ Comment created successfully!")
            print(f"  URL: {comment_obj.html_url}")
        else:
            raise cyclopts.ValidationError(
                "Either provide --list-files, or --comment (with optional --file and --line)"
            )

    except Exception as e:
        logger.error("operation_failed", error=str(e))
        print(f"\n❌ Failed to complete operation: {e}")
        raise SystemExit(1) from e
