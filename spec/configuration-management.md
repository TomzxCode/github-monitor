# Configuration Management Specification

## Overview

The Configuration Management module provides functionality for loading configuration from YAML files and merging it with CLI arguments. It ensures that CLI arguments always take precedence over configuration file values while providing sensible defaults.

## Requirements

### Core Functionality

#### 1. Configuration File Loading
- The system MUST load configuration from YAML files specified via `--config`
- The system MUST accept both string paths and `Path` objects
- The system MUST validate that the configuration file exists
- The system MUST call `sys.exit(1)` if the configuration file is not found
- The system MUST use `yaml.safe_load()` for secure YAML parsing
- The system MUST return an empty dictionary if the YAML file is empty
- The system MUST validate that the parsed YAML is a dictionary (not list or scalar)

#### 2. Error Handling
- The system MUST catch `yaml.YAMLError` and report parsing failures
- The system MUST catch general exceptions for file read errors
- The system MUST print all error messages to stderr
- The system MUST include the file path in error messages
- The system MUST include the specific YAML error details when parsing fails
- The system MUST exit with code 1 for all configuration errors

#### 3. Configuration Merging
- The system MUST provide a function to merge configuration with CLI values
- The system MUST copy the base configuration before merging
- The system MUST only apply CLI values that are not `None`
- The system MUST NOT override configuration values with `None` from CLI
- CLI arguments MUST always take precedence over file values

### API Reference

#### `load_config(config_path: Path | str) -> dict[str, Any]`

Load configuration from a YAML file.

**Parameters:**
- `config_path`: Path to the YAML configuration file

**Returns:**
- Dictionary containing the configuration

**Raises:**
- `SystemExit(1)`: If the file cannot be read or parsed

**Error Messages:**
- File not found: `"Error: Configuration file not found: {config_path}"`
- Invalid format: `"Error: Configuration file must contain a YAML dictionary: {config_path}"`
- YAML error: `"Error: Failed to parse YAML configuration file: {config_path}\n  {error}"`
- Read error: `"Error: Failed to read configuration file: {config_path}\n  {error}"`

#### `merge_config_with_defaults(config: dict[str, Any], cli_values: dict[str, Any]) -> dict[str, Any]`

Merge configuration from file with CLI arguments.

**Parameters:**
- `config`: Configuration loaded from file
- `cli_values`: Values provided via CLI (None values are ignored)

**Returns:**
- Merged configuration dictionary

### Merging Behavior

Given a configuration file:

```yaml
path: /data/github
nats_server: nats://remote:4222
dry_run: false
```

And CLI values:

```python
{
    "path": None,  # Not provided via CLI
    "dry_run": True,  # Explicitly set via CLI
    "repositories": ["owner/repo"]  # Only via CLI
}
```

The merged result will be:

```python
{
    "path": "/data/github",  # From config (CLI None ignored)
    "nats_server": "nats://remote:4222",  # From config
    "dry_run": True,  # CLI overrides config
    "repositories": ["owner/repo"]  # CLI only
}
```

### Dependencies

- `yaml` (PyYAML) - YAML file parsing
- `pathlib.Path` - Path handling
- `sys` - System exit

### Security Considerations

- The system MUST use `yaml.safe_load()` instead of `yaml.load()` to prevent arbitrary code execution
- The system MUST validate the YAML structure before use
- The system MUST handle malformed YAML gracefully without exposing sensitive data
