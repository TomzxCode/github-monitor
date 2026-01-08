# GitHub Monitor

A Python-based system that monitors GitHub repositories for issues and pull requests through polling using GitHub's GraphQL API, then publishes events to NATS JetStream for processing.

## Overview

GitHub Monitor is a two-component system designed for automated GitHub issue and PR management:

1. **Monitor** (`github-monitor monitor`): Polls GitHub repositories for issues/PRs using GraphQL API and publishes events to NATS
2. **Event Handler** (`github-monitor event-handler`): Consumes events from NATS and invokes Claude CLI to process them

## Quick Start

```bash
# Install dependencies
uv sync

# Monitor GitHub repositories (run once)
uv run github-monitor monitor /path/to/data --repositories owner/repo

# Monitor with interval (e.g., every 5 minutes)
uv run github-monitor monitor /path/to/data --repositories owner/repo --interval 5m

# Handle events from NATS
uv run github-monitor event-handler /path/to/data --templates-dir /path/to/templates
```

## Features

- **GitHub GraphQL API**: Efficient polling with pagination and filtering
- **NATS JetStream**: Reliable message streaming with configurable retention
- **Template-based Processing**: Customizable event handling with markdown templates
- **PR Comments**: Create line-specific and general comments on pull requests
- **Active Tracking**: Only process issues/PRs marked with `.active` files
- **Comment Monitoring**: Track new comments on issues and PRs

## Documentation

- [Configuration Guide](CONFIG.md)
- [Specifications](spec/) - Detailed technical specifications for each component

## Directory Structure

The system uses a hierarchical directory structure to track issues/PRs:

```
{base_path}/{owner}/{repo}/{issue_or_pr_number}/
├── .active          # Flag file indicating active monitoring
├── .type            # Cached type (issue or pr)
├── .last_checked    # Last monitoring check timestamp
└── .last_comment_check  # Last comment check timestamp
```

## License

See [LICENSE](../LICENSE) for details.
