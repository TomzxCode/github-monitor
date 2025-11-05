# GitHub Monitor

Monitor GitHub issues, pull requests, and their comments through polling with `gh` CLI, and publish events to NATS JetStream for automated processing.

This tool's intent is to help manage and automate workflows around GitHub issues and PRs by integrating with Claude CLI for AI-driven automation.

You define a set of markdown templates that act as prompts for Claude CLI when specific events occur (e.g., new issue, updated PR, new comment).
You can then either have Claude automatically respond to issues/PRs or use it to generate summaries, labels, or other metadata.

## Overview

This tool provides a single command with three subcommands:

- **`github-monitor monitor`**: Polls GitHub repositories for issues, PRs, and comments, publishing events to NATS JetStream
- **`github-monitor event-handler`**: Consumes events from NATS and handles them (creates directories, invokes Claude CLI with templates, etc.)
- **`github-monitor pr-comment`**: Submit comments on GitHub Pull Requests (both general and line-specific review comments)

## Features

- Monitor multiple GitHub repositories for issues and pull requests
- Track comments on issues and PRs
- Publish events to NATS JetStream with retention policies
- Durable consumer support for reliable event processing
- Template-based event handling with Claude CLI integration
- Flexible monitoring modes (continuous or one-time)
- Dry-run mode for testing
- Filter issues/PRs by update timestamp

## Requirements

- Python 3.13+
- [gh CLI](https://cli.github.com/) (GitHub CLI)
- [NATS server](https://nats.io/) with JetStream enabled
- [Claude CLI](https://github.com/anthropics/anthropic-quickstarts) (optional, for event handling)

## Installation

```bash
# Using uv (recommended)
uv sync

# Install the package
uv pip install -e .
```

## Quick Start

### 1. Start NATS Server with JetStream

```bash
nats-server -js
```

### 2. Monitor Repositories

```bash
# Monitor specific repositories (runs once)
github-monitor monitor /path/to/data --repositories owner/repo1 owner/repo2

# Monitor with continuous polling every 5 minutes
github-monitor monitor /path/to/data --repositories owner/repo --interval 5m

# Monitor only issues/PRs updated since a specific time
github-monitor monitor /path/to/data --repositories owner/repo --updated-since 2024-01-01T00:00:00Z

# Dry run to see what would happen
github-monitor monitor /path/to/data --repositories owner/repo --dry-run
```

### 3. Handle Events

```bash
# Start the event handler
github-monitor event-handler /path/to/data

# With custom templates directory
github-monitor event-handler /path/to/data --templates-dir /path/to/templates

# Skip events from specific users
github-monitor event-handler /path/to/data --skip-users bot-user1 bot-user2
```

## Commands

### github-monitor monitor

Monitor GitHub repositories and publish events to NATS.

**Usage:**
```bash
github-monitor monitor PATH [OPTIONS]
```

**Options:**
- `--repositories`: List of repositories to track (format: `owner/repo`). If not provided, uses existing directories
- `--nats-server`: NATS server URL (default: `nats://localhost:4222`)
- `--dry-run`: Show what would be done without making changes
- `--updated-since`: Filter issues/PRs updated since ISO8601 timestamp
- `--monitor-issues`: Monitor and publish events for issues and PRs (default: true)
- `--monitor-issue-comments`: Monitor comments on issues (default: true)
- `--monitor-pr-comments`: Monitor comments on PRs (default: true)
- `--active-only`: Only monitor issues/PRs with `.active` flag (default: true)
- `--interval`: Run monitoring at this interval (format: `5m`, `1h30m`, `2d`). If not specified, runs once

**Examples:**
```bash
# Monitor two repositories every 10 minutes
github-monitor monitor ./data --repositories anthropics/claude anthropics/anthropic-sdk-python --interval 10m

# Monitor only new issues, not comments
github-monitor monitor ./data --repositories owner/repo --no-monitor-issue-comments --no-monitor-pr-comments

# Monitor all issues, not just active ones
github-monitor monitor ./data --repositories owner/repo --no-active-only
```

### github-monitor event-handler

Handle GitHub issue and PR events from NATS JetStream.

**Usage:**
```bash
github-monitor event-handler PATH [OPTIONS]
```

**Options:**
- `--templates-dir`: Templates directory containing markdown files for event handlers
- `--nats-server`: NATS server URL (default: `nats://localhost:4222`)
- `--stream`: JetStream stream name (default: `GITHUB_EVENTS`)
- `--consumer`: Durable consumer name (default: `github-event-handler`)
- `--batch-size`: Number of messages to fetch per batch (default: 10)
- `--fetch-timeout`: Timeout in seconds for fetching messages (default: 5.0)
- `--skip-users`: List of usernames to skip event handling for
- `--recreate-consumer`: Delete and recreate the consumer (useful for reprocessing all messages)
- `--claude-verbose`: Print raw Claude CLI output directly to stdout
- `--auto-confirm`: Automatically process events without confirmation (default: false)

**Examples:**
```bash
# Run with templates and auto-confirm
github-monitor event-handler ./data --templates-dir ./templates --auto-confirm

# Skip events from bots
github-monitor event-handler ./data --skip-users dependabot renovate-bot

# Reprocess all events from the beginning
github-monitor event-handler ./data --recreate-consumer
```

### github-monitor pr-comment

Submit comments on GitHub Pull Requests.

**Usage:**
```bash
github-monitor pr-comment REPO PR_NUMBER [OPTIONS]
```

**Options:**
- `--comment`: Comment body text
- `--file`: File path for line comment (relative to repository root)
- `--line`: Line number for line comment
- `--commit`: Commit SHA (optional, uses latest if not provided)
- `--list-files`: List files changed in the PR
- `--token`: GitHub token (or use GITHUB_TOKEN env var)

**Examples:**
```bash
# Create a line comment on a specific file
github-monitor pr-comment owner/repo 123 --file src/main.py --line 42 --comment "This needs refactoring"

# Create a general PR comment
github-monitor pr-comment owner/repo 123 --comment "Looks good to me!"

# List files changed in a PR
github-monitor pr-comment owner/repo 123 --list-files

# Specify a commit SHA for the line comment
github-monitor pr-comment owner/repo 123 --file src/main.py --line 42 --comment "Fix this" --commit abc123
```

**Note:** Make sure `GITHUB_TOKEN` is set in your environment or .env file, or pass via `--token`.

## Directory Structure

The tool organizes data in the following structure:

```
{base_path}/
└── {owner}/
    └── {repo}/
        └── {issue_or_pr_number}/
            ├── .active              # Marks issue/PR as actively tracked
            ├── .type                # "issue" or "pr"
            ├── .last_checked        # Last monitoring timestamp
            └── .last_comment_check  # Last comment check (for both issues and PRs)
```

## Event Types

The system publishes the following event types to NATS:

- `github.issue.new`: New open issue discovered
- `github.issue.updated`: Active issue has been updated
- `github.issue.closed`: Active issue has been closed
- `github.pr.new`: New open PR discovered
- `github.pr.updated`: Active PR has been updated
- `github.pr.closed`: Active PR has been closed
- `github.issue.comment.new`: New comment on an issue
- `github.pr.comment.new`: New comment on a PR

## Templates

Templates allow you to define custom behavior when events are received. The event handler looks for templates in the following hierarchy:

1. `{owner}/{repo}/{event_name}.md`
2. `{owner}/.default/{event_name}.md`
3. `.default/{event_name}.md`

**Template Variables:**

Templates have access to the following variables:
- `REPOSITORY`: Repository in `owner/repo` format
- `NUMBER`: Issue or PR number
- `BASE_DIR`: Base directory path

**Example Template** (`templates/.default/github.issue.new.md`):

```markdown
A new issue has been created in repository {{REPOSITORY}}.

Issue number: {{NUMBER}}
Base directory: {{BASE_DIR}}

Please review the issue and create a .active file if you want to track it.
```

**Skipping Events:**

To ignore specific events, create an empty template file. For example, to ignore new PR events for a specific repository:

```bash
touch templates/owner/repo/github.pr.new.md
```

## Development

### Setup

```bash
# Install with dev dependencies
uv sync
```

### Testing

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/github_monitor
```

### Linting/Formatting

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Fix linting issues
uv run ruff check --fix
```

## NATS JetStream Configuration

The system automatically creates a JetStream stream with the following configuration:

- **Stream Name**: `GITHUB_EVENTS`
- **Subjects**: `github.*`
- **Retention**: Limits-based (keeps messages for 7 days or up to 10k messages/100MB)
- **Consumer**: Durable consumer with explicit acknowledgment

## License

See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please ensure you:

1. Run tests before committing
2. Run linter/formatter before committing
3. Use type hints
4. Create "green path" tests that cover main functionality
