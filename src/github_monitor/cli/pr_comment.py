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
    submit: Annotated[
        Optional[str], cyclopts.Parameter(help="Submit a review with event: approve, request_changes, or comment")
    ] = None,
) -> None:
    """Submit comments on GitHub Pull Requests.

    Examples:
        # Create a line comment on a specific file
        github-monitor pr-comment owner/repo 123 --file src/main.py --line 42 --comment "This needs refactoring"

        # Create a general PR comment
        github-monitor pr-comment owner/repo 123 --comment "Looks good to me!"

        # Submit a review with approval on a line
        github-monitor pr-comment owner/repo 123 --file src/main.py --line 42 --comment "LGTM" --submit approve

        # Submit a review requesting changes on a line
        github-monitor pr-comment owner/repo 123 --file src/main.py --line 42 --comment "Please fix" \\
            --submit request_changes

    Note: Make sure GITHUB_TOKEN is set in your environment or .env file, or pass via --token
    """
    try:
        # Authenticate once
        github_client = pr_comment_module.get_github_token(token)

        if file and line and comment:
            # Validate and convert submit event if provided
            event = None  # Default to None (pending review)
            if submit:
                event_map = {
                    "approve": "APPROVE",
                    "request_changes": "REQUEST_CHANGES",
                    "comment": "COMMENT",
                }

                submit_lower = submit.lower()
                if submit_lower not in event_map:
                    raise cyclopts.ValidationError(
                        f"Invalid --submit value: {submit}. Must be one of: approve, request_changes, comment"
                    )

                event = event_map[submit_lower]

            # Create a line-specific comment (and optionally submit as review)
            result_obj = pr_comment_module.create_pr_review_comment(
                github_client, repo, pr_number, file, line, comment, event
            )

            if event:
                print("✓ Review submitted successfully!")
                print(f"  State: {result_obj['state']}")
            else:
                print("✓ Review comment created (pending)!")
            print(f"  URL: {result_obj['html_url']}")
        elif comment:
            # Create a general comment
            if submit:
                raise cyclopts.ValidationError("--submit requires --file and --line to create a review comment")

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
