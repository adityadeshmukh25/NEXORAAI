# NEXORA AI

### Your AI-Powered Software Engineering Workspace

NEXORA AI is an AI-powered software engineering workspace designed to help developers manage and streamline the software development lifecycle.

Built with **FastAPI, React, TypeScript, Tailwind CSS, SQLite, and Ollama**, NEXORA AI provides a foundation for an intelligent development environment that can progressively support requirement analysis, software architecture, code generation, validation, and automated code repair.

The project is being developed in multiple phases, with each phase introducing additional software engineering capabilities.

---

## Features — Phase 1

The initial release provides the core application foundation:

- **FastAPI Backend:** REST API for application operations.
- **React + TypeScript Frontend:** Interactive development dashboard.
- **Tailwind CSS:** Responsive user interface.
- **SQLite Database:** Local persistence for project information.
- **Ollama Integration:** Connects to locally hosted AI models.
- **Model Availability Checks:** Checks Ollama connectivity and installed models.
- **Project Management:** Create, view, list, and delete projects.
- **System Dashboard:** Displays backend, database, and Ollama connection status.

> **Note:** Phase 1 focuses on the core application foundation. Advanced autonomous code generation, agent orchestration, and restricted code execution are not enabled in this release.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, TypeScript |
| Styling | Tailwind CSS |
| Frontend Build Tool | Vite |
| Backend | Python, FastAPI |
| Database | SQLite |
| AI Integration | Ollama |
| Default AI Model | qwen2.5-coder:3b |
| API Documentation | Swagger UI |

---

## Prerequisites

Install the following before running NEXORA AI:

- Windows 10/11, macOS, or Linux
- Python 3.10 or later
- Node.js 20 or later
- npm
- Git
- Ollama

### Install Ollama

Download Ollama from:

https://ollama.com/download

After installation, open a terminal and execute:

```bash
ollama pull qwen2.5-coder:3b
```

Verify the installed model:

```bash
ollama list
```

Ollama normally runs locally at:

```text
http://localhost:11434
```

---

## Getting Started

Follow these steps to run NEXORA AI on your local machine.

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/nexora-ai.git
```

Navigate into the project:

```bash
cd nexora-ai
```

Replace `YOUR_USERNAME` with your GitHub username and `nexora-ai` with your actual repository name if different.

### 2. Configure the Backend

Navigate to the backend directory:

```bash
cd backend
```

Create a Python virtual environment:

**Windows PowerShell**

```powershell
py -3 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create your local environment configuration:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

Configure the environment variables in `backend/.env`:

```env
APP_NAME=NEXORA AI
API_HOST=127.0.0.1
API_PORT=8000
DATABASE_URL=sqlite:///./data/autonomous_ai_engineer.db
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:3b
FRONTEND_ORIGIN=http://localhost:5173
```

Start the backend from the `backend` directory:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend services:

- API: http://127.0.0.1:8000
- Swagger Documentation: http://127.0.0.1:8000/docs
- Health Check: http://127.0.0.1:8000/api/health

The SQLite database is created automatically when the application starts.

### 3. Configure the Frontend

Open a second terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create a local frontend environment file named `.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start the development server:

```bash
npm run dev
```

Open the application in your browser:

**http://localhost:5173**

---

## How NEXORA AI Works

Once the application is running, you can use its Phase 1 capabilities.

### Dashboard

The dashboard provides an overview of the application and its connected services.

It displays:

- Backend API status
- Database connectivity
- Ollama connection status
- Installed AI models
- Project information

### AI Model Connectivity

NEXORA AI connects to Ollama running locally on your machine.

The application checks whether Ollama is available and whether the configured model is installed.

The default model is:

```text
qwen2.5-coder:3b
```

### Project Management

The project management functionality allows you to:

- Create a new project.
- Add a project description.
- Specify the technology stack.
- View existing projects.
- Delete projects.

Project information is stored in the local SQLite database.

---

## API Endpoints

The following REST API endpoints are available in Phase 1.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Checks backend and database health |
| GET | `/api/ollama/status` | Checks Ollama connectivity and installed models |
| GET | `/api/projects` | Retrieves all projects |
| POST | `/api/projects` | Creates a new project |
| GET | `/api/projects/{project_id}` | Retrieves project details |
| DELETE | `/api/projects/{project_id}` | Deletes a project |

### Example Project Creation Request

```json
{
  "name": "Employee Management System",
  "description": "An employee management application with authentication and attendance.",
  "tech_stack": "FastAPI, React, SQLite"
}
```

---

## Configuration

NEXORA AI uses environment variables to configure its backend and frontend.

| Variable | Purpose |
|---|---|
| `APP_NAME` | Application name |
| `API_HOST` | Backend host address |
| `API_PORT` | Backend port |
| `DATABASE_URL` | SQLite database location |
| `OLLAMA_BASE_URL` | Ollama service address |
| `OLLAMA_MODEL` | AI model used by the application |
| `FRONTEND_ORIGIN` | Frontend origin allowed by the backend |
| `VITE_API_BASE_URL` | Backend API address used by the frontend |

Environment files are intended for local configuration and should not be committed to the public repository.

---

## Troubleshooting

### Ollama is disconnected

1. Make sure Ollama is installed and running.
2. Execute `ollama list`.
3. Confirm that `qwen2.5-coder:3b` is installed.
4. Check `OLLAMA_BASE_URL` in `backend/.env`.
5. Open `http://localhost:11434/api/tags` in your browser.

### Frontend cannot connect to the backend

1. Confirm that the backend is running on port `8000`.
2. Verify `VITE_API_BASE_URL` in `frontend/.env`.
3. Restart the Vite development server after modifying environment variables.

### Database issues

The SQLite database and its parent directory are created automatically by the backend when required.

If you encounter a database error, verify the database path and directory permissions.

---

## Development Roadmap

NEXORA AI is planned as a multi-phase software engineering platform.

| Phase | Planned Capability |
|---|---|
| Phase 1 | Core application foundation and project management |
| Phase 2 | Requirement analysis and structured project specifications |
| Phase 3 | AI planning and software architecture agents |
| Phase 4 | AI-powered code generation and workspace management |
| Phase 5 | Automated code review and static analysis |
| Phase 6 | Restricted execution, testing, debugging, and autonomous repair |
| Phase 7 | Agent activity streaming, history, and Git integration |
| Phase 8 | Documentation generation and project ZIP export |

*Roadmap items describe planned development and should not be interpreted as features already available in Phase 1.*

---

## Security and Privacy

NEXORA AI is designed to run locally during development.

Please follow these security practices:

- Never commit `.env` files.
- Never publish API keys, passwords, access tokens, or private credentials.
- Keep database files and local runtime data out of public repositories unless intentionally sanitized.
- Do not execute generated or untrusted code directly on your host machine.
- Use an isolated environment when testing generated code.
- Review configuration files before making the repository public.

The repository should contain example configuration files with placeholder values rather than real credentials.

---

## Project Structure

```text
NEXORA-AI/
│
├── backend/
│   ├── app/
│   ├── requirements.txt
│   ├── .env.example
│   └── data/
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── .env.example
│
├── .gitignore
└── README.md
```

*The structure above is a simplified overview. Actual files may vary as development progresses.*

---

## License

This project is distributed under the license specified in the repository. If no license has been added, all rights remain with the copyright holder; public availability on GitHub does not automatically grant permission to reuse the code.

---

## Author

Developed as an AI-powered software engineering project.

**NEXORA AI — Build Smarter. Ship Faster.**
