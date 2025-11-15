"""Event handler command for github-monitor CLI."""

import asyncio
import sys
from datetime import timedelta
from pathlib import Path
from typing import Annotated

import cyclopts
from nats.aio.client import Client as NATS
from nats.js.api import ConsumerConfig, DeliverPolicy

from github_monitor.cli.config_loader import load_config, merge_config_with_defaults
from github_monitor.event_handler import EventHandler, check_claude_installed, message_handler


async def event_handler_main(args):
    """Main async function for event handler command."""
    # Check if claude is available
    claude_available = check_claude_installed()
    if not claude_available:
        print(
            "Warning: Claude CLI is not installed. Will skip Claude invocations.",
            file=sys.stderr,
        )
        print(
            "Install from: https://github.com/anthropics/anthropic-quickstarts",
            file=sys.stderr,
        )
        print()

    # Create event handler
    handler = EventHandler(
        base_path=args.path,
        claude_available=claude_available,
        templates_dir=args.templates_dir,
        skip_users=args.skip_users,
        repositories=args.repositories,
        claude_verbose=args.claude_verbose,
    )

    # Connect to NATS
    nc = NATS()

    try:
        print(f"Connecting to NATS at {args.nats_server}...")
        await nc.connect(args.nats_server)
        print("Connected to NATS")
        print()

        # Get JetStream context
        js = nc.jetstream()

        # Create or get the consumer with proper configuration
        # For new consumers, start from the beginning of the stream (DeliverPolicy.ALL)
        print(f"Setting up consumer '{args.consumer}' on stream '{args.stream}'...")

        consumer_exists = False
        try:
            # Check if consumer already exists
            consumer_info = await js.consumer_info(args.stream, args.consumer)
            consumer_exists = True
            print(f"Consumer '{args.consumer}' already exists (pending: {consumer_info.num_pending})")

            # If recreate flag is set, delete and recreate the consumer
            if args.recreate_consumer:
                print("Recreating consumer as requested...")
                await js.delete_consumer(args.stream, args.consumer)
                consumer_exists = False
        except Exception:
            # Consumer doesn't exist
            pass

        if not consumer_exists:
            # Create consumer with DeliverPolicy.ALL and extended ack_wait
            print("Creating new consumer with DeliverPolicy.ALL...")

            consumer_config = ConsumerConfig(
                durable_name=args.consumer,
                deliver_policy=DeliverPolicy.ALL,
                ack_policy="explicit",
                ack_wait=int(args.ack_wait.total_seconds()),  # Extended timeout for long-running operations
            )
            await js.add_consumer(args.stream, consumer_config)
            consumer_info = await js.consumer_info(args.stream, args.consumer)
            print(f"Created new consumer '{args.consumer}' (pending: {consumer_info.num_pending})")
            print(f"Consumer configured with ack_wait={int(args.ack_wait.total_seconds())} seconds")

        # Subscribe to JetStream stream with durable consumer
        print("Creating pull subscription...")

        psub = await js.pull_subscribe(
            "github.*",  # Subscribe to all GitHub events (issues, PRs, and comments)
            durable=args.consumer,
            stream=args.stream,
        )
        print(f"Subscribed to stream '{args.stream}' with durable consumer '{args.consumer}'")
        print()
        if args.max_concurrent > 1:
            print(f"Parallel processing enabled with max_concurrent={args.max_concurrent}")
        else:
            print("Sequential processing enabled (max_concurrent=1)")
        print("Listening for events... (Press Ctrl+C to exit)")
        print()

        # Create semaphore to limit concurrent message processing
        semaphore = asyncio.Semaphore(args.max_concurrent)

        async def process_with_semaphore(msg):
            """Process a message with semaphore-based concurrency control."""
            async with semaphore:
                await message_handler(msg, handler, args.auto_confirm)

        # Continuously fetch and process messages
        while True:
            try:
                # Fetch messages in batches
                msgs = await psub.fetch(batch=args.batch_size, timeout=args.fetch_timeout.total_seconds())

                # Process messages in parallel (up to max_concurrent at a time)
                if args.max_concurrent > 1:
                    # Parallel processing using asyncio.gather
                    tasks = [process_with_semaphore(msg) for msg in msgs]
                    await asyncio.gather(*tasks, return_exceptions=True)
                else:
                    # Sequential processing for backward compatibility
                    for msg in msgs:
                        await message_handler(msg, handler, args.auto_confirm)
            except TimeoutError:
                # No messages available, continue polling
                continue
            except Exception as e:
                print(f"Error fetching messages: {e}", file=sys.stderr)
                await asyncio.sleep(1)  # Brief pause before retrying

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        if nc.is_connected:
            await nc.close()

    return 0


def event_handler(
    path: Annotated[
        Path | None, cyclopts.Parameter(help="Base path containing repository/issue_number directories")
    ] = None,
    templates_dir: Annotated[
        Path | None, cyclopts.Parameter(help="Templates directory containing markdown files for event handlers")
    ] = None,
    nats_server: Annotated[str | None, cyclopts.Parameter(help="NATS server URL")] = None,
    stream: Annotated[str | None, cyclopts.Parameter(help="JetStream stream name")] = None,
    consumer: Annotated[str | None, cyclopts.Parameter(help="Durable consumer name")] = None,
    batch_size: Annotated[int | None, cyclopts.Parameter(help="Number of messages to fetch per batch")] = None,
    fetch_timeout: Annotated[
        timedelta | None, cyclopts.Parameter(help="Timeout for fetching messages (format: AdBhCmDs, e.g., 5s, 30s)")
    ] = None,
    ack_wait: Annotated[
        timedelta | None,
        cyclopts.Parameter(help="AckWait timeout for message processing (format: AdBhCmDs, e.g., 5m, 300s)"),
    ] = None,
    max_concurrent: Annotated[
        int | None,
        cyclopts.Parameter(
            help="Maximum number of events to process concurrently. Set to 1 for sequential processing. Default: 5"
        ),
    ] = None,
    skip_users: Annotated[
        str | None, cyclopts.Parameter(help="Regex pattern to match usernames to skip event handling for")
    ] = None,
    repositories: Annotated[
        str | None,
        cyclopts.Parameter(
            help="Regex pattern to filter repositories (e.g., 'owner/repo' or '.*my-org.*'). "
            "Only matching repositories will be processed."
        ),
    ] = None,
    recreate_consumer: Annotated[
        bool | None, cyclopts.Parameter(help="Delete and recreate the consumer (useful for reprocessing all messages)")
    ] = None,
    claude_verbose: Annotated[
        bool | None, cyclopts.Parameter(help="Print raw Claude CLI output directly to stdout instead of parsing JSONL")
    ] = None,
    auto_confirm: Annotated[
        bool | None,
        cyclopts.Parameter(
            help="Automatically process events without confirmation. If not set, prompts after each event."
        ),
    ] = None,
    config: Annotated[
        Path | None,
        cyclopts.Parameter(help="Path to YAML configuration file. CLI arguments override config file values."),
    ] = None,
):
    """Handle GitHub issue and PR events from NATS JetStream."""

    # Load configuration from file if provided
    if config:
        file_config = load_config(config)
    else:
        file_config = {}

    # Merge with CLI arguments (CLI takes precedence)
    cli_values = {
        "path": path,
        "templates_dir": templates_dir,
        "nats_server": nats_server,
        "stream": stream,
        "consumer": consumer,
        "batch_size": batch_size,
        "fetch_timeout": fetch_timeout,
        "ack_wait": ack_wait,
        "max_concurrent": max_concurrent,
        "skip_users": skip_users,
        "repositories": repositories,
        "recreate_consumer": recreate_consumer,
        "claude_verbose": claude_verbose,
        "auto_confirm": auto_confirm,
    }
    merged_config = merge_config_with_defaults(file_config, cli_values)

    # Apply defaults for any missing values
    final_path = merged_config.get("path")
    if final_path is None:
        print("Error: path is required (via --path or in config file)", file=sys.stderr)
        sys.exit(1)
    final_path = Path(final_path)

    final_templates_dir = merged_config.get("templates_dir")
    if final_templates_dir is not None:
        final_templates_dir = Path(final_templates_dir)

    final_nats_server = merged_config.get("nats_server", "nats://localhost:4222")
    final_stream = merged_config.get("stream", "GITHUB_EVENTS")
    final_consumer = merged_config.get("consumer", "github-event-handler")
    final_batch_size = merged_config.get("batch_size", 10)
    final_max_concurrent = merged_config.get("max_concurrent", 5)
    final_recreate_consumer = merged_config.get("recreate_consumer", False)
    final_claude_verbose = merged_config.get("claude_verbose", False)
    final_auto_confirm = merged_config.get("auto_confirm", False)

    # Handle timedelta values - could be strings from config or timedelta from CLI
    final_fetch_timeout = merged_config.get("fetch_timeout", timedelta(seconds=5))
    if isinstance(final_fetch_timeout, str):
        final_fetch_timeout = parse_duration_to_timedelta(final_fetch_timeout)

    final_ack_wait = merged_config.get("ack_wait", timedelta(seconds=300))
    if isinstance(final_ack_wait, str):
        final_ack_wait = parse_duration_to_timedelta(final_ack_wait)

    # Create args object with parsed values
    class Args:
        pass

    args = Args()
    args.path = final_path
    args.templates_dir = final_templates_dir
    args.nats_server = final_nats_server
    args.stream = final_stream
    args.consumer = final_consumer
    args.batch_size = final_batch_size
    args.fetch_timeout = final_fetch_timeout
    args.ack_wait = final_ack_wait
    args.max_concurrent = final_max_concurrent
    args.skip_users = merged_config.get("skip_users")
    args.repositories = merged_config.get("repositories")
    args.recreate_consumer = final_recreate_consumer
    args.claude_verbose = final_claude_verbose
    args.auto_confirm = final_auto_confirm

    # Run async main
    try:
        exit_code = asyncio.run(event_handler_main(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


def parse_duration_to_timedelta(duration_str: str) -> timedelta:
    """Parse duration string like '5m', '1h30m', '2d' to timedelta.

    Args:
        duration_str: Duration string

    Returns:
        timedelta object
    """
    import re

    if not duration_str:
        return timedelta(seconds=5)

    total_seconds = 0
    # Pattern matches: number followed by unit (d, h, m, s)
    pattern = r"(\d+)([dhms])"
    matches = re.findall(pattern, duration_str.lower())

    if not matches:
        return timedelta(seconds=5)

    for value, unit in matches:
        value = int(value)
        if unit == "d":
            total_seconds += value * 86400
        elif unit == "h":
            total_seconds += value * 3600
        elif unit == "m":
            total_seconds += value * 60
        elif unit == "s":
            total_seconds += value

    return timedelta(seconds=total_seconds if total_seconds > 0 else 5)
