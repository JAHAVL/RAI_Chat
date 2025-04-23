# AI Assistant App - Modular Architecture

## Architecture Overview

The AI Assistant app has been restructured to follow a truly modular architecture where each module is self-contained and can be purchased/distributed separately. This document outlines the architectural design decisions and implementation details.

## Key Design Principles

1. **Self-Contained Modules**: Each module contains everything it needs to function, including backend API, frontend UI components, and module-specific assets.

2. **RESTful API Architecture**: Modules communicate with the core application and each other exclusively through well-defined RESTful APIs.

3. **Dynamic Module Loading**: The core application dynamically discovers and loads available modules at runtime.

4. **Consistent File Structure**: All modules follow a consistent file structure and naming convention.

## Module Structure

Each module follows this structure:

```
modules/
  [module_name]_module/
    __init__.py                 # Python package initialization
    [module_name]_api.py        # Backend API endpoints
    [module_name]_module.py     # Module functionality implementation
    [module_name]_ui.py         # Legacy UI integration
    ui/
      react/                    # React components for this module
        components/             # UI components
        api/                    # Frontend API interfaces
        module.js               # Module registration
      assets/                   # Module-specific assets
    package.json                # Module's package definition
```

## Core Application Structure

The core application is in the RAI_Chat directory:

```
RAI_Chat/
  frontend/
    module_loader.js            # Module registration system
    module_discovery.js         # Module discovery and loading
    App.jsx                     # Main application component
    shared/                     # Shared resources
      theme.ts                  # Shared theme definition
```

## Module Registration System

Modules register themselves with the core application through a standardized registration process:

1. Each module has a `module.js` file that exports a `register` function
2. The core application scans for available modules at startup
3. Each discovered module is registered with the system
4. The core application dynamically renders UI components from registered modules

## Current Modules

The following modules have been implemented:

1. **chat_module**: Provides the core chat assistant functionality
2. **video_module**: Provides video analysis capabilities 
3. **code_editor_module**: Provides code editing and execution functionality

## Future Enhancements

1. **Module Versioning**: Add version compatibility checking
2. **Module Marketplace**: Create a system for listing and installing additional modules
3. **Access Control**: Add license validation for purchased modules

## Migration Notes

The application has been restructured from its previous organization. Legacy files have been backed up and can be safely removed using the `cleanup_legacy_files.sh` script.
