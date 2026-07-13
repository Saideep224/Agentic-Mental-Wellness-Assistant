# Deployment & Configuration

Esona is configured for automatic, Git-integrated deployment across Vercel, Render, and Supabase.

## Frontend (Vercel)
The Next.js client is deployed to Vercel:
- **Build Command**: `next build`
- **Output Directory**: `.next`
- **Root Directory**: `frontend`
- **Required Environment Variables**:
  - `NEXT_PUBLIC_SUPABASE_URL`: Active Supabase API URL.
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase client-safe anonymous key.
  - `NEXT_PUBLIC_API_URL`: URL of the Render API backend (e.g. `https://esona-api.onrender.com`).

---

## Backend (Render)
The FastAPI python app is deployed to Render:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
- **Root Directory**: `backend`
- **Configuration File**: Root [render.yaml](file:///e:/2026%20research%20intern/esona/render.yaml) defines the service properties.
- **Required Environment Variables**:
  - `DATABASE_URL`: Postgres connection string referencing Supabase (uses port 6543 pooler URL).
  - `JWT_SECRET`: Secret key for signing session tokens.
  - `OPENAI_API_KEY`: Key for GPT-4o-mini and text embeddings.
  - `GEMINI_API_KEY`: Key for Gemini model endpoints.
  - `FRONTEND_URL`: URL of the active Vercel frontend.

---

## Database (Supabase)
Production database persistence uses Supabase PostgreSQL:
- **SQL Migrations**: Schema structure can be created or updated using the scripts in `supabase/` (e.g. `supabase/esona_production_schema.sql`).
- **Connection Configuration**: Make sure connections to the database use the transaction pooler host with `prepared_statement_cache_size=0` enabled in SQLAlchemy connect parameters to avoid statement preparation errors.
