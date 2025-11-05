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
    token: Annotated[Optional[str], cyclopts.Parameter(help="GitHub token (or use GITHUB_TOKEN env var)")] = None,
) -> None:
    """Submit comments on GitHub Pull Requests.

    Examples:
        # Create a line comment on a specific file
        github-monitor pr-comment owner/repo 123 --file src/main.py --line 42 --comment "This needs refactoring"

        # Create a general PR comment
        github-monitor pr-comment owner/repo 123 --comment "Looks good to me!"

    Note: Make sure GITHUB_TOKEN is set in your environment or .env file, or pass via --token
    """
    try:
        # Authenticate once
        github_client = pr_comment_module.get_github_token(token)

        if file and line and comment:
            # Create a line-specific comment
            comment_obj = pr_comment_module.create_pr_review_comment(
                github_client, repo, pr_number, file, line, comment
            )
            print("✓ Comment created successfully!")
            print(f"  URL: {comment_obj['html_url']}")
        elif comment:
            # Create a general comment
            comment_obj = pr_comment_module.create_pr_comment(github_client, repo, pr_number, comment)
            print("✓ Comment created successfully!")
            print(f"  URL: {comment_obj['html_url']}")
        else:
            raise cyclopts.ValidationError("Please provide --comment (with optional --file and --line)")

    except cyclopts.ValidationError as e:
        raise SystemExit(1) from e
    except Exception as e:
        logger.error("operation_failed", error=str(e))
        print(f"\n❌ Failed to complete operation: {e}")
        raise SystemExit(1) from e
