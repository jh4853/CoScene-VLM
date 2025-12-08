# CoScene Backend

Agentic 3D Scene Editing System using LangGraph and Vision-Language Models.

## Project Overview

This backend enables conversational 3D scene editing through natural language prompts. It uses:
- **FastAPI** for REST and WebSocket APIs
- **LangGraph** for agent orchestration
- **Claude 3.5 Sonnet** for USD generation and scene understanding
- **Blender** for headless 3D rendering
- **PostgreSQL** for persistent storage

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 16
- Redis 7
- Blender 4.0+ (for rendering service)
- Docker & Docker Compose (for containerized deployment)

### Installation

1. Clone the repository:
```bash
cd coscene-backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
psql -U postgres -f scripts/init_db.sql
alembic upgrade head
```

### Running Locally

Start the API server:
```bash
uvicorn api.main:app --reload --port 8000
```

API will be available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Running with Docker

```bash
docker-compose up --build
```

## Project Structure

```
coscene-backend/
├── api/                    # FastAPI application
│   ├── main.py            # Application entry point
│   ├── models.py          # Pydantic models
│   └── routes/            # API routes
│       ├── sessions.py    # Session management
│       ├── scenes.py      # Scene editing
│       └── websocket.py   # WebSocket handlers
├── agents/                # LangGraph agents
│   ├── scene_editor.py    # Main agent workflow
│   └── prompts.py         # VLM prompt templates
├── services/              # Business logic
│   ├── storage.py         # Database operations
│   ├── usd_service.py     # USD manipulation
│   └── render_service.py  # Blender integration
├── docker/                # Docker configurations
│   ├── Dockerfile.api
│   ├── Dockerfile.render
│   └── docker-compose.yml
└── scripts/               # Utility scripts
    ├── blender_render.py  # Blender rendering script
    └── init_db.sql        # Database schema
```

## API Endpoints

### Session Management
- `POST /sessions` - Create new editing session
- `GET /sessions/{id}` - Get session details
- `DELETE /sessions/{id}` - End session

### Scene Editing
- `POST /sessions/{id}/edit` - Process scene edit
- `GET /sessions/{id}/scene` - Download USD scene
- `GET /renders/{id}` - Get render image

### WebSocket
- `WS /ws/{session_id}` - Real-time updates

See full API documentation at `/docs` when running the server.

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
ruff check .
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Contributing

See `IMPLEMENTATION_PLAN.md` for detailed development plan.
