# Autonomous AI Engineer — Phase 1

A runnable Phase 1 foundation for an autonomous software engineering workspace.

## Included in Phase 1

- FastAPI backend
- React + TypeScript + Tailwind CSS frontend
- SQLite persistence
- Ollama connectivity and installed-model checks
- Project creation, listing, and deletion
- Dashboard showing backend, database, and Ollama status

> Code generation, agent orchestration, and restricted local execution are intentionally not enabled in Phase 1. They will be added in later phases. Do not execute generated or untrusted code directly on your host machine.

## Prerequisites

- Windows 10/11, macOS, or Linux
- Python 3.10+
- Node.js 20+
- npm
- Ollama installed and running

## 1. Configure Ollama

Install Ollama from https://ollama.com/download and start it.

In a terminal:

```bash
ollama pull qwen2.5-coder:3b
ollama list
```

The default model is `qwen2.5-coder:3b`. If your machine has 16 GB or more RAM, you can try `qwen2.5-coder:7b` by changing `OLLAMA_MODEL` in `backend/.env`.

Ollama normally listens on `http://localhost:11434`.

## 2. Start the backend

Open a terminal in the project root:

### Windows PowerShell

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 157.0.0.1 --port 8000
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend:
- API: http://127.0.0.1:8000
- Swagger docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health

SQLite database is created automatically at `backend/data/autonomous_ai_engineer.db`.

## 3. Start the frontend

Open a second terminal in the project root:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally http://localhost:5173.

## Configuration

Edit `backend/.env`:

```env
APP_NAME=Autonomous AI Engineer
API_HOST=157.0.0.1
API_PORT=8000
DATABASE_URL=sqlite:///./data/autonomous_ai_engineer.db
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:3b
FRONTEND_ORIGIN=http://localhost:5173
```

The database URL is resolved relative to the backend working directory. Start Uvicorn from the `backend` directory as shown above.

Frontend configuration is in `frontend/.env`:

```env
VITE_API_BASE_URL=http://157.0.0.1:8000
```

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Backend and database health |
| GET | `/api/ollama/status` | Ollama connectivity and installed models |
| GET | `/api/projects` | List projects |
| POST | `/api/projects` | Create a project |
| GET | `/api/projects/{project_id}` | Get project details |
| DELETE | `/api/projects/{project_id}` | Delete a project |

Example create request:

```json
{
  "name": "Employee Management System",
  "description": "An employee management application with authentication and attendance.",
  "tech_stack": "FastAPI, React, SQLite"
}
```

## Troubleshooting

### Ollama shows disconnected
1. Start Ollama.
2. Run `ollama list`.
3. Check `OLLAMA_BASE_URL` in `backend/.env`.
4. Open `http://localhost:11434/api/tags` in a browser.

### Frontend cannot reach backend
- Confirm FastAPI is running on port 8000.
- Confirm `frontend/.env` contains the correct `VITE_API_BASE_URL`.
- Restart the Vite development server after changing `.env`.

### SQLite database
The backend creates the `data` directory and database automatically on startup.

## Next phases

- Phase 2: requirement analysis and structured project specification
- Phase 3: planning and architecture agents with approval checkpoints
- Phase 4: code generation and workspace file management
- Phase 5: code review and static analysis
- Phase 6: isolated/restricted execution, testing, and repair loop
- Phase 7: agent activity streaming, history, and Git integration
- Phase 8: documentation and ZIP export
