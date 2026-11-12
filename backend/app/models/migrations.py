"""Ordered additive migrations. Never reset a user's existing database."""
from sqlalchemy import text

LATEST = 1


def migrate(engine):
    from app.models.database import Base
    import app.models.entities  # register tables
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE IF NOT EXISTS schema_versions (version INTEGER PRIMARY KEY)'))
        versions = set(connection.execute(text('SELECT version FROM schema_versions')).scalars())
        if versions and max(versions) > LATEST:
            raise RuntimeError('Database schema is newer than this application; restore compatible code')
        if 1 not in versions:
            # v1 adds accounts, audit history, quotas and question ownership.
            # Existing tables/columns are not rewritten; all new schema is additive.
            Base.metadata.create_all(connection)
            connection.execute(text('INSERT INTO schema_versions(version) VALUES (1)'))
