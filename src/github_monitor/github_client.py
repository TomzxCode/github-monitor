"""Shared GitHub GraphQL API client."""

import os
import sys
from typing import Any

import requests
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class GitHubGraphQLClient:
    """Client for making GraphQL requests to GitHub API."""

    def __init__(self, token: str | None = None):
        """
        Initialize the GitHub GraphQL client.

        Args:
            token: GitHub personal access token. If not provided, will try to get from GITHUB_TOKEN env var.

        Raises:
            ValueError: If no token is provided and GITHUB_TOKEN env var is not set.
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN environment variable or pass token parameter.")

        self.api_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Optional variables for the GraphQL query

        Returns:
            Response data dictionary

        Raises:
            requests.HTTPError: If the request fails
            ValueError: If the response contains errors
        """
        try:
            payload: dict[str, Any] = {"query": query}
            if variables:
                payload["variables"] = variables

            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            # Check for GraphQL errors
            if "errors" in data:
                error_messages = [e.get("message", str(e)) for e in data["errors"]]
                raise ValueError(f"GraphQL errors: {', '.join(error_messages)}")

            return data

        except requests.RequestException as e:
            print(f"Error executing GraphQL query: {e}", file=sys.stderr)
            raise


# Global client instance (will be initialized on first use)
_github_client: GitHubGraphQLClient | None = None


def get_github_client(token: str | None = None) -> GitHubGraphQLClient:
    """
    Get or create the global GitHub GraphQL client instance.

    Args:
        token: Optional GitHub token. If not provided, uses GITHUB_TOKEN env var.

    Returns:
        GitHubGraphQLClient instance
    """
    global _github_client
    if _github_client is None or token is not None:
        _github_client = GitHubGraphQLClient(token)
    return _github_client
