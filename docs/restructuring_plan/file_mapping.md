# RAI Chat Backend File Mapping

This document provides a detailed mapping of current files to their new locations in the proposed structure.

## File Mapping

| Current Path | New Path | Notes |
|-------------|----------|-------|
| `RAI_Chat/Backend/rai_api_server.py` | `RAI_Chat/backend/app.py` + `RAI_Chat/backend/wsgi.py` | Split into application factory and WSGI entry point |
| `RAI_Chat/Backend/Launch_App.py` | `RAI_Chat/scripts/launch_app.py` | Moved to scripts directory |
| `RAI_Chat/Backend/config.py` | `RAI_Chat/backend/config.py` | Centralized configuration |
| `RAI_Chat/Backend/api/chat_api.py` | `RAI_Chat/backend/api/chat.py` | Moved to API blueprint |
| `RAI_Chat/Backend/components/action_handler.py` | `RAI_Chat/backend/services/action_handler.py` | Moved to services |
| `RAI_Chat/Backend/components/prompt_builder.py` | `RAI_Chat/backend/services/prompt_builder.py` | Moved to services |
| `RAI_Chat/Backend/components/prompts.py` | `RAI_Chat/backend/services/prompts.py` | Moved to services |
| `RAI_Chat/Backend/core/auth/models.py` | `RAI_Chat/backend/core/auth/models.py` | Path case changed |
| `RAI_Chat/Backend/core/auth/service.py` | `RAI_Chat/backend/core/auth/service.py` | Path case changed |
| `RAI_Chat/Backend/core/auth/strategies.py` | `RAI_Chat/backend/core/auth/strategies.py` | Path case changed |
| `RAI_Chat/Backend/core/auth/utils.py` | `RAI_Chat/backend/core/auth/utils.py` | Path case changed |
| `RAI_Chat/Backend/core/database/connection.py` | `RAI_Chat/backend/core/database/session.py` | Renamed for clarity |
| `RAI_Chat/Backend/core/database/models.py` | `RAI_Chat/backend/core/database/models.py` | Path case changed |
| `RAI_Chat/Backend/managers/chat_file_manager.py` | `RAI_Chat/backend/services/file_storage.py` | Moved to services |
| `RAI_Chat/Backend/managers/conversation_manager.py` | `RAI_Chat/backend/services/conversation.py` | Moved to services |
| `RAI_Chat/Backend/managers/user_session_manager.py` | `RAI_Chat/backend/services/session.py` | Moved to services |
| `RAI_Chat/Backend/managers/memory/contextual_memory.py` | `RAI_Chat/backend/services/memory/contextual.py` | Moved to services/memory |
| `RAI_Chat/Backend/managers/memory/episodic_memory.py` | `RAI_Chat/backend/services/memory/episodic.py` | Moved to services/memory |
| `RAI_Chat/Backend/Built_in_modules/web_search_module/tavily_client.py` | `RAI_Chat/backend/modules/web_search/tavily.py` | Moved to modules |
| `RAI_Chat/Backend/utils/module_loader.py` | `RAI_Chat/backend/utils/module_loader.py` | Path case changed |
| `RAI_Chat/Backend/utils/path_finder.py` | `RAI_Chat/backend/utils/path.py` | Consolidated path utilities |
| `RAI_Chat/Backend/utils/path_manager.py` | `RAI_Chat/backend/utils/path.py` | Consolidated path utilities |
| `RAI_Chat/Backend/alembic/*` | `RAI_Chat/backend/migrations/*` | Moved to migrations directory |
| `RAI_Chat/Backend/scripts/*.py` | `RAI_Chat/scripts/*.py` | Moved to top-level scripts directory |
| `RAI_Chat/Backend/tests/*.py` | `RAI_Chat/tests/unit/*.py` or `RAI_Chat/tests/integration/*.py` | Organized by test type |

## New Files to Create

| New Path | Purpose |
|----------|---------|
| `RAI_Chat/backend/__init__.py` | Package initialization with version |
| `RAI_Chat/backend/api/__init__.py` | API blueprint registration |
| `RAI_Chat/backend/api/auth.py` | Authentication endpoints (extracted from rai_api_server.py) |
| `RAI_Chat/backend/api/memory.py` | Memory endpoints (extracted from rai_api_server.py) |
| `RAI_Chat/backend/api/session.py` | Session management endpoints (extracted from rai_api_server.py) |
| `RAI_Chat/backend/extensions/__init__.py` | Flask extension initialization |
| `RAI_Chat/backend/extensions/cors.py` | CORS configuration |
| `RAI_Chat/backend/schemas/__init__.py` | Schema package initialization |
| `RAI_Chat/backend/schemas/auth.py` | Authentication schemas |
| `RAI_Chat/backend/schemas/chat.py` | Chat schemas |
| `RAI_Chat/backend/schemas/session.py` | Session schemas |
| `RAI_Chat/tests/conftest.py` | Test fixtures and configuration |

## Implementation Steps

1. **Create Directory Structure**:
   ```bash
   mkdir -p RAI_Chat/backend/{api,core/{auth,database,logging},services/memory,utils,extensions,modules/web_search,schemas,static,templates,migrations}
   mkdir -p RAI_Chat/scripts
   mkdir -p RAI_Chat/tests/{unit,integration}
   ```

2. **Create Package Initialization Files**:
   ```bash
   touch RAI_Chat/backend/__init__.py
   touch RAI_Chat/backend/api/__init__.py
   touch RAI_Chat/backend/core/{__init__.py,auth/__init__.py,database/__init__.py,logging/__init__.py}
   touch RAI_Chat/backend/services/{__init__.py,memory/__init__.py}
   touch RAI_Chat/backend/utils/__init__.py
   touch RAI_Chat/backend/extensions/__init__.py
   touch RAI_Chat/backend/modules/{__init__.py,web_search/__init__.py}
   touch RAI_Chat/backend/schemas/__init__.py
   touch RAI_Chat/tests/{__init__.py,unit/__init__.py,integration/__init__.py}
   ```

3. **Move Files**: Move each file to its new location according to the mapping.

4. **Update Imports**: Update import statements in each file to reflect the new structure.

5. **Create Application Factory**: Split the current `rai_api_server.py` into `app.py` (application factory) and `wsgi.py` (WSGI entry point).

6. **Update Launch Script**: Update the launch script to use the new structure.

7. **Test**: Test the application to ensure everything works as expected.

## Import Pattern Examples

### Application Factory (`app.py`):
```python
from flask import Flask
from .extensions import cors
from .api import auth_bp, chat_bp, memory_bp, session_bp
from .core.database.session import init_db

def create_app(config_object="backend.config.ProductionConfig"):
    app = Flask(__name__)
    app.config.from_object(config_object)
    
    # Initialize extensions
    cors.init_app(app)
    
    # Initialize database
    init_db(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(memory_bp, url_prefix="/api/memory")
    app.register_blueprint(session_bp, url_prefix="/api/session")
    
    return app
```

### API Blueprint (`api/chat.py`):
```python
from flask import Blueprint, request, jsonify, g
from ..core.auth.utils import token_required
from ..services.conversation import ConversationManager
from ..services.session import get_user_session_manager

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/", methods=["POST"])
@token_required
def chat():
    # Implementation
    pass
```

### Service Layer (`services/conversation.py`):
```python
from typing import Dict, List, Any, Optional, Generator
from ..core.database.session import SQLAlchemySession
from .memory.contextual import ContextualMemoryManager
from .memory.episodic import EpisodicMemoryManager
from .file_storage import ChatFileManager

class ConversationManager:
    # Implementation
    pass
```

### WSGI Entry Point (`wsgi.py`):
```python
from .app import create_app

app = create_app()

if __name__ == "__main__":
    import os
    from waitress import serve
    
    port = int(os.environ.get("RAI_API_PORT", 6102))
    serve(app, host="0.0.0.0", port=port, threads=8)
```
