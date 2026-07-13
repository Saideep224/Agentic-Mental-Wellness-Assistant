# Esona Repository Cleanup & Architecture Audit

This document inventories the files in the repository, classifies them by status, and provides the verification details for removing legacy or duplicate files.

## 1. Files Proposed for Deletion

The following 27 files are proposed for deletion from the repository as they are confirmed dead, redundant, or generated debug output:

| File Path | Classification | Verification / Reason for Deletion |
| :--- | :--- | :--- |
| `backend/app/services/ai_router.py` | LEGACY | Old specialist agent router from Esona V1. Verified no active imports or routes depend on it (Esona V2 uses the unified LangGraph chatbot pipeline). |
| `backend/app/services/specialist_service.py` | LEGACY | Base specialist service containing legacy model routing functions. Unused in V2. |
| `backend/app/services/doctor_service.py` | LEGACY | Old medical/doctor specialist agent service. Unused in V2. |
| `backend/app/services/finance_service.py` | LEGACY | Old financial specialist agent service. Unused in V2. |
| `backend/app/services/fitness_service.py` | LEGACY | Old fitness specialist agent service. Unused in V2. |
| `backend/app/services/lawyer_service.py` | LEGACY | Old legal specialist agent service. Unused in V2. |
| `backend/app/services/mentor_service.py` | LEGACY | Old academic mentor specialist agent service. Unused in V2. |
| `backend/app/services/relationship_service.py` | LEGACY | Old relationship coach specialist agent service. Unused in V2. |
| `backend/app/services/tech_service.py` | LEGACY | Old technical support specialist agent service. Unused in V2. |
| `backend/app/agents/specialist_registry.py` | LEGACY | System prompts and configs for the legacy specialist agents. Unused in V2. |
| `backend/app/future_ai/embeddings_fine_tune.py` | LEGACY | Experimental script for embeddings fine-tuning. Never imported or called. |
| `backend/app/future_ai/personalized_ai_profile.py` | LEGACY | Experimental personalization class. Dead code. |
| `backend/app/future_ai/rag_vector_db.py` | LEGACY | Experimental ChromaDB/vector RAG setup. Never used. |
| `backend/app/future_ai/voice_emotion_analyzer.py` | LEGACY | Experimental audio feature analysis model script. Unused. |
| `backend/app/future_ai/__init__.py` | LEGACY | Empty package initializer for legacy `future_ai` directory. |
| `frontend/src/components/landing/HeroSection.tsx` | LEGACY | Old static landing page hero layout. Homepage now uses `CinematicHome`. |
| `frontend/src/components/landing/FeatureCards.tsx` | LEGACY | Old landing page feature component. Unused. |
| `frontend/src/components/landing/CTASection.tsx` | LEGACY | Old landing page call-to-action banner. Unused. |
| `frontend/src/components/landing/EsonaGetStartedButton.tsx` | LEGACY | Old static button layout. Unused. |
| `frontend/src/components/landing/InteractiveTorch.tsx` | LEGACY | Old landing page torchlight background card effect. Unused. |
| `frontend/src/components/landing/InteractiveTorch.module.css` | LEGACY | CSS modules stylesheet for the old torch component. Unused. |
| `BG1.mp4` (root directory) | DUPLICATE | Duplicate of `frontend/public/BG1.mp4` (~36MB). |
| `Sunset.mp4` (root directory) | DUPLICATE | Duplicate of `frontend/public/BG2.mp4` (~78MB) representing sunset background. |
| `backend/render.yaml` | DUPLICATE | Redundant duplicate Render setup file. The master `render.yaml` in the root is used for deployments. |
| `backend/test_eval_output.txt` | GENERATED | Evaluation printouts accidentally tracked in Git. |
| `backend/test_eval_output2.txt` | GENERATED | Evaluation printouts accidentally tracked in Git. |
| `backend/test_eval_output3.txt` | GENERATED | Evaluation printouts accidentally tracked in Git. |

---

## 2. Suspicious Files That Are PRESERVED

The following files are preserved as they are active and necessary for local execution, fallback modes, or documentation:

1. **`backend/initialize_db.py` (ACTIVE)**: Utility command to rebuild the local SQLite tables for dev environments.
2. **`backend/scripts/migrate_sqlite_to_postgres.py` (ACTIVE)**: Migration script used to transfer schema and rows from SQLite to Supabase Postgres.
3. **`backend/app/agents/graph.py` (LEGACY - PRESERVED)**: Serves as a backward-compatibility shim for imports pointing to `app.agents.graph` (redirects dynamically to `app.chatbot.pipeline`).
4. **`supabase/` migrations (DOCUMENTATION)**: Keeps the production database schema updates and record migrations documented (`supabase/*.sql`).

---

## 3. Dependencies Audit

- **Frontend (`package.json`)**: All 14 packages are directly imported and active in the React client. No packages proposed for removal.
- **Backend (`requirements.txt`)**: Pinning is kept intact. No packages proposed for removal. In particular, `asyncpg`, `aiosqlite`, `SQLAlchemy`, and `langgraph` are verified active.

---

## 4. Gitignore Adjustments Proposed
- Add rules to ignore log files (`*.log`), python cache files, local SQLite databases (`*.db`), and testing output (`test_eval_output*.txt`) if generated in future.

---

## 5. Final Proposed Repository Structure
```
Saideep224/Agentic-Mental-Wellness-Assistant/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── render.yaml               # Root deployment blueprint
├── docs/                     # Comprehensive architecture documentation
│   ├── CLEANUP_AUDIT.md
│   ├── ARCHITECTURE.md
│   ├── BACKEND.md
│   ├── FRONTEND.md
│   ├── DATABASE.md
│   ├── MENTALBERT.md
│   ├── KNOWLEDGE_GRAPH.md
│   ├── CHAT_PIPELINE.md
│   ├── ONBOARDING.md
│   └── DEPLOYMENT.md
├── backend/
│   ├── requirements.txt
│   ├── runtime.txt
│   ├── initialize_db.py
│   ├── scripts/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models/           # DB tables & model definitions
│       ├── schemas/          # Pydantic schemas
│       ├── routes/           # REST endpoints & SSE
│       ├── services/         # Logic layers (MentalBERT, memory, KG)
│       ├── agents/           # Logical cognitive agent files
│       ├── chatbot/          # LangGraph graph orchestration
│       └── utils/
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── app/              # Next.js pages (chat, dashboard, onboarding)
│   │   ├── components/       # UI components (chat, dashboard, layout)
│   │   ├── hooks/            # Custom hooks
│   │   ├── api/              # API clients & Supabase Sync
│   │   ├── providers/
│   │   ├── database/         # Supabase JS client
│   │   ├── styles/
│   │   └── utils/
│   └── public/               # Static assets (BG1.mp4, BG2.mp4, music, logo)
└── supabase/                 # Production SQL schemas
```
