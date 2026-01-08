# PR Comment System Specification

## Overview

The PR Comment System provides functionality for creating comments on GitHub pull requests. It supports both general PR comments and line-specific review comments using the GitHub GraphQL API.

## Requirements

### Core Functionality

#### 1. General PR Comments
- The system MUST support creating general comments on pull requests
- The system MUST accept the following parameters:
  - `repo_name` - Repository name in "owner/repo" format
  - `pr_number` - Pull request number
  - `comment_body` - The comment text
- The system MUST use the `addComment` GraphQL mutation
- The system MUST return the comment URL, ID, and body after creation

#### 2. Line-Specific Review Comments
- The system MUST support creating review comments on specific lines of files
- The system MUST accept the following parameters:
  - `repo_name` - Repository name in "owner/repo" format
  - `pr_number` - Pull request number
  - `file_path` - Path to the file relative to repository root
  - `line_number` - Line number to comment on
  - `comment_body` - The comment text
- The system MUST use the `addPullRequestReviewThread` GraphQL mutation
- The system MUST return the comment URL, ID, body, and state after creation

#### 3. Review Submission
- The system MUST support submitting review comments with a review event
- The system MUST support the following review events:
  - `APPROVE` - Submit the review with approval
  - `REQUEST_CHANGES` - Submit the review requesting changes
  - `COMMENT` - Submit the review as a general comment
- The system MUST create a pending review when no event is specified
- The system MUST use the `submitPullRequestReview` mutation to submit reviews
- The system MUST retrieve the pending review ID before submitting

#### 4. Authentication
- The system MUST use the shared GitHub GraphQL client for authentication
- The system MUST obtain the GitHub token from the `GITHUB_TOKEN` environment variable or via parameter
- The system MUST validate that a token is available before making API calls

### Return Values

#### General Comment Response

```json
{
  "html_url": string,
  "id": string,
  "body": string
}
```

#### Review Comment Response (Pending)

```json
{
  "html_url": string,
  "id": string,
  "body": string,
  "state": "PENDING"
}
```

#### Review Comment Response (Submitted)

```json
{
  "html_url": string,
  "id": string,
  "body": string,
  "state": "APPROVED" | "CHANGES_REQUESTED" | "COMMENTED"
}
```

### Error Handling

- The system MUST raise exceptions when GitHub API returns errors
- The system MUST log errors using structlog
- The system MUST include relevant error context (e.g., repository, PR number)
- The system MUST handle missing or invalid repository format gracefully

### GraphQL Operations

#### Query: Get PR Node ID

```graphql
query($owner: String!, $repo: String!, $prNumber: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $prNumber) {
      id
    }
  }
}
```

#### Mutation: Add Pull Request Review Thread

```graphql
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
```

#### Mutation: Add Comment

```graphql
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
```

#### Mutation: Submit Pull Request Review

```graphql
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
```

### Logging

- The system MUST log successful comment creation with `comment_created` event
- The system MUST log successful review creation with `review_created` event
- The system MUST log successful review thread creation with `review_thread_created` event
- The system MUST log errors with `github_api_error` event
- All log entries MUST include relevant context (url, state, error details)
