# YAML Configuration Files

The `github-monitor` CLI supports YAML configuration files for all commands. This allows you to store commonly used options in a file instead of passing them as command-line arguments every time.

## Benefits

- **Easier to use**: Store complex configurations once and reuse them
- **Version control**: Track configuration changes in your repository
- **Override flexibility**: CLI arguments always override config file values
- **Documentation**: Configuration files serve as documentation for your setup

## Configuration Files

Three example configuration files are provided in the `examples/` directory:

1. **`examples/config-monitor.yaml`** - For the `monitor` command
2. **`examples/config-event-handler.yaml`** - For the `event-handler` command
3. **`examples/config-pr-comment.yaml`** - For the `pr-comment` command

## Usage

### Monitor Command

```bash
# Use configuration file
github-monitor monitor --config examples/config-monitor.yaml

# Override specific values from config file
github-monitor monitor --config examples/config-monitor.yaml --dry-run --interval 10m

# Mix config file with CLI arguments
github-monitor monitor --config examples/config-monitor.yaml --repositories owner/repo1 owner/repo2
```

### Event Handler Command

```bash
# Use configuration file
github-monitor event-handler --config examples/config-event-handler.yaml

# Override specific values
github-monitor event-handler --config examples/config-event-handler.yaml --auto-confirm --batch-size 20

# Use config with custom consumer name
github-monitor event-handler --config examples/config-event-handler.yaml --consumer my-custom-consumer
```

### PR Comment Command

```bash
# Use configuration file
github-monitor pr-comment --config examples/config-pr-comment.yaml

# Override comment from config
github-monitor pr-comment --config examples/config-pr-comment.yaml --comment "Updated review comment"

# Use config with additional options
github-monitor pr-comment --config examples/config-pr-comment.yaml --submit approve
```

## Configuration File Format

All configuration files use YAML format. Here's an example structure:

### config-monitor.yaml

```yaml
# Base path containing repository/issue_number directories
path: "./issues"

# List of repositories to track (format: owner/repo)
repositories:
  - "owner/repo1"
  - "owner/repo2"

# NATS server URL
nats_server: "nats://localhost:4222"

# Show what would be done without making changes
dry_run: false

# Filter issues/PRs updated since this ISO8601 timestamp
updated_since: null

# Monitor options
monitor_issues: true
monitor_issue_comments: true
monitor_pr_comments: true
active_only: true

# Run monitoring at this interval (examples: "5m", "1h30m", "2d")
interval: null
```

### config-event-handler.yaml

```yaml
# Base path containing repository/issue_number directories
path: "./issues"

# Templates directory
templates_dir: null

# NATS configuration
nats_server: "nats://localhost:4222"
stream: "GITHUB_EVENTS"
consumer: "github-event-handler"

# Batch processing
batch_size: 10
fetch_timeout: "5s"
ack_wait: "300s"

# Filtering
skip_users: null
repositories: null

# Options
recreate_consumer: false
claude_verbose: false
auto_confirm: false
```

### config-pr-comment.yaml

```yaml
# Repository and PR details
repo: "owner/repo"
pr_number: 123

# Comment content
comment: "This looks good!"

# Line comment details (optional)
file: null
line: null

# GitHub token (or use GITHUB_TOKEN env var)
token: null

# Review submission (optional: approve, request_changes, comment)
submit: null
```

## Duration Format

For time-based parameters (like `interval`, `fetch_timeout`, `ack_wait`), use the format: `AdBhCmDs`

Examples:
- `"5s"` - 5 seconds
- `"30s"` - 30 seconds
- `"5m"` - 5 minutes
- `"1h"` - 1 hour
- `"1h30m"` - 1 hour and 30 minutes
- `"2d"` - 2 days
- `"1d12h30m"` - 1 day, 12 hours, and 30 minutes

## CLI Argument Priority

When both a configuration file and CLI arguments are provided:

1. **CLI arguments always take precedence** over config file values
2. **Config file values** are used when CLI arguments are not provided
3. **Default values** are used when neither config nor CLI provides a value

Example:
```bash
# If examples/config-monitor.yaml has: path: "./issues"
# This command will use path: "./my-issues" (CLI overrides config)
github-monitor monitor --config examples/config-monitor.yaml --path ./my-issues
```

## Tips

1. **Start with examples**: Copy one of the provided config files from `examples/` and modify it
2. **Use null for optional values**: Set optional parameters to `null` if not needed (or omit them)
3. **Version control**: Commit your config files (except sensitive data like tokens)
4. **Multiple configs**: Create different config files for different environments
   - `config-monitor-dev.yaml`
   - `config-monitor-prod.yaml`
5. **Environment variables**: Still use environment variables for sensitive data like `GITHUB_TOKEN`
