# Utils Directory

This directory contains utility modules for the RAI Chat application. 

## Core Utility Files

The following files are the primary utility modules that should be used:

- **pathconfig.py** - Centralized path configuration and utilities
  - Handles path determination across Docker and local environments
  - Provides utility functions for working with paths
  - CONSOLIDATION: Replaces and combines functionality from `path.py` and `path_manager.py`

- **imports.py** - Import management utilities
  - Ensures consistent imports across Docker and local environments
  - Tools for fixing import statements for Docker compatibility
  - CONSOLIDATION: Includes functionality from `fix_docker_imports.py`

## Other Utility Files

- **module_loader.py** - Handles dynamic module loading
- **llm_api_client.py** - Low-level LLM API client utilities

## Deprecated Files (Do Not Use)

The following files have been deprecated and their functionality consolidated into the core utility files:

- ~~path.py~~ - Use `pathconfig.py` instead
- ~~path_manager.py~~ - Use `pathconfig.py` instead
- ~~path_finder.py~~ - Analysis tool that may still be used for development, but not by the application itself
- ~~fix_docker_imports.py~~ - Use `imports.py` instead (the function `fix_imports_for_docker()`)

## Usage Examples

### Path Configuration (pathconfig.py)

```python
from utils.pathconfig import DATA_DIR, get_user_base_dir, ensure_directory_exists

# Get directory for a user
user_dir = get_user_base_dir("user_123")

# Ensure a directory exists
log_dir = ensure_directory_exists(DATA_DIR / "logs")
```

### Import Management (imports.py)

```python
# Add to top of files to configure paths
from utils.imports import configure_import_paths
configure_import_paths()

# Import modules consistently
from utils.imports import import_module
models = import_module("core.database.models")

# Fix imports for Docker (development use only)
from utils.imports import fix_imports_for_docker
fix_imports_for_docker()
```
