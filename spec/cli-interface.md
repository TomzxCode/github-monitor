# CLI Interface Specification

## Overview

The CLI Interface provides command-line access to all GitHub Monitor functionality using the cyclopts framework. It supports three main commands: `monitor`, `event-handler`, and `pr-comment`, each with comprehensive configuration options via YAML files and CLI arguments.

## Requirements

### Core Framework

- The system MUST use cyclopts for command-line argument parsing
- The system MUST support three top-level commands: `monitor`, `event-handler`, `pr-comment`
- The system MUST load configuration from YAML files when specified
- The system MUST merge configuration files with CLI arguments (CLI arguments take precedence)
- The system MUST support loading environment variables from `.env` files

### Common Features

#### Configuration File Support
- All commands MUST support `--config` parameter for YAML configuration files
- The system MUST validate YAML files exist and are readable
- The system MUST parse YAML as a dictionary (not a list or scalar)
- The system MUST report clear errors for malformed YAML

#### Duration Parsing
- The system MUST support duration strings in format `AdBhCmDs` (days, hours, minutes, seconds)
- Examples: `5m`, `1h30m`, `2d`, `300s`, `1h`
- The system MUST convert duration strings to `timedelta` objects
- The system MUST support both string (from config) and `timedelta` (from CLI) types

### Monitor Command (`github-monitor monitor`)

#### Required Parameters
- `--path` (Path): Base path containing repository/issue_number directories

#### Optional Parameters
- `--repositories` (list[str]): List of repositories to track (format: owner/repo). If not provided, uses existing directories
- `--nats-server` (str): NATS server URL (default: `nats://localhost:4222`)
- `--dry-run` (bool): Show what would be done without making changes (default: False)
- `--updated-since` (str): Filter issues/PRs updated since this ISO8601 timestamp
- `--monitor-issues` (bool): Monitor and publish events for issues and PRs (default: True)
- `--monitor-issue-comments` (bool): Monitor and publish events for new comments on active issues (default: True)
- `--monitor-pr-comments` (bool): Monitor and publish events for new comments on active pull requests (default: True)
- `--active-only` (bool): Only monitor issues/PRs with .active flag (default: True)
- `--interval` (duration): Run monitoring at this interval. If not specified, runs once and exits

#### Behavior
- The system MUST validate that `GITHUB_TOKEN` is available before starting
- The system MUST exit with code 130 on SIGINT (Ctrl+C)
- The system MUST support graceful shutdown on keyboard interrupt
- The system MUST connect to NATS unless in dry-run mode
- The system MUST ensure JetStream stream exists before publishing
- When `--interval` is specified, the system MUST:
  - Run monitoring cycles continuously
  - Calculate sleep duration to maintain fixed interval
  - Start next cycle immediately if the cycle took longer than the interval
  - Display cycle count and timing information
- The system MUST separate issues from PRs using cached type information
- The system MUST display progress messages for each monitoring phase

### Event Handler Command (`github-monitor event-handler`)

#### Required Parameters
- `--path` (Path): Base path containing repository/issue_number directories

#### Optional Parameters
- `--templates-dir` (Path): Templates directory containing markdown files for event handlers
- `--nats-server` (str): NATS server URL (default: `nats://localhost:4222`)
- `--stream` (str): JetStream stream name (default: `GITHUB_EVENTS`)
- `--consumer` (str): Durable consumer name (default: `github-event-handler`)
- `--batch-size` (int): Number of messages to fetch per batch (default: 10)
- `--fetch-timeout` (duration): Timeout for fetching messages (default: 5 seconds)
- `--ack-wait` (duration): AckWait timeout for message processing (default: 300 seconds)
- `--skip-users` (str): Regex pattern to match usernames to skip event handling for
- `--repositories` (str): Regex pattern to filter repositories (only matching repositories will be processed)
- `--recreate-consumer` (bool): Delete and recreate the consumer (useful for reprocessing all messages)
- `--claude-verbose` (bool): Print raw Claude CLI output directly to stdout instead of parsing JSONL
- `--auto-confirm` (bool): Automatically process events without confirmation (default: False)

#### Behavior
- The system MUST check if Claude CLI is installed and warn if not available
- The system MUST create a durable consumer with `DeliverPolicy.ALL` if it doesn't exist
- The system MUST display pending message count when consumer exists
- The system MUST support recreating the consumer via `--recreate-consumer`
- The system MUST subscribe to all GitHub events (`github.*`) via pull subscription
- The system MUST fetch messages in batches
- The system MUST handle `TimeoutError` gracefully (no messages available)
- The system MUST pause briefly on fetch errors before retrying
- The system MUST exit with code 0 on keyboard interrupt

### PR Comment Command (`github-monitor pr-comment`)

#### Required Parameters
- `repo` (str): Repository name in format 'owner/repo'
- `pr-number` (int): Pull request number

#### Optional Parameters
- `--comment` (str): Comment body text
- `--file` (str): File path for line comment
- `--line` (int): Line number for line comment
- `--token` (str): GitHub token (or use GITHUB_TOKEN env var)
- `--submit` (str): Submit a review with event: `approve`, `request_changes`, or `comment`

#### Behavior
- The system MUST require `--comment` to be provided
- If `--file` and `--line` are provided with `--comment`, the system MUST create a line-specific review comment
- If only `--comment` is provided, the system MUST create a general PR comment
- If `--submit` is provided without `--file` and `--line`, the system MUST raise a validation error
- The system MUST validate `--submit` values against allowed options
- The system MUST convert submit values to uppercase event constants (`APPROVE`, `REQUEST_CHANGES`, `COMMENT`)
- The system MUST print success messages with URLs after creating comments
- The system MUST exit with code 1 on validation or operation errors
- The system MUST log operation failures with structlog

### Error Handling

- The system MUST raise `cyclopts.ValidationError` for invalid input
- The system MUST print validation errors to stderr
- The system MUST exit with appropriate status codes:
  - 0 for success
  - 1 for errors
  - 130 for SIGINT (monitor command only)

### Logging Output

- The system MUST print connection status messages
- The system MUST print consumer creation/reuse information
- The system MUST print cycle timing information (monitor command with interval)
- The system MUST print success/failure messages for operations
- The system MUST print warnings for missing optional components (e.g., Claude CLI)

## Configuration File Format

### Example Monitor Configuration

```yaml
path: /data/github
repositories:
  - owner/repo1
  - owner/repo2
nats_server: nats://localhost:4222
dry_run: false
monitor_issues: true
monitor_issue_comments: true
monitor_pr_comments: true
active_only: true
interval: 5m
```

### Example Event Handler Configuration

```yaml
path: /data/github
templates_dir: /templates
nats_server: nats://localhost:4222
stream: GITHUB_EVENTS
consumer: github-event-handler
batch_size: 10
fetch_timeout: 5s
ack_wait: 5m
skip_users: "bot|automation"
repositories: "owner/.*"
auto_confirm: true
claude_verbose: false
```

### Example PR Comment Configuration

```yaml
repo: owner/repo
pr_number: 123
comment: "This needs refactoring"
file: src/main.py
line: 42
submit: approve
```
