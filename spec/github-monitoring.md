# GitHub Monitoring Specification

## Overview

The GitHub Monitoring component is responsible for polling GitHub repositories for issues and pull requests using the GraphQL API, detecting changes, and publishing events to NATS JetStream for downstream processing.

## Requirements

### Core Functionality

#### 1. Repository Discovery
- The system MUST scan the base directory structure `{base_path}/{owner}/{repo}/` to identify tracked repositories
- The system MUST support filtering repositories via command-line arguments
- The system MUST support both manual repository specification and automatic discovery

#### 2. Issue and Pull Request Polling
- The system MUST use GitHub GraphQL API for all data fetching
- The system MUST support fetching issues and pull requests with pagination (up to 100 items per page)
- The system MUST support filtering by `updated_since` timestamp using `filterBy: {since: timestamp}` clause
- The system MUST fetch the following fields for each issue/PR:
  - `number`, `title`, `body`, `url`, `state`
  - `createdAt`, `updatedAt`, `closedAt`/`mergedAt`
  - `author` (login)
  - `assignees` (list of logins)
  - `labels` (list of names)
- The system MUST additionally fetch for PRs: `isDraft`, `mergeable`, `reviewDecision`

#### 3. Active Issue/PR Tracking
- The system MUST scan for `.active` files in `{base_path}/{owner}/{repo}/{number}/.active` to determine tracked items
- The system MUST only process issues/PRs that have an `.active` file
- The system MUST maintain `.last_checked` timestamp files to track last monitoring time
- The system MUST cache item type (issue vs PR) in `.type` files to avoid redundant API calls

#### 4. Event Publishing
- The system MUST publish the following events to NATS JetStream:
  - `github.issue.new` - When a new open issue is discovered
  - `github.issue.updated` - When an active tracked issue has been updated
  - `github.issue.closed` - When an active tracked issue has been closed
  - `github.pr.new` - When a new open PR is discovered
  - `github.pr.updated` - When an active tracked PR has been updated
  - `github.pr.closed` - When an active tracked PR has been closed
- The system MUST include repository, number, and all GraphQL data in event payloads
- The system MUST update timestamps after successful event publishing

#### 5. Comment Monitoring
- The system MUST monitor comments on both issues and pull requests
- The system MUST publish `github.issue.comment.new` events for new issue comments
- The system MUST publish `github.pr.comment.new` events for new PR comments
- The system SHOULD batch comment fetching at the repository level to minimize API calls
- The system MUST use the earliest last-check timestamp across all items in a repository for filtering
- The system MUST maintain `.last_comment_check` timestamp files per issue/PR
- The system MUST include full comment data (author, body, timestamps, reactions) in events

### Error Handling

- The system MUST log errors to stderr without exiting for non-fatal errors
- The system MUST continue processing other repositories/items if one fails
- The system MUST handle GraphQL errors gracefully and report them
- The system MUST handle HTTP request errors and retry where appropriate

### Dry Run Mode

- The system MUST support a `--dry-run` flag that previews actions without making changes
- In dry run mode, the system MUST NOT publish events to NATS
- In dry run mode, the system MUST NOT write timestamp files
- In dry run mode, the system MUST print what actions would be taken

### Directory Structure

The system MUST use the following directory structure:

```
{base_path}/{owner}/{repo}/{issue_or_pr_number}/
├── .active          # Flag file indicating this issue/PR should be actively monitored
├── .type            # Contains "issue" or "pr" (cached to avoid API calls)
├── .last_checked    # ISO8601 timestamp of last monitoring check
└── .last_comment_check  # Last time comments were checked
```

### NATS JetStream Integration

- The system MUST ensure the `GITHUB_EVENTS` stream exists before publishing
- The system MUST create the stream with the following configuration if it does not exist:
  - Retention: 7 days (`max_age`)
  - Max messages: 10,000 (`max_msgs`)
  - Max size: 100MB (`max_bytes`)
  - Discard policy: OLD (`DiscardPolicy.OLD`)
  - Subjects: `github.>` (wildcard for all github.* subjects)
- The system MUST use JSON encoding for all event messages

### Performance Considerations

- The system SHOULD use pagination to fetch large numbers of items
- The system SHOULD batch comment fetching at the repository level when possible
- The system MUST cache the type (issue/PR) in `.type` files to avoid API calls
- The system MUST respect GitHub GraphQL rate limits (default timeout: 30 seconds per request)

## Data Structures

### Issue/PR Event Data

```json
{
  "type": "issue" | "pr",
  "number": int,
  "title": string,
  "body": string | null,
  "url": string,
  "state": string,
  "created_at": string (ISO8601),
  "updated_at": string (ISO8601),
  "closed_at": string | null,
  "author": string,
  "assignees": [string],
  "labels": [string],
  "merged_at": string | null,  // PRs only
  "is_draft": boolean,          // PRs only
  "mergeable": string | null,   // PRs only
  "review_decision": string | null  // PRs only
}
```

### Comment Event Data

```json
{
  "id": string,
  "database_id": int,
  "url": string,
  "author": string,
  "author_association": string,
  "body": string,
  "body_text": string,
  "created_at": string (ISO8601),
  "updated_at": string (ISO8601),
  "published_at": string (ISO8601),
  "last_edited_at": string | null,
  "is_minimized": boolean,
  "minimized_reason": string | null,
  "reactions": {
    "total_count": int,
    "items": [
      {
        "content": string,
        "user": string
      }
    ]
  }
}
```
