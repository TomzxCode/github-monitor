# GitHub GraphQL Client Specification

## Overview

The GitHub GraphQL Client provides a shared interface for making authenticated GraphQL requests to the GitHub API. It handles authentication, request execution, error handling, and maintains a global client instance for reuse across the application.

## Requirements

### Core Functionality

#### 1. Client Initialization
- The system MUST initialize the client with a GitHub personal access token
- The system MUST obtain the token from:
  1. The `token` parameter passed to `__init__()`
  2. The `GITHUB_TOKEN` environment variable (if no token parameter is provided)
- The system MUST raise a `ValueError` if no token is available
- The system MUST load environment variables from `.env` file using python-dotenv

#### 2. Request Execution
- The system MUST execute GraphQL queries via HTTP POST to `https://api.github.com/graphql`
- The system MUST include the following headers:
  - `Authorization: Bearer {token}`
  - `Content-Type: application/json`
- The system MUST set a 30-second timeout for all requests
- The system MUST support both queries and mutations

#### 3. Request Payload
- The system MUST send requests with JSON content type
- The system MUST include the `query` field containing the GraphQL query string
- The system MUST include the `variables` field if variables are provided (optional)

#### 4. Response Handling
- The system MUST return the full response data dictionary
- The system MUST check for GraphQL errors in the response
- The system MUST raise a `ValueError` if the response contains GraphQL errors
- The system MUST include all error messages in the exception

#### 5. HTTP Error Handling
- The system MUST raise `requests.HTTPError` for HTTP errors (4xx, 5xx)
- The system MUST use `response.raise_for_status()` to detect HTTP errors
- The system MUST log GraphQL execution errors to stderr
- The system MUST handle `requests.RequestException` and propagate

#### 6. Global Client Instance
- The system MUST maintain a global client instance (`_github_client`)
- The system MUST initialize the global client on first use
- The system MUST support re-initializing the global client when a new token is provided
- The system MUST provide a `get_github_client()` function to access the global instance

### API Reference

#### `GitHubGraphQLClient` Class

```python
class GitHubGraphQLClient:
    def __init__(self, token: str | None = None)
    def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]
```

#### `get_github_client()` Function

```python
def get_github_client(token: str | None = None) -> GitHubGraphQLClient
```

### Error Messages

#### Missing Token

```
"GitHub token is required. Set GITHUB_TOKEN environment variable or pass token parameter."
```

#### GraphQL Errors

```
"GraphQL errors: {error_message_1}, {error_message_2}, ..."
```

#### Execution Error

```
"Error executing GraphQL query: {exception_details}"
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub personal access token for API authentication |

### Dependencies

- `requests` - HTTP client for making API requests
- `python-dotenv` - Loading environment variables from `.env` file
