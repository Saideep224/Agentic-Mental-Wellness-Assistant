# Database Schema & Persistence

Esona implements a dual-mode database layer mapping Python objects to both local developmental databases and cloud production instances:

```
SQLite (Local Dev Mode)  <-- [ SQLAlchemy ORM ] -->  PostgreSQL (Supabase Production)
```

## Key Database Tables

### 1. `profiles`
Represents the user account, settings, and generated personality profile.
- `user_id` (UUID, Primary Key): Matches Supabase Auth user ID.
- `id` (UUID, Unique): Matches the profiles table row key.
- `email` (Text, Unique): User's primary email.
- `full_name` (Text): Display name.
- `onboarding_completed` (Boolean): Global onboarding status flag.
- `personality_profile` (JSON): Derived traits (reply length, communication style, humor preference, stress patterns).

### 2. `user_question_answers`
Stores answers to the onboarding questionnaire.
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key → `profiles.user_id`)
- `question_id` (Integer): Index (1 to 27)
- `question_text` (Text)
- `category` (Text): Category name (personality, background, etc.)
- `selected_answer` (JSON): Array of selected options.
- `custom_answer` (Text, Nullable): Text inputs for "other" options.

### 3. `conversations` & `chat_messages`
Stores chat history threads.
- `conversations.id` (UUID, Primary Key)
- `conversations.user_id` (UUID, Foreign Key)
- `conversations.emotional_tag` (Text): Poetic sentiment representing the chat category.
- `chat_messages.id` (UUID, Primary Key)
- `chat_messages.conversation_id` (UUID, Foreign Key)
- `chat_messages.role` (Text): `"user"` or `"assistant"`.
- `chat_messages.content` (Text): Body text.
- `chat_messages.emotion` (Text): Categorized emotion flag.

### 4. `memories`
Stores extracted facts and behavioral observations.
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key)
- `memory_summary` (Text): Clear textual summary of the observation.
- `behavior_patterns` (JSON): Behavioral patterns dictionary.
- `memory_type` (Text): `"preference"`, `"relationship"`, or `"stress_trigger"`.

### 5. `mood_logs` & `emotion_logs`
Tracks daily statistics for dashboard trends.
- `mood_logs.mood_score` (Float): Numerical score (0.0 to 1.0) derived from user messages.
- `mood_logs.detected_emotion` (Text): Primary emotion.
- `mood_logs.stress` (Float): Normalized stress probability (0.0 to 1.0).
- `mood_logs.anxiety` (Float): Normalized anxiety probability (0.0 to 1.0).

---

## PostgreSQL & SQLite Compatibility Layer

The database connection employs several strategies to ensure cross-platform compatibility:
1. **`SafeUUID` Decorator**: Translates PostgreSQL's native `UUID` types to simple `CHAR(36)` fields when running on SQLite, maintaining data format consistency.
2. **SQLite WAL setup**: During local SQLite development, writes are optimized by automatically setting `PRAGMA journal_mode=WAL;` and `PRAGMA synchronous=NORMAL;` to prevent database locks.
3. **Transaction pooler compatibility**: Configures connection parameters to use `prepared_statement_cache_size=0` in Postgres, which is required for Supabase's transaction pooler (port 6543).
