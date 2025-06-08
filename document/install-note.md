# UV Package Management Guide

## Installation Commands

### To install a package:
```bash
uv pip install <package_name>
```

### To list all packages installed in the current virtual environment:
```bash
uv pip list
```

### To remove all packages from the virtual environment:
```bash
uv pip uninstall -r <(uv pip list --format=freeze)
```

**Note:** `uv pip list --format=freeze` generates a list of installed packages in requirements.txt format, which is piped to `uv pip uninstall -r` to uninstall all packages.

### To install dev dependencies:
```bash
uv pip install ".[dev]"
```
### To sync the virtual environment with the dependencies in `pyproject.toml`:
```bash
uv sync
```

