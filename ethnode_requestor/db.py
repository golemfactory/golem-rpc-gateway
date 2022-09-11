import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


def get_postgres_connection_string(is_async=False):
    user = os.environ.get("POSTGRES_USER", "dev")
    password = os.environ.get("POSTGRES_PASSWORD", "dev_pass")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "dev")
    if is_async:
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
    else:
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def get_db_engine(is_async=False):
    db_type = os.environ.get("MONITOR_DB_ENGINE", "sqlite")
    if db_type == "sqlite":
        if is_async:
            conn_string = os.environ.get('SQLITE_CONN_STRING', 'sqlite+aiosqlite:///ethnode.sqlite')
            engine = create_async_engine(conn_string, echo=False, future=True)
        else:
            conn_string = os.environ.get('SQLITE_CONN_STRING', 'sqlite:///ethnode.sqlite')
            engine = create_engine(conn_string, echo=False, future=True)

    elif db_type == "postgres":
        conn_string = os.environ.get('POSTGRES_CONN_STRING', get_postgres_connection_string(is_async=is_async))
        if is_async:
            engine = create_async_engine(conn_string, echo=False, future=True)
        else:
            engine = create_engine(conn_string, echo=False, future=True)
            if not database_exists(engine.url):
                create_database(engine.url)
    else:
        raise Exception(f"Unknown database type {db_type}")
    return engine


db_engine = get_db_engine()
db_async_engine = get_db_engine(is_async=True)
async_session = sessionmaker(
    db_async_engine, expire_on_commit=False, class_=AsyncSession
)

