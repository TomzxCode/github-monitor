# Event Handler Specification

## Overview

The Event Handler component consumes GitHub issue and PR events from NATS JetStream and processes them by invoking Claude CLI with customizable templates. It handles directory management for tracked issues/PRs and supports filtering by users and repositories.

## Requirements

### Core Functionality

#### 1. Message Consumption
- The system MUST connect to NATS JetStream and consume messages from the `GITHUB_EVENTS` stream
- The system MUST use a durable consumer to track message processing state
- The system MUST support configurable `ack_wait` timeout (default: 300 seconds)
- The system MUST explicitly acknowledge (`ack`) successful message processing
- The system MUST negative acknowledge (`nak`) messages that fail processing for redelivery
- The system MUST terminate (`term`) messages with fatal errors (e.g., missing required fields)

#### 2. Long-Running Message Processing
- The system MUST send periodic `in_progress` signals during Claude CLI execution to extend the acknowledgment deadline
- The system MUST send `in_progress` signals every 20 seconds during processing
- The system MUST stop signaling after processing completes or fails

#### 3. Event Type Handling
- The system MUST handle the following event types:
  - `github.issue.new` - Creates directory structure for new issues
  - `github.issue.updated` - Invokes Claude to process active issues
  - `github.issue.closed` - Removes `.active` file to mark issues as inactive
  - `github.pr.new` - Creates directory structure for new PRs
  - `github.pr.updated` - Invokes Claude to process active PRs
  - `github.pr.closed` - Removes `.active` file to mark PRs as inactive
  - `github.issue.comment.new` - Handles new comments on issues
  - `github.pr.comment.new` - Handles new comments on PRs
  - `github.issue.process` - Legacy alias for `github.issue.updated` (backward compatibility)

#### 4. Directory Management
- The system MUST create directories `{base_path}/{owner}/{repo}/{number}/` for new issues/PRs
- The system MUST remove `.active` files when issues/PRs are closed
- The system MUST NOT create `.active` files (users create these manually to enable tracking)

#### 5. Template-Based Claude Invocation
- The system MUST support a hierarchical template search:
  1. `{templates_dir}/{owner}/{repo}/{event_name}.md`
  2. `{templates_dir}/{owner}/.default/{event_name}.md`
  3. `{templates_dir}/.default/{event_name}.md`
- The system MUST use the first matching template found in the hierarchy
- The system MUST skip Claude invocation if no template is found
- The system MUST skip Claude invocation if the template file is empty (used to ignore events)
- The system MUST inject the following variables before template content:
  - `REPOSITORY={repository}` (e.g., "owner/repo")
  - `NUMBER={number}` (issue/PR number)
  - `BASE_DIR={base_path}` (absolute path)

#### 6. Claude CLI Integration
- The system MUST invoke Claude with the following arguments:
  - `--output-format stream-json`
  - `--verbose`
  - `--include-partial-messages`
  - `--allowed-tools SlashCommand`
  - `-p "{prompt}"` (variables + template content)
- The system SHOULD parse and display Claude's streaming JSON output
- The system MUST display model information, permission mode, available tools, and slash commands from init messages
- The system MUST display text content and tool use from assistant messages
- The system MUST support a `--claude-verbose` flag to output raw Claude output without parsing

#### 7. Filtering
- The system MUST support filtering by username using regex patterns (`--skip-users`)
- The system MUST support filtering by repository using regex patterns (`--repositories`)
- The system MUST acknowledge and skip events that match the skip filters

#### 8. User Interaction
- The system MUST support an `--auto-confirm` flag (default: True)
- When `--auto-confirm` is False, the system MUST prompt the user before processing each event
- The system MUST display event information before prompting:
  - Repository and number (e.g., "owner/repo#123")
  - Author username
  - URL
  - Title (if available)

### Error Handling

- The system MUST log errors to stderr without exiting for non-fatal errors
- The system MUST send `nak` for messages that fail due to processing errors (enables retry)
- The system MUST send `term` for messages with missing required fields (no retry)
- The system MUST handle JSON decode errors gracefully with `nak`

### Logging

- The system MUST print event type and action being taken (e.g., "[NEW ISSUE]", "[UPDATE PR]")
- The system MUST print template discovery results (e.g., "[TEMPLATE] Found template at ...")
- The system MUST print Claude invocation status (success/failure)
- The system MUST print comment details for comment events (author, created_at, url)

## Data Structures

### Event Message Format

All events from NATS contain the following fields:

```json
{
  "repository": string,  // "owner/repo"
  "number": int | string,
  "author": string,
  "url": string,
  "title": string | null,
  // ... additional fields from monitoring component
}
```

### Comment Event Format

```json
{
  "repository": string,
  "number": int | string,
  "comment": {
    "author": string,
    "created_at": string (ISO8601),
    "url": string,
    // ... additional comment fields
  }
}
```

## Claude CLI Output Parsing

When parsing streaming JSON output, the system MUST handle:

1. **System init messages** (`type: "system"`, `subtype: "init"`):
   - `model` - Model name
   - `permissionMode` - Permission mode
   - `tools` - List of available tools
   - `slash_commands` - List of available slash commands

2. **Assistant messages** (`type: "assistant"`):
   - `message.id` - Unique message identifier
   - `message.content` - Array of content items:
     - `type: "text"` with `text` field
     - `type: "tool_use"` with `name` and `input` fields
