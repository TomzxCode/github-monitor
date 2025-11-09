"""CLI command for submitting comments on GitHub Pull Requests."""

from pathlib import Path
from typing import Annotated

import cyclopts
import structlog

from github_monitor import pr_comment as pr_comment_module
from github_monitor.cli.config_loader import load_config, merge_config_with_defaults


logger = structlog.get_logger()


def pr_comment(
    repo: Annotated[str | None, cyclopts.Parameter(help="Repository name in format 'owner/repo'")] = None,
    pr_number: Annotated[int | None, cyclopts.Parameter(help="Pull request number")] = None,
    *,
    comment: Annotated[str | None, cyclopts.Parameter(help="Comment body text")] = None,
    file: Annotated[str | None, cyclopts.Parameter(help="File path for line comment")] = None,
    line: Annotated[int | None, cyclopts.Parameter(help="Line number for line comment")] = None,
    token: Annotated[str | None, cyclopts.Parameter(help="GitHub token (or use GITHUB_TOKEN env var)")] = None,
    submit: Annotated[
        str | None, cyclopts.Parameter(help="Submit a review with event: approve, request_changes, or comment")
    ] = None,
    config: Annotated[
        Path | None, cyclopts.Parameter(help="Path to YAML configuration file. CLI arguments override config file values.")
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

        # Use a configuration file
        github-monitor pr-comment --config config-pr-comment.yaml

    Note: Make sure GITHUB_TOKEN is set in your environment or .env file, or pass via --token
    """
    # Load configuration from file if provided
    if config:
        file_config = load_config(config)
    else:
        file_config = {}

    # Merge with CLI arguments (CLI takes precedence)
    cli_values = {
        "repo": repo,
        "pr_number": pr_number,
        "comment": comment,
        "file": file,
        "line": line,
        "token": token,
        "submit": submit,
    }
    merged_config = merge_config_with_defaults(file_config, cli_values)

    # Extract final values
    final_repo = merged_config.get("repo")
    final_pr_number = merged_config.get("pr_number")
    final_comment = merged_config.get("comment")
    final_file = merged_config.get("file")
    final_line = merged_config.get("line")
    final_token = merged_config.get("token")
    final_submit = merged_config.get("submit")

    # Validate required fields
    if not final_repo:
        raise cyclopts.ValidationError("Repository (repo) is required (via --repo or in config file)")
    if not final_pr_number:
        raise cyclopts.ValidationError("Pull request number (pr_number) is required (via pr_number argument or in config file)")

    try:
        # Authenticate once
        github_client = pr_comment_module.get_github_token(final_token)

        if final_file and final_line and final_comment:
            # Validate and convert submit event if provided
            event = None  # Default to None (pending review)
            if final_submit:
                event_map = {
                    "approve": "APPROVE",
                    "request_changes": "REQUEST_CHANGES",
                    "comment": "COMMENT",
                }

                submit_lower = final_submit.lower()
                if submit_lower not in event_map:
                    raise cyclopts.ValidationError(
                        f"Invalid --submit value: {final_submit}. Must be one of: approve, request_changes, comment"
                    )

                event = event_map[submit_lower]

            # Create a line-specific comment (and optionally submit as review)
            result_obj = pr_comment_module.create_pr_review_comment(
                github_client, final_repo, final_pr_number, final_file, final_line, final_comment, event
            )

            if event:
                print("✓ Review submitted successfully!")
                print(f"  State: {result_obj['state']}")
            else:
                print("✓ Review comment created (pending)!")
            print(f"  URL: {result_obj['html_url']}")
        elif final_comment:
            # Create a general comment
            if final_submit:
                raise cyclopts.ValidationError("--submit requires --file and --line to create a review comment")

            comment_obj = pr_comment_module.create_pr_comment(github_client, final_repo, final_pr_number, final_comment)
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
