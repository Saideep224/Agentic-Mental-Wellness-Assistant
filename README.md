# 🌊 Esona - Your Supporting Buddie

An AI-powered multi-agent mental wellness chatbot that understands your personality, emotions, and communication style to provide truly personalized, human-like emotional support.

![Esona](https://img.shields.io/badge/Esona-Mental%20Wellness-0ea5e9?style=for-the-badge)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi%20Agent-8b5cf6?style=for-the-badge)

## ✨ Features

- **Multi-Agent AI Architecture** — 7 specialized agents collaborating for every response
- **Personality Profiling** — 20-question onboarding to understand who you are
- **Emotional Memory** — Remembers your emotional patterns and history
- **Adaptive Tone** — Adjusts communication style to match your preferences
- **Mood Analytics** — Beautiful dashboard with emotional trend visualization
- **Calming UI** — Japanese-inspired aesthetic with ambient animations

## 🏗️ Architecture

```
User Message → Router Agent → [Emotion, Personality, Context, Memory Agents]
                                              ↓
                              Recommendation Agent → Response Agent → Reply
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, TypeScript, TailwindCSS v4, Framer Motion, ShadCN UI |
| Backend | FastAPI (Python 3.11+) |
| AI | OpenAI GPT-4o, LangGraph |
| Database | PostgreSQL 16 |
| Memory | ChromaDB (vector embeddings) |
| Auth | Auth.js (NextAuth v5) |

## 📦 Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- PostgreSQL 16 (or Docker)
- OpenAI API key

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd esona
```

### 2. Start PostgreSQL

```bash
# Using Docker
docker-compose up -d

# Or use your local PostgreSQL instance
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OpenAI API key and database URL

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your settings

# Start development server
npm run dev
```

### 5. Open in Browser

Navigate to `http://localhost:3000`

## 🔐 Environment Variables

### Backend (`backend/.env`)
```env
DATABASE_URL=postgresql+asyncpg://esona:esona_dev_2026@localhost:5432/esona
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4o
CHROMA_PERSIST_DIR=./chroma_data
JWT_SECRET=your-secure-jwt-secret-key
FRONTEND_URL=http://localhost:3000
```

### Frontend (`frontend/.env.local`)
```env
NEXTAUTH_SECRET=your-nextauth-secret-key
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## 📁 Project Structure

```
esona/
├── frontend/          # Next.js 15 application
│   ├── src/
│   │   ├── app/       # Pages (landing, onboarding, chat, dashboard)
│   │   ├── components/ # React components
│   │   ├── hooks/     # Custom hooks
│   │   ├── lib/       # Utilities and config
│   │   └── providers/ # Context providers
│   └── public/        # Static assets
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── agents/    # LangGraph multi-agent system
│   │   ├── memory/    # ChromaDB vector memory
│   │   ├── models/    # SQLAlchemy models
│   │   ├── routers/   # API endpoints
│   │   ├── schemas/   # Pydantic schemas
│   │   └── services/  # Business logic
│   └── alembic/       # Database migrations
├── docker-compose.yml # PostgreSQL setup
└── README.md
```

## 🤖 Agent System

| Agent | Role |
|-------|------|
| **Router** | Decides which agents to activate per message |
| **Emotion** | Stress analysis, mood classification, burnout detection |
| **Personality** | Overthinking detection, communication style analysis |
| **Context** | Emotional trigger identification, deeper meaning detection |
| **Memory** | Emotional history retrieval, pattern recognition |
| **Recommendation** | Calming suggestions, adaptive coping strategies |
| **Response** | Synthesizes all agents into natural, human-like reply |

## 📄 License

MIT License — feel free to use, modify, and share.

---

*Built with 💙 for emotional wellbeing*
