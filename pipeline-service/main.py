import os
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import Base, DATABASE_URL, engine, get_db, reset_legacy_customer_table
from models.customer import Customer
from services.ingestion import check_mock_server_health, ingest_customers


MOCK_SERVER_URL = os.getenv("MOCK_SERVER_URL", "http://mock-server:5000")


@asynccontextmanager
async def lifespan(_: FastAPI):
    reset_legacy_customer_table()
    Base.metadata.create_all(bind=engine)
    print("Pipeline service started successfully.")
    yield


app = FastAPI(title="Customer Pipeline Service", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round(time.time() - start, 3)
    print(f"{request.method} {request.url} - {duration}s")
    return response


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/ingest")
def run_ingestion(db: Session = Depends(get_db)):
    try:
        check_mock_server_health(MOCK_SERVER_URL)
        records_processed, load_summary = ingest_customers(
            db, MOCK_SERVER_URL, DATABASE_URL
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "status": "success",
        "records_processed": records_processed,
        "load_summary": load_summary,
    }


@app.get("/api/customers")
def list_customers(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.scalar(select(func.count()).select_from(Customer)) or 0
    offset = (page - 1) * limit
    customers = db.scalars(
        select(Customer).order_by(Customer.customer_id).offset(offset).limit(limit)
    ).all()

    data = [
        {
            "customer_id": customer.customer_id,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "email": customer.email,
            "phone": customer.phone,
            "address": customer.address,
            "date_of_birth": customer.date_of_birth.isoformat()
            if customer.date_of_birth
            else None,
            "account_balance": float(customer.account_balance)
            if customer.account_balance is not None
            else None,
            "created_at": customer.created_at.isoformat()
            if customer.created_at
            else None,
        }
        for customer in customers
    ]

    return {"data": data, "total": total, "page": page, "limit": limit}


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "customer_id": customer.customer_id,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "email": customer.email,
        "phone": customer.phone,
        "address": customer.address,
        "date_of_birth": customer.date_of_birth.isoformat()
        if customer.date_of_birth
        else None,
        "account_balance": float(customer.account_balance)
        if customer.account_balance is not None
        else None,
        "created_at": customer.created_at.isoformat()
        if customer.created_at
        else None,
    }
