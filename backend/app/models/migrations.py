"""Ordered additive migrations. Never reset a user's existing database."""
from sqlalchemy import inspect, text

LATEST = 2


def migrate(engine):
    from app.models.database import Base
    from app.models.entities import RegistrationInvitation
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(2144139071)"))
        elif engine.dialect.name == "sqlite":
            connection.execute(text("BEGIN IMMEDIATE"))
        connection.execute(text('CREATE TABLE IF NOT EXISTS schema_versions (version INTEGER PRIMARY KEY)'))
        versions = set(connection.execute(text('SELECT version FROM schema_versions')).scalars())
        if versions not in (set(), {1}, {1, 2}):
            raise RuntimeError('Unrecognized schema version history. Use compatible application code.')
        if 1 not in versions:
            Base.metadata.create_all(connection)
            connection.execute(text('INSERT INTO schema_versions(version) VALUES (1)'))
        if 2 not in versions:
            RegistrationInvitation.__table__.create(connection, checkfirst=True)
            columns = {column["name"] for column in inspect(connection).get_columns("correction_reports")}
            if "publication_consent" not in columns:
                connection.execute(text(
                    "ALTER TABLE correction_reports ADD COLUMN publication_consent BOOLEAN NOT NULL DEFAULT FALSE"
                ))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS bb_users_username ON users (username)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS bb_attempt_history ON practice_attempts (user_id, created_at, id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS bb_report_history ON correction_reports (user_id, created_at, id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS bb_activity_time ON learning_activities (user_id, created_at)"))
            if engine.dialect.name == "postgresql":
                connection.execute(text("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"))
                connection.execute(text(
                    "SELECT setval(sequence_name, greatest(nextval(sequence_name), max_id)) "
                    "FROM (SELECT pg_get_serial_sequence('users','id')::regclass AS sequence_name, "
                    "(SELECT max(id) FROM users) AS max_id) s WHERE max_id IS NOT NULL"
                ))
            connection.execute(text('INSERT INTO schema_versions(version) VALUES (2)'))
        verify_schema(connection, Base.metadata)


def verify_schema(connection, metadata):
    schema = inspect(connection)
    for table in metadata.sorted_tables:
        if not schema.has_table(table.name):
            raise RuntimeError(f"Database schema is missing table {table.name}")
        actual = {column["name"] for column in schema.get_columns(table.name)}
        missing = set(table.columns.keys()) - actual
        if missing:
            raise RuntimeError(f"Database table {table.name} is missing columns {', '.join(sorted(missing))}")


def is_current(connection):
    versions = set(connection.execute(text("SELECT version FROM schema_versions")).scalars())
    return versions == set(range(1, LATEST + 1))
