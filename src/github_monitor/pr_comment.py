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
    event: str | None = None,
) -> dict[str, Any]:
    """Create a review comment on a specific line of a file in a PR, optionally submitting it as a review.

    Args:
        github_client: GitHub authentication token
        repo_name: Repository name in format "owner/repo"
        pr_number: Pull request number
        file_path: Path to the file relative to repository root
        line_number: Line number to comment on
        comment_body: The comment text
        event: Optional review event to perform (APPROVE, REQUEST_CHANGES, COMMENT).
               If None, creates a pending review without submitting.

    Returns:
        Dictionary containing review or thread information including html_url

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

        # Create a pending review with a comment thread
        create_review_mutation = """
        mutation($input: AddPullRequestReviewThreadInput!) {
            addPullRequestReviewThread(input: $input) {
                thread {
                    id
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

        create_variables = {
            "input": {
                "pullRequestId": pull_request_id,
                "path": file_path,
                "body": comment_body,
                "line": line_number,
            }
        }

        create_result = client.execute(create_review_mutation, create_variables)
        thread = create_result["data"]["addPullRequestReviewThread"]["thread"]
        comment = thread["comments"]["nodes"][0]

        # If no event is specified, return the pending comment without submitting
        if event is None:
            comment_obj = {
                "html_url": comment["url"],
                "id": comment["id"],
                "body": comment["body"],
                "state": "PENDING",
            }
            logger.info("review_thread_created", url=comment_obj["html_url"])
            return comment_obj

        # If event is specified, get the pending review and submit it
        get_pending_review_query = """
        query($owner: String!, $repo: String!, $prNumber: Int!) {
            repository(owner: $owner, name: $repo) {
                pullRequest(number: $prNumber) {
                    reviews(last: 1, states: [PENDING]) {
                        nodes {
                            id
                        }
                    }
                }
            }
        }
        """

        pending_review_response = client.execute(
            get_pending_review_query,
            {"owner": owner, "repo": repo, "prNumber": pr_number},
        )

        reviews = pending_review_response["data"]["repository"]["pullRequest"]["reviews"]["nodes"]
        if not reviews:
            raise Exception("No pending review found after creating review thread")

        review_id = reviews[0]["id"]

        # Submit the review using submitPullRequestReview mutation
        submit_mutation = """
        mutation($input: SubmitPullRequestReviewInput!) {
            submitPullRequestReview(input: $input) {
                pullRequestReview {
                    id
                    url
                    state
                    body
                }
            }
        }
        """

        submit_variables = {
            "input": {
                "pullRequestReviewId": review_id,
                "event": event,
            }
        }

        submit_result = client.execute(submit_mutation, submit_variables)
        review = submit_result["data"]["submitPullRequestReview"]["pullRequestReview"]

        # Convert to expected format
        review_obj = {
            "html_url": review["url"],
            "id": review["id"],
            "state": review["state"],
            "body": review.get("body", ""),
        }

        logger.info("review_created", url=review_obj["html_url"], state=review_obj["state"])
        return review_obj

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
