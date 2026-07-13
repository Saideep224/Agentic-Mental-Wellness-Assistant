"""
Custom SQLAlchemy type decorators for the Esona database.
"""

import uuid
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

class SafeUUID(TypeDecorator):
    """
    A platform-independent UUID type.
    Uses PostgreSQL's UUID type when on PostgreSQL,
    otherwise uses CHAR(36) for SQLite.
    
    Accepts string UUIDs or uuid.UUID objects transparently.
    Always returns uuid.UUID objects to the application for consistency.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        
        # Normalize to uuid.UUID object if postgresql, or string if SQLite
        if dialect.name == 'postgresql':
            if isinstance(value, uuid.UUID):
                return value
            try:
                return uuid.UUID(str(value))
            except ValueError:
                return None
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except ValueError:
            return value
