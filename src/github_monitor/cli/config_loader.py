"""Configuration file loader for github-monitor CLI."""

import sys
from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: Path | str) -> dict[str, Any]:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Dictionary containing the configuration

    Raises:
        SystemExit: If the file cannot be read or parsed
    """
    config_path = Path(config_path)

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if config is None:
            return {}

        if not isinstance(config, dict):
            print(f"Error: Configuration file must contain a YAML dictionary: {config_path}", file=sys.stderr)
            sys.exit(1)

        return config

    except yaml.YAMLError as e:
        print(f"Error: Failed to parse YAML configuration file: {config_path}", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to read configuration file: {config_path}", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        sys.exit(1)


def merge_config_with_defaults(config: dict[str, Any], cli_values: dict[str, Any]) -> dict[str, Any]:
    """Merge configuration from file with CLI arguments.

    CLI arguments take precedence over config file values.

    Args:
        config: Configuration loaded from file
        cli_values: Values provided via CLI (None values are ignored)

    Returns:
        Merged configuration dictionary
    """
    result = config.copy()

    # Override with CLI values that are not None
    for key, value in cli_values.items():
        if value is not None:
            result[key] = value

    return result
