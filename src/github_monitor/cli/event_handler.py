"""Event handler command for github-monitor CLI."""

import asyncio
import sys
from pathlib import Path
from typing import Annotated

import cyclopts
from nats.aio.client import Client as NATS
from nats.js.api import ConsumerConfig, DeliverPolicy

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
            # Create consumer with DeliverPolicy.ALL
            print("Creating new consumer with DeliverPolicy.ALL...")

            consumer_config = ConsumerConfig(
                durable_name=args.consumer,
                deliver_policy=DeliverPolicy.ALL,
                ack_policy="explicit",
            )
            await js.add_consumer(args.stream, consumer_config)
            consumer_info = await js.consumer_info(args.stream, args.consumer)
            print(f"Created new consumer '{args.consumer}' (pending: {consumer_info.num_pending})")

        # Subscribe to JetStream stream with durable consumer
        print("Creating pull subscription...")

        psub = await js.pull_subscribe(
            "github.*",  # Subscribe to all GitHub events (issues, PRs, and comments)
            durable=args.consumer,
            stream=args.stream,
        )
        print(f"Subscribed to stream '{args.stream}' with durable consumer '{args.consumer}'")
        print()
        print("Listening for events... (Press Ctrl+C to exit)")
        print()

        # Continuously fetch and process messages
        while True:
            try:
                # Fetch messages in batches
                msgs = await psub.fetch(batch=args.batch_size, timeout=args.fetch_timeout)
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
    path: Annotated[Path, cyclopts.Parameter(help="Base path containing repository/issue_number directories")],
    templates_dir: Annotated[
        Path | None, cyclopts.Parameter(help="Templates directory containing markdown files for event handlers")
    ] = None,
    nats_server: Annotated[str, cyclopts.Parameter(help="NATS server URL")] = "nats://localhost:4222",
    stream: Annotated[str, cyclopts.Parameter(help="JetStream stream name")] = "GITHUB_EVENTS",
    consumer: Annotated[str, cyclopts.Parameter(help="Durable consumer name")] = "github-event-handler",
    batch_size: Annotated[int, cyclopts.Parameter(help="Number of messages to fetch per batch")] = 10,
    fetch_timeout: Annotated[float, cyclopts.Parameter(help="Timeout in seconds for fetching messages")] = 5.0,
    skip_users: Annotated[
        str | None, cyclopts.Parameter(help="Regex pattern to match usernames to skip event handling for")
    ] = None,
    repositories: Annotated[
        str | None,
        cyclopts.Parameter(
            help="Regex pattern to filter repositories (e.g., 'owner/repo' or '.*my-org.*'). Only matching repositories will be processed."
        ),
    ] = None,
    recreate_consumer: Annotated[
        bool, cyclopts.Parameter(help="Delete and recreate the consumer (useful for reprocessing all messages)")
    ] = False,
    claude_verbose: Annotated[
        bool, cyclopts.Parameter(help="Print raw Claude CLI output directly to stdout instead of parsing JSONL")
    ] = False,
    auto_confirm: Annotated[
        bool,
        cyclopts.Parameter(
            help="Automatically process events without confirmation. If not set, prompts after each event."
        ),
    ] = False,
):
    """Handle GitHub issue and PR events from NATS JetStream."""

    # Create args object with parsed values
    class Args:
        pass

    args = Args()
    args.path = path
    args.templates_dir = templates_dir
    args.nats_server = nats_server
    args.stream = stream
    args.consumer = consumer
    args.batch_size = batch_size
    args.fetch_timeout = fetch_timeout
    args.skip_users = skip_users
    args.repositories = repositories
    args.recreate_consumer = recreate_consumer
    args.claude_verbose = claude_verbose
    args.auto_confirm = auto_confirm

    # Run async main
    try:
        exit_code = asyncio.run(event_handler_main(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
