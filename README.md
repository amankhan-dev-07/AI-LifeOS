# AI-LifeOS

An AI-powered personal productivity and finance platform that integrates tasks, goals, habits, planning, and finance into a unified, user-scoped LifeOS.

## What is AI-LifeOS?

AI-LifeOS is an intelligent, self-hosted productivity ecosystem designed to manage your entire digital life in one secure place. By combining structured data management (SQL-backed) with a natural language command interface, it allows you to query, create, and manage your tasks, finances, and schedule without leaving the terminal-like efficiency of the AI Command Center.

## Why AI-LifeOS?

Managing productivity often leads to fragmented workflows across multiple applications—one for tasks, one for notes, one for finances, and a calendar for scheduling. AI-LifeOS solves this by providing a unified, unified platform that treats your life data as an interconnected system, ensuring that your goals, habits, and tasks all feed into a single, cohesive view of your productivity.

## Core Modules

| Module | Description |
| :--- | :--- |
| **Tasks** | Manage day-to-day to-dos with priorities, due dates, and completion tracking. |
| **Goals** | Track long-term progress across categories like career, health, or education. |
| **Habits** | Build consistency with daily, weekly, or monthly habits and streak monitoring. |
| **Planner** | An intelligent scheduler for time-blocking tasks and habits. |
| **Notes** | Keep quick thoughts and information tagged and organized. |
| **Finance** | Track income and expenses with categorical insights. |
| **Reminders** | Set time-bound prompts for critical actions. |
| **Global Search** | Find information across all your LifeOS data. |
| **LifeOS Intelligence** | Get a deterministic overview of your current productivity status. |
| **AI Command Center** | Natural language interface for executing LifeOS operations. |

## AI Command Center

The AI Command Center allows you to manage your LifeOS using natural language. It supports:
- **Deterministic Intent Classification**: Translates free-text commands into structured actions.
- **Action Planning**: Proposes safe, multi-step action plans before execution.
- **Confirmation**: Sensitive operations (deletions, financial writes) are gated behind explicit confirmation.
- **Error Handling**: Provides specific, actionable clarification when commands are ambiguous or lack required information.

## LifeOS Intelligence

The Intelligence layer provides a deterministic summary of your current productivity state. By aggregating tasks, habit streaks, and financial data, it offers an authoritative briefing on your overall progress, completely independent of external LLM availability.

## Security

- **User-Scoped Data**: Every record is strictly bound to the authenticated user ID.
- **Isolation**: Multi-user isolation is enforced at the database query level; users cannot read, update, or delete records belonging to others.
- **Protected Actions**: Destructive operations require explicit user confirmation.

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python 3.10, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL |
| **Auth** | JWT bearer tokens, bcrypt password hashing |
| **Frontend** | React 18, TypeScript, Vite, Tailwind, React Router |

## Architecture

```text
User Request → FastAPI Endpoint → Orchestration Service → Domain Service → PostgreSQL
                                       ↓
                                 Intent Service (Deterministic/Local LLM)
```

## Project Structure

```text
backend/     FastAPI app (app/), Alembic migrations (alembic/), requirements.txt
frontend/    React + Vite client
docs/        Production deployment guide
docker/      Docker configuration
scripts/     Management scripts
README.md    Documentation
```

## Getting Started

### Local Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate # or .venv/Scripts/activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Set SECRET_KEY and DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload
```

### Local Frontend
```bash
cd frontend
npm ci
npm run dev
```

### Docker Compose
```bash
cp .env.example .env
# Set SECRET_KEY and POSTGRES_PASSWORD
docker compose build
docker compose up -d
docker compose run --rm migrate
```

## Environment Variables

The project uses `.env` files for configuration.
- `/.env`: Used by Docker Compose.
- `/backend/.env`: Used when running the backend directly.

**WARNING:** Never commit these files to version control. They contain sensitive credentials (e.g., `SECRET_KEY`, `DATABASE_URL`).

## Testing

The codebase maintains a robust suite of tests covering core domains, AI orchestration, security, and edge cases. As of Phase 14, major core functionality is verified.

## Screenshots

*Placeholders for product screenshots will be added here.*

## Performance

The frontend is built with React and Vite for a lightweight, responsive user experience, while the backend leverages FastAPI for high-performance, asynchronous request handling.

## Product Status

Core major development is complete. Future work is focused on maintenance, production deployment refinement, security hardening, and incremental performance improvements.

## Roadmap

- Deployment automation.
- Enhanced AI Command Center phrasings.
- Extended intelligence insights.
- Performance optimization for large datasets.

## License

This project is proprietary.

## Vision

To provide a private, self-hosted, and intelligent foundation for managing personal productivity, bridging the gap between raw data and meaningful life management.
