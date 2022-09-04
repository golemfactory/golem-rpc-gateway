import os
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.asyncio import create_async_engine

def get_postgres_connection_string():
    user = os.environ.get("POSTGRES_USER", "user")
    password = os.environ.get("POSTGRES_PASSWORD", "ICmDzTGZri")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "gateway")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def get_db_engine():
    db_type = os.environ.get("MONITOR_DB_ENGINE", "sqlite")
    if db_type == "sqlite":
        conn_string = os.environ.get('SQLITE_CONN_STRING', 'sqlite:///ethnode.sqlite')
        engine = create_engine(conn_string, echo=False, future=True)
    elif db_type == "postgres":
        conn_string = os.environ.get('POSTGRES_CONN_STRING', get_postgres_connection_string())
        engine = create_engine(conn_string, echo=False, future=True)
        if not database_exists(engine.url):
            create_database(engine.url)
    else:
        raise Exception(f"Unknown database type {db_type}")
    return engine


def get_async_db_engine():
    db_type = os.environ.get("MONITOR_DB_ENGINE", "sqlite")
    if db_type == "sqlite":
        conn_string = os.environ.get('SQLITE_CONN_STRING', 'sqlite+aiosqlite:///ethnode.sqlite')
        engine = create_async_engine(conn_string, echo=False, future=True)
    elif db_type == "postgres":
        conn_string = os.environ.get('POSTGRES_CONN_STRING', get_postgres_connection_string())
        engine = create_async_engine(conn_string, echo=False, future=True)
        if not database_exists(engine.url):
            create_database(engine.url)
    else:
        raise Exception(f"Unknown database type {db_type}")
    return engine


db_engine = get_db_engine()
# db_async_engine = get_async_db_engine()
