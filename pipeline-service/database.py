import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/customer_db",
)

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_legacy_customer_table() -> None:
    inspector = inspect(engine)
    if "customers" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("customers")}
    legacy_dlt_columns = {"_dlt_load_id", "_dlt_id"}

    if not legacy_dlt_columns.intersection(columns):
        return

    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS customers"))
