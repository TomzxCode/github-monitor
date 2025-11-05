# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Monitor is a Python-based system that monitors GitHub issues and pull requests through polling, then publishes events to NATS JetStream for processing. The system consists of two main components:

1. **Monitor** (`github-monitor`): Polls GitHub repositories for issues/PRs and publishes events to NATS
2. **Event Handler** (`github-event-handler`): Consumes events from NATS and invokes Claude CLI to process them

## Commands

### Development Setup
```bash
# Install dependencies (uv is used for package management)
uv sync

# Install dev dependencies
uv sync --group dev

# Run linter/formatter
uv run ruff check .
uv run ruff format .

# Run tests
uv run pytest
```

### Running the Application

```bash
# Monitor GitHub repositories (run once)
uv run github-monitor /path/to/data --repositories owner/repo

# Monitor with interval (e.g., every 5 minutes)
uv run github-monitor /path/to/data --repositories owner/repo --interval 5m

# Handle events from NATS
uv run github-event-handler /path/to/data --templates-dir /path/to/templates

# Dry run (see what would happen without making changes)
uv run github-monitor /path/to/data --repositories owner/repo --dry-run
```

### Testing Individual Components

```bash
# Run a single test file
uv run pytest tests/test_specific.py

# Run a specific test function
uv run pytest tests/test_specific.py::test_function_name

# Run with verbose output
uv run pytest -v
```

## Architecture

### Two-Component System

The system is designed as a producer-consumer pattern:

1. **Monitor (Producer)**: Polls GitHub using `gh` CLI and GraphQL queries, then publishes events to NATS JetStream
2. **Event Handler (Consumer)**: Listens to NATS events and invokes Claude CLI to process them using customizable templates

### Event Flow

```
GitHub API → Monitor → NATS JetStream → Event Handler → Claude CLI
```

### Directory Structure Convention

The system uses a hierarchical directory structure to track issues/PRs:

```
{base_path}/{owner}/{repo}/{issue_or_pr_number}/
├── .active          # Flag file indicating this issue/PR should be actively monitored
├── .type            # Contains "issue" or "pr" (cached to avoid API calls)
├── .last_checked    # ISO8601 timestamp of last monitoring check
└── .last_comment_check  # Last time comments were checked (unified for both issues and PRs)
```

### Event Types

The system publishes these events to NATS:

- `github.issue.new`: New open issue discovered
- `github.issue.updated`: Active issue has been updated
- `github.issue.closed`: Active issue has been closed
- `github.pr.new`: New open PR discovered
- `github.pr.updated`: Active PR has been updated
- `github.pr.closed`: Active PR has been closed
- `github.issue.comment.new`: New comment on an issue
- `github.pr.comment.new`: New comment on a PR

### Template System

Event handlers use markdown templates to define how Claude should process events. Templates are searched in this hierarchy:

1. `{templates_dir}/{owner}/{repo}/{event_name}.md`
2. `{templates_dir}/{owner}/.default/{event_name}.md`
3. `{templates_dir}/.default/{event_name}.md`

Templates receive these variables:
- `REPOSITORY`: Repository in "owner/repo" format
- `NUMBER`: Issue/PR number
- `BASE_DIR`: Base directory path

An empty template file is used to skip processing for specific events.

### Dependencies

Required CLI tools:
- `gh` (GitHub CLI): Used for API calls
- `claude` (optional): Used by event handler to process events

Required Python packages:
- `nats-py`: NATS JetStream client
- `cyclopts`: CLI framework

### GraphQL Query Strategy

The monitor uses GitHub's GraphQL API for efficient data fetching:

- Fetches up to 100 items per page with automatic pagination
- Uses `filterBy: {since: timestamp}` to only fetch recently updated items
- Batches comment fetching at the repository level for efficiency
- Caches item types (issue vs PR) in `.type` files to reduce API calls

### Comment Monitoring Optimization

To minimize API calls, comment monitoring:
1. Finds the earliest last-check timestamp across all issues/PRs in a repository
2. Fetches all comments updated since that time with a single query
3. Filters results per issue/PR based on individual last-check timestamps
4. Updates last-check timestamps after processing

### NATS JetStream Configuration

Stream configuration (`GITHUB_EVENTS`):
- Retention: 7 days
- Max messages: 10,000
- Max size: 100MB
- Discard policy: Old messages when limits reached

Consumer configuration:
- Durable consumer for resumability
- Explicit acknowledgment
- DeliverPolicy.ALL for new consumers (processes all retained messages)

# MUST DO

* Always update CLAUDE.md
* Always update README.md
* Always run tests after changes are done
* Always run linter/formatter after changes are done
