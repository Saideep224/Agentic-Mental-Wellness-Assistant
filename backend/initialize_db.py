import asyncio
import os
from sqlalchemy import inspect
from app.database import engine, Base
# Import models to register them with Base
from app.models import User, Conversation, Message, EmotionalProfile, OnboardingResponse

async def main():
    # Retrieve the database path from connection URL
    # SQLite URL looks like: sqlite+aiosqlite:///./esona.db
    # We can parse the filename or just check the default `./esona.db`
    db_path = "./esona.db"
    if os.path.exists(db_path):
        print(f"Removing existing database at {db_path}...")
        try:
            os.remove(db_path)
            print("Database removed successfully.")
        except Exception as e:
            print(f"Error removing database: {e}")
            
    print("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables initialized successfully.")

    # Verify tables
    print("Verifying tables...")
    async with engine.connect() as conn:
        def get_tables(connection):
            inspector = inspect(connection)
            return inspector.get_table_names()
        
        tables = await conn.run_sync(get_tables)
        print("Tables in database:", tables)
        
        expected_tables = {"users", "conversations", "messages", "emotional_profiles", "onboarding_responses"}
        missing_tables = expected_tables - set(tables)
        if not missing_tables:
            print("SUCCESS: All tables created successfully!")
        else:
            print(f"ERROR: Missing tables: {missing_tables}")

if __name__ == "__main__":
    asyncio.run(main())
