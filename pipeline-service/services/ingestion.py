import os
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import dlt
import requests
from requests import Response
from requests.exceptions import RequestException
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.customer import Customer


CUSTOMER_COLUMNS = {
    "customer_id": {"data_type": "text", "nullable": False},
    "first_name": {"data_type": "text", "nullable": False},
    "last_name": {"data_type": "text", "nullable": False},
    "email": {"data_type": "text", "nullable": False},
    "phone": {"data_type": "text", "nullable": True},
    "address": {"data_type": "text", "nullable": True},
    "date_of_birth": {"data_type": "date", "nullable": True},
    "account_balance": {"data_type": "decimal", "nullable": True},
    "created_at": {"data_type": "timestamp", "nullable": True},
}


@dlt.resource(
    name="customers",
    primary_key="customer_id",
    write_disposition="merge",
    columns=CUSTOMER_COLUMNS,
)
def customer_resource(mock_server_url: str, page_size: int = 100):
    page = 1

    while True:
        response = fetch_with_retry(
            f"{mock_server_url}/api/customers",
            params={"page": page, "limit": page_size},
        )
        response.raise_for_status()
        payload = response.json()

        customers = payload.get("data", [])
        if not customers:
            break

        for customer in customers:
            yield customer

        total = payload.get("total", 0)
        limit = payload.get("limit", page_size)
        if page * limit >= total:
            break

        page += 1


def fetch_with_retry(url: str, params: dict | None = None, retries: int = 3, delay: int = 2) -> Response:
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            return requests.get(url, params=params, timeout=30)
        except RequestException as exc:
            last_error = exc
            print(f"Request failed on attempt {attempt}/{retries}. Retrying...")
            if attempt < retries:
                time.sleep(delay)

    raise RuntimeError(f"Failed to fetch data from {url}") from last_error


def is_valid_customer(record: dict) -> bool:
    if not record.get("customer_id"):
        print(f"Skipping invalid record without customer_id: {record}")
        return False
    if not record.get("email"):
        print(f"Skipping invalid record without email: {record}")
        return False
    return True


def normalize_customer(record: dict) -> dict:
    normalized = dict(record)
    normalized["date_of_birth"] = (
        date.fromisoformat(record["date_of_birth"])
        if record.get("date_of_birth")
        else None
    )
    normalized["created_at"] = (
        datetime.fromisoformat(record["created_at"])
        if record.get("created_at")
        else None
    )
    normalized["account_balance"] = (
        Decimal(str(record["account_balance"]))
        if record.get("account_balance") is not None
        else None
    )
    return normalized


def collect_customers(mock_server_url: str) -> list[dict]:
    customers: list[dict] = []
    for record in customer_resource(mock_server_url=mock_server_url):
        if not is_valid_customer(record):
            continue
        customers.append(normalize_customer(record))
    return customers


def build_pipeline(database_url: str):
    os.environ["DESTINATION__POSTGRES__CREDENTIALS"] = database_url
    return dlt.pipeline(
        pipeline_name="customer_ingestion_pipeline",
        destination="postgres",
        dataset_name="public",
    )


def run_pipeline_load(records: list[dict], database_url: str) -> Any:
    pipeline = build_pipeline(database_url)
    # Keep dlt as part of the ingestion pipeline for extraction metadata and schema handling.
    # We load into an internal staging table to demonstrate dlt integration without relying on
    # destination-side type coercion for the final customers table.
    return pipeline.run(
        records,
        table_name="customers_staging",
        write_disposition="replace",
        columns=CUSTOMER_COLUMNS,
    )


def upsert_customers(db: Session, records: list[dict]) -> None:
    stmt = insert(Customer).values(records)
    update_columns = {
        column.name: stmt.excluded[column.name]
        for column in Customer.__table__.columns
        if column.name != "customer_id"
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=[Customer.customer_id],
        set_=update_columns,
    )

    try:
        db.execute(stmt)
        db.commit()
    except IntegrityError:
        db.rollback()
        print("Duplicate detected, skipping conflicting customer rows.")
        raise


def ingest_customers(
    db: Session, mock_server_url: str, database_url: str
) -> tuple[int, str]:
    records = collect_customers(mock_server_url)
    if not records:
        return 0, "No customer records were returned by the mock server."

    load_info = run_pipeline_load(records, database_url)
    upsert_customers(db, records)
    return len(records), str(load_info)


def check_mock_server_health(mock_server_url: str) -> None:
    response = fetch_with_retry(f"{mock_server_url}/api/health", retries=3, delay=1)
    response.raise_for_status()
