"""Command-line interface for github-monitor."""

import cyclopts

from github_monitor.cli.event_handler import event_handler
from github_monitor.cli.monitor import monitor
from github_monitor.cli.pr_comment import pr_comment


app = cyclopts.App(name="github-monitor", help="GitHub monitoring and event handling tool")

# Register commands
app.command(monitor, name="monitor")
app.command(event_handler, name="event-handler")
app.command(pr_comment, name="pr-comment")

if __name__ == "__main__":
    app()
