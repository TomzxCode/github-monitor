"""Monitor command for github-monitor CLI."""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import cyclopts
from nats.aio.client import Client as NATS

from github_monitor.monitor import (
    ensure_jetstream_stream,
    find_active_issues,
    get_github_client,
    get_tracked_repositories,
    is_pull_request,
    monitor_issue_comments,
    monitor_pr_comments,
    monitor_repositories,
    parse_duration,
    process_active_issues,
)


async def run_monitoring_cycle(args, nc, js):
    """Run a single monitoring cycle."""
    # Determine which repositories to track
    if args.repositories:
        repositories = args.repositories
    else:
        repositories = get_tracked_repositories(args.path)

    if not repositories:
        print(
            "No repositories to track. Specify repositories with --repositories owner/repo",
            file=sys.stderr,
        )
        return 1

    print(f"Tracking repositories: {', '.join(repositories)}\n")

    # Monitor repositories and publish events for new issues/PRs (if enabled)
    if args.monitor_issues:
        new_count = await monitor_repositories(js, args.path, repositories, args.dry_run, args.updated_since)
        if new_count > 0:
            print(f"Discovered {new_count} new issue(s)/PR(s)\n")

    # Find all active issues/PRs (if issue monitoring is enabled)
    active_issues = []
    active_prs = []
    if args.monitor_issues:
        if args.active_only:
            print(f"Scanning {args.path} for active issues/PRs (with .active flag)...")
        else:
            print(f"Scanning {args.path} for all issues/PRs...")
        all_active_items = find_active_issues(args.path, args.active_only, repositories)

        if not all_active_items:
            print("No active issues/PRs found.")
            # Don't return early - we might still want to monitor comments
        else:
            # Separate issues from PRs
            for repository, number in all_active_items:
                if is_pull_request(repository, number, args.path):
                    active_prs.append((repository, number))
                else:
                    active_issues.append((repository, number))

            print(f"Found {len(active_issues)} active issue(s) and {len(active_prs)} active PR(s)\n")

            # Process active issues/PRs and publish events
            await process_active_issues(js, args.path, all_active_items, args.dry_run)
    elif args.monitor_issue_comments or args.monitor_pr_comments:
        # If comment monitoring is enabled but issue monitoring is not,
        # still need to find active issues/PRs for comment checking
        if args.active_only:
            print(f"Scanning {args.path} for active issues/PRs (with .active flag, for comment monitoring)...")
        else:
            print(f"Scanning {args.path} for all issues/PRs (for comment monitoring)...")
        all_active_items = find_active_issues(args.path, args.active_only, repositories)
        if not all_active_items:
            print("No active issues/PRs found.")
        else:
            # Separate issues from PRs
            for repository, number in all_active_items:
                if is_pull_request(repository, number, args.path):
                    active_prs.append((repository, number))
                else:
                    active_issues.append((repository, number))

            print(f"Found {len(active_issues)} active issue(s) and {len(active_prs)} active PR(s)\n")

    # Monitor issue comments if enabled
    if args.monitor_issue_comments and active_issues:
        print("Monitoring issue comments...")
        comment_count = await monitor_issue_comments(js, args.path, active_issues, args.dry_run)
        if comment_count > 0:
            print(f"Found {comment_count} new issue comment{'s' if comment_count != 1 else ''}\n")
        else:
            print()

    # Monitor PR comments if enabled
    if args.monitor_pr_comments and active_prs:
        print("Monitoring PR comments...")
        pr_count = await monitor_pr_comments(js, args.path, active_prs, args.dry_run)
        if pr_count > 0:
            print(f"Found {pr_count} new PR comment{'s' if pr_count != 1 else ''}\n")
        else:
            print()

    return 0


async def monitor_main(args):
    """Main async function for monitor command."""
    # Connect to NATS
    nc = NATS()
    js = None

    try:
        if not args.dry_run:
            print(f"Connecting to NATS at {args.nats_server}...")
            await nc.connect(args.nats_server)
            print("Connected to NATS\n")

            # Ensure JetStream stream exists and get JetStream context
            js = await ensure_jetstream_stream(nc)
            print()

        # If interval is specified, run in a loop
        if args.interval:
            print(f"Running monitoring every {args.interval} seconds. Press Ctrl+C to stop.\n")
            cycle_count = 0
            try:
                while True:
                    cycle_count += 1
                    cycle_start = datetime.now(timezone.utc)
                    print(f"=== Monitoring Cycle {cycle_count} at {cycle_start.isoformat()} ===\n")

                    await run_monitoring_cycle(args, nc, js)

                    cycle_end = datetime.now(timezone.utc)
                    elapsed_seconds = (cycle_end - cycle_start).total_seconds()

                    # Calculate remaining time to maintain fixed interval
                    sleep_duration = max(0, args.interval - elapsed_seconds)

                    if sleep_duration > 0:
                        print(
                            f"=== Cycle {cycle_count} completed in {elapsed_seconds:.2f}s. "
                            f"Waiting {sleep_duration:.2f}s until next cycle ===\n"
                        )
                        await asyncio.sleep(sleep_duration)
                    else:
                        print(
                            f"=== Cycle {cycle_count} completed in {elapsed_seconds:.2f}s. "
                            f"Cycle took longer than interval ({args.interval}s), "
                            f"starting next cycle immediately ===\n"
                        )
            except KeyboardInterrupt:
                print("\n\n=== Monitoring interrupted by user ===")
                print(f"Completed {cycle_count} monitoring cycle(s)")
                print("Shutting down gracefully...\n")
        else:
            # Run once
            await run_monitoring_cycle(args, nc, js)

    except KeyboardInterrupt:
        print("\n\n=== Monitoring interrupted by user ===")
        print("Shutting down gracefully...\n")
    finally:
        if not args.dry_run and nc.is_connected:
            print("Closing NATS connection...")
            await nc.close()
            print("NATS connection closed.")

    return 0


def monitor(
    path: Annotated[Path, cyclopts.Parameter(help="Base path containing repository/issue_number directories")],
    repositories: Annotated[
        list[str] | None,
        cyclopts.Parameter(
            help="List of repositories to track (format: owner/repo). If not provided, uses existing directories."
        ),
    ] = None,
    nats_server: Annotated[str, cyclopts.Parameter(help="NATS server URL")] = "nats://localhost:4222",
    dry_run: Annotated[bool, cyclopts.Parameter(help="Show what would be done without making changes")] = False,
    updated_since: Annotated[
        str | None,
        cyclopts.Parameter(help="Filter issues/PRs updated since this ISO8601 timestamp (e.g., 2024-01-01T00:00:00Z)"),
    ] = None,
    monitor_issues: Annotated[
        bool, cyclopts.Parameter(help="Monitor and publish events for issues and PRs (new, updated, closed)")
    ] = True,
    monitor_issue_comments: Annotated[
        bool, cyclopts.Parameter(help="Monitor and publish events for new comments on active issues")
    ] = True,
    monitor_pr_comments: Annotated[
        bool, cyclopts.Parameter(help="Monitor and publish events for new comments on active pull requests")
    ] = True,
    active_only: Annotated[
        bool,
        cyclopts.Parameter(
            help="Only monitor issues/PRs with .active flag. Use --no-active-only to monitor all directories."
        ),
    ] = True,
    interval: Annotated[
        timedelta | None,
        cyclopts.Parameter(
            help=(
                "Run monitoring at this interval (format: AdBhCmDs, e.g., 5m, 1h30m, 2d). "
                "If not specified, runs once and exits."
            )
        ),
    ] = None,
):
    """Monitor GitHub issues and publish events to NATS."""

    # Create args object with parsed values
    class Args:
        pass

    args = Args()
    args.path = path
    args.repositories = repositories
    args.nats_server = nats_server
    args.dry_run = dry_run
    args.updated_since = updated_since
    args.monitor_issues = monitor_issues
    args.monitor_issue_comments = monitor_issue_comments
    args.monitor_pr_comments = monitor_pr_comments
    args.active_only = active_only
    args.interval = interval.total_seconds() if interval else None

    # Check that GitHub token is available
    try:
        get_github_client()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Please set GITHUB_TOKEN environment variable or create a .env file.", file=sys.stderr)
        sys.exit(1)

    # Run async main with proper keyboard interrupt handling
    try:
        exit_code = asyncio.run(monitor_main(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        # Handle interrupt at top level (though monitor_main should catch it)
        print("\n\n=== Monitoring interrupted ===", file=sys.stderr)
        sys.exit(130)  # Standard exit code for SIGINT
