# 🌊 Esona — Agentic Mental Wellness Companion

Esona is an AI-powered mental wellness companion that dynamically adapts to your moods, preferences, and conversations. Rather than using single-prompt LLM generation, Esona orchestrates a multi-agent LangGraph cognitive workflow to deliver personalized, emotionally intelligent support.

---

## 🚀 Key Features

* **Multi-Agent Orchestration**: Utilizes cooperative agents (Safety, Emotion, Intent, Memory, Response) to process inputs and formulate replies.
* **Atmospheric Personalization**: Tailors language style, length, humor preference, and advice delivery based on a 27-question onboarding profile.
* **Long-Term Memory Manager**: Extracts personal preferences, relationships, and stress triggers into structured memories and summaries.
* **Persistent Knowledge Graph**: Constructs a directed relationship graph of user-mentioned entities, injecting relevant context back into prompts.
* **Wellness Analytics Dashboard**: Displays interactive mood trends, stress indicators, and customized coping recommendations.

---

## 🛠️ Technology Stack

* **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS, Framer Motion, Recharts
* **Backend**: FastAPI (Python), SQLAlchemy, LangGraph, Pydantic, uvicorn
* **Database**: Supabase (PostgreSQL production storage), aiosqlite (Local development fallback)
* **AI & Emotion**: OpenAI API, Gemini API, OpenRouter, and a MentalBERT lexical analyzer fallback.

---

## 📂 Repository Structure

```
.
├── docs/                     # Technical Architecture sub-documents
│   ├── ARCHITECTURE.md       # System workflow and folder layout
│   ├── BACKEND.md            # API routes, models, schemas, and directories
│   ├── FRONTEND.md           # Page routing, React components, and custom hooks
│   ├── DATABASE.md           # Database tables, PostgreSQL and SQLite layers
│   ├── MENTALBERT.md         # Emotion classifier pipeline and fallbacks
│   ├── KNOWLEDGE_GRAPH.md    # Graph entity extraction and injection
│   ├── CHAT_PIPELINE.md      # Multi-agent LangGraph workflow
│   ├── ONBOARDING.md         # 27-question Wizard and profile builders
│   └── DEPLOYMENT.md         # Environment configs, Render, and Vercel
├── backend/                  # FastAPI Application
├── frontend/                 # Next.js Application
├── supabase/                 # Database SQL migration scripts
└── docker-compose.yml        # Docker configuration for local services
```

---

## ⚙️ Local Development Setup

### 1. Backend Configuration
Navigate to the `backend/` directory, configure your `.env` file, and boot the API server:
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python initialize_db.py
uvicorn app.main:app --reload
```
Required Backend Environment Variables:
- `DATABASE_URL` (e.g. `sqlite+aiosqlite:///./esona.db`)
- `OPENAI_API_KEY`, `GEMINI_API_KEY`
- `JWT_SECRET`
- `FRONTEND_URL`

### 2. Frontend Configuration
Navigate to the `frontend/` directory, install packages, and boot the web dev server:
```bash
cd frontend
npm install
npm run dev
```
Required Frontend Environment Variables:
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL` (defaults to backend local address)

---

## 📘 Detailed Documentation
Please reference the files inside the [docs/](file:///e:/2026%20research%20intern/esona/docs) directory for full architectural specifications, services, models, and deployment configurations.

---

### Developed by
**Sai Deep**  
B.Tech Student, SRM University-AP  
*Research Initiative & Human-Centered AI Learning Platform*
