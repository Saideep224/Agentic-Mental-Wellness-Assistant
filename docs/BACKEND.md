# Backend Architecture

The Esona backend is built on **FastAPI** using asynchronous Python, structured logically into routes, schemas, models, services, and cognitive agents.

## Directory Breakdown

- **`app/main.py`**: Boots the FastAPI instance, hooks up CORS middleware, registers routers, and binds global exception handlers.
- **`app/config.py`**: Loads system configurations from `.env` using Pydantic Settings. Manages model selection keys, JWT secrets, and DB connection checks.
- **`app/database.py`**: Defines the SQLAlchemy database connection engine. Implements `SafeUUID` (handling Postgres `UUID` vs SQLite `CHAR(36)` type translation) and exposes the `get_db` session dependency.
- **`app/models/`**:
  - `user.py`: Declares the `User` class mapping to the `profiles` table.
  - `onboarding.py`: Maps responses to individual questions (`user_question_answers` table).
  - `conversation.py` & `message.py`: Maps chat history (`conversations` and `chat_messages` tables).
  - `memory.py`: Maps long-term memories (`memories` table).
  - `mood_log.py` & `emotion_log.py`: Maps daily logs (`mood_logs` and `emotion_logs` tables).
  - `user_graph.py` & `knowledge_graph.py`: Maps entities and relationships.
- **`app/routes/`**:
  - `auth.py`: Handles token verification and user profile auto-creation on login.
  - `chat.py`: Exposes REST endpoints for managing conversations and the main Server-Sent Events (SSE) chat stream.
  - `onboarding.py`: Live-saves questionnaire responses and executes background profiling.
  - `dashboard.py` & `insights.py`: Generates personal emotional analytics, stress trends, and growth goals.
- **`app/services/`**: Exposes singleton objects for specific domain logic (e.g. `mentalbert_service`, `memory_service`, `knowledge_graph_service`, `profile_service`).
- **`app/agents/`**: Holds logical processing nodes representing modular steps in the cognitive pipeline.
- **`app/chatbot/`**: Configures the state and LangGraph graph workflow.

---

## FastAPI Routes & APIs

| Route | Method | Description |
| :--- | :--- | :--- |
| `/api/auth/me` | GET | Retrieve/auto-create the active user's profile. |
| `/api/auth/supabase-login` | POST | Supabase OAuth bridge profile builder. |
| `/api/chat/conversations` | GET | List conversations for the logged-in user. |
| `/api/chat/conversations` | POST | Create a new conversation thread. |
| `/api/chat/conversations/{id}` | DELETE | Delete a conversation thread. |
| `/api/chat/stream` | GET | Server-Sent Events (SSE) chat response generator. |
| `/api/onboarding/status` | GET | Check onboarding completion percentage and answers. |
| `/api/onboarding/answer` | POST | Live-save an individual onboarding response to database. |
| `/api/onboarding/submit` | POST | Submit final answers and trigger async profile builder. |
| `/api/dashboard/growth-insights` | GET | Retrieve coping strategies, challenges, and growth goals. |
| `/api/dashboard/mood-trends` | GET | Retrieve aggregated mood, stress, and anxiety history. |
