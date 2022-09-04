import os
from sqlalchemy import create_engine


def get_db_engine():
    db_type = os.environ.get("MONITOR_DB_ENGINE", "sqlite")
    if db_type == "sqlite":
        conn_string = os.environ.get('SQLITE_CONN_STRING', 'sqlite:///ethnode.sqlite')
        engine = create_engine(conn_string, echo=False, future=True)
    elif db_type == "postgres":
        conn_string = os.environ.get('POSTGRES_CONN_STRING',
                                     'postgresql+psycopg2://user:ICmDzTGZri@localhost/folder-monitor')
        engine = create_engine(conn_string, echo=False, future=True)
    else:
        raise Exception(f"Unknown database type {db_type}")
    return engine


db_engine = get_db_engine()

