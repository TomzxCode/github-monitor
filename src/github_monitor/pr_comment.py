"""Submit comments on GitHub Pull Requests at specific lines in files.

This module uses the GitHub GraphQL API to interact with GitHub.
It can create both general PR comments and line-specific review comments.
"""

from typing import Any

import structlog

from github_monitor.github_client import get_github_client


logger = structlog.get_logger()


def get_github_token(token: str | None = None) -> str:
    """Get and validate a GitHub token.

    Args:
        token: GitHub token. If not provided, uses get_github_client which loads from GITHUB_TOKEN env var.

    Returns:
        GitHub authentication token

    Raises:
        ValueError: If no token is provided and GITHUB_TOKEN is not set
    """
    if token:
        return token

    # Use the shared client to get/validate token
    client = get_github_client(token)
    if not client.token:
        raise ValueError("GitHub token is required")
    return client.token


def create_pr_review_comment(
    github_client: str,
    repo_name: str,
    pr_number: int,
    file_path: str,
    line_number: int,
    comment_body: str,
) -> dict[str, Any]:
    """Create a review comment on a specific line of a file in a PR.

    Args:
        github_client: GitHub authentication token
        repo_name: Repository name in format "owner/repo"
        pr_number: Pull request number
        file_path: Path to the file relative to repository root
        line_number: Line number to comment on
        comment_body: The comment text

    Returns:
        Dictionary containing comment information including html_url

    Raises:
        Exception: If the GitHub API returns an error
    """
    try:
        owner, repo = repo_name.split("/")
        client = get_github_client(github_client)

        # Get the Pull Request node ID for the mutation
        pr_id_query = """
        query($owner: String!, $repo: String!, $prNumber: Int!) {
            repository(owner: $owner, name: $repo) {
                pullRequest(number: $prNumber) {
                    id
                }
            }
        }
        """
        pr_id_response = client.execute(
            pr_id_query,
            {"owner": owner, "repo": repo, "prNumber": pr_number},
        )
        pull_request_id = pr_id_response["data"]["repository"]["pullRequest"]["id"]

        # Create the review comment using GraphQL mutation
        mutation = """
        mutation($input: AddPullRequestReviewThreadInput!) {
            addPullRequestReviewThread(input: $input) {
                thread {
                    comments(first: 1) {
                        nodes {
                            id
                            url
                            body
                        }
                    }
                }
            }
        }
        """

        variables = {
            "input": {
                "pullRequestId": pull_request_id,
                "body": comment_body,
                "path": file_path,
                "line": line_number,
            }
        }

        result = client.execute(mutation, variables)
        comment = result["data"]["addPullRequestReviewThread"]["thread"]["comments"]["nodes"][0]

        # Convert to expected format
        comment_obj = {"html_url": comment["url"], "id": comment["id"], "body": comment["body"]}

        logger.info("comment_created", url=comment_obj["html_url"])
        return comment_obj

    except Exception as e:
        logger.error("github_api_error", error=str(e))
        raise


def create_pr_comment(
    github_client: str,
    repo_name: str,
    pr_number: int,
    comment_body: str,
) -> dict[str, Any]:
    """Create a general comment on a PR (not tied to a specific line).

    Args:
        github_client: GitHub authentication token
        repo_name: Repository name in format "owner/repo"
        pr_number: Pull request number
        comment_body: The comment text

    Returns:
        Dictionary containing comment information including html_url

    Raises:
        Exception: If the GitHub API returns an error
    """
    try:
        owner, repo = repo_name.split("/")
        client = get_github_client(github_client)

        # Get the Pull Request node ID
        pr_id_query = """
        query($owner: String!, $repo: String!, $prNumber: Int!) {
            repository(owner: $owner, name: $repo) {
                pullRequest(number: $prNumber) {
                    id
                }
            }
        }
        """
        pr_id_response = client.execute(
            pr_id_query,
            {"owner": owner, "repo": repo, "prNumber": pr_number},
        )
        subject_id = pr_id_response["data"]["repository"]["pullRequest"]["id"]

        # Create a comment using GraphQL mutation
        mutation = """
        mutation($input: AddCommentInput!) {
            addComment(input: $input) {
                commentEdge {
                    node {
                        id
                        url
                        body
                    }
                }
            }
        }
        """

        variables = {"input": {"subjectId": subject_id, "body": comment_body}}

        result = client.execute(mutation, variables)
        comment = result["data"]["addComment"]["commentEdge"]["node"]

        # Convert to expected format
        comment_obj = {"html_url": comment["url"], "id": comment["id"], "body": comment["body"]}

        logger.info("comment_created", url=comment_obj["html_url"])
        return comment_obj

    except Exception as e:
        logger.error("github_api_error", error=str(e))
        raise
