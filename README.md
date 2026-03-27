# Backend Developer Technical Assessment

Production-ready submission for the backend assessment. This project builds a three-service Dockerized data pipeline:

- `mock-server`: Flask API that serves customer data from a JSON file
- `pipeline-service`: FastAPI API that ingests data from Flask into PostgreSQL using `dlt`
- `postgres`: PostgreSQL 15 database for persistent storage

The complete flow is:

`customers.json` -> Flask mock API -> FastAPI ingestion endpoint -> `dlt` load -> PostgreSQL -> FastAPI query endpoints

## Tech Stack

- Python 3.11
- Flask
- FastAPI
- SQLAlchemy
- PostgreSQL 15
- `dlt` with Postgres destination
- Docker Compose

## Features

- JSON-backed mock customer service with 24 sample records
- Pagination support on both Flask and FastAPI APIs
- Single-customer lookup endpoints
- Health check endpoints for all services
- `dlt`-powered ingestion into PostgreSQL
- Idempotent merge/upsert behavior using `customer_id` as the primary key
- Docker Compose health checks to reduce startup race conditions
- Request logging middleware for FastAPI observability
- Retry logic for mock-server API calls
- Basic record validation before ingestion
- Email index on the customer table for lookup performance
- Environment-based configuration for deployability

## Project Structure

```text
.
|-- docker-compose.yml
|-- README.md
|-- mock-server
|   |-- app.py
|   |-- data
|   |   `-- customers.json
|   |-- Dockerfile
|   `-- requirements.txt
`-- pipeline-service
    |-- database.py
    |-- Dockerfile
    |-- main.py
    |-- requirements.txt
    |-- __init__.py
    |-- models
    |   |-- __init__.py
    |   `-- customer.py
    `-- services
        |-- __init__.py
        `-- ingestion.py
```

## API Overview

### Flask Mock Server

Base URL: `http://localhost:5000`

#### `GET /api/health`

Returns service health.

Example response:

```json
{
  "status": "ok"
}
```

#### `GET /api/customers?page=1&limit=10`

Returns paginated customers from the JSON dataset.

Example response:

```json
{
  "data": [
    {
      "customer_id": "CUST-001",
      "first_name": "Aarav",
      "last_name": "Sharma",
      "email": "aarav.sharma@example.com",
      "phone": "+1-555-0101",
      "address": "101 Maple Street, Austin, TX 78701",
      "date_of_birth": "1990-01-15",
      "account_balance": 1540.25,
      "created_at": "2024-01-05T10:15:00"
    }
  ],
  "total": 24,
  "page": 1,
  "limit": 10
}
```

#### `GET /api/customers/{customer_id}`

Returns a single customer or `404` if the customer does not exist.

### FastAPI Pipeline Service

Base URL: `http://localhost:8000`

#### `GET /api/health`

Returns service health.

#### `POST /api/ingest`

Fetches all customer pages from the Flask service and loads them into PostgreSQL using `dlt`.

Example response:

```json
{
  "status": "success",
  "records_processed": 24,
  "load_summary": "Pipeline customer_ingestion_pipeline load step completed ..."
}
```

#### `GET /api/customers?page=1&limit=10`

Returns paginated customers from PostgreSQL.

#### `GET /api/customers/{customer_id}`

Returns one customer row from PostgreSQL or `404`.

## How `dlt` Is Used

`dlt` is integrated inside [`pipeline-service/services/ingestion.py`](C:\Users\nites\Downloads\Amit Backend\pipeline-service\services\ingestion.py):

- `customer_resource(...)` is a `dlt.resource` that fetches customer data page by page from the Flask API
- `build_pipeline(...)` creates a `dlt` pipeline targeting the PostgreSQL destination
- `run_pipeline_load(...)` executes `pipeline.run(...)` with merge semantics
- `customer_id` is used as the primary key so repeated ingestions update existing rows instead of duplicating them

This means the ingestion endpoint is safe to call multiple times.

## Engineering Enhancements

The FastAPI service includes a few extra touches to make the submission feel more production-aware:

- Request logging middleware records method, URL, and request duration
- Retry logic handles transient Flask API/network failures
- Invalid records are skipped before load if required fields are missing
- Environment variables are used for database and service configuration
- A database index is defined on `email` to show performance awareness
- Startup logging confirms when the pipeline service is ready

## Prerequisites

Make sure these are installed before running the project:

- Docker Desktop
- Docker Compose

Optional for local non-Docker development:

- Python 3.10+
- Git

## Run The Project

From the project root:

```bash
docker compose up --build
```

If your machine uses the older Compose command, this also works:

```bash
docker-compose up --build
```

## Verify The Services

### 1. Test the Flask mock server

```bash
curl "http://localhost:5000/api/health"
curl "http://localhost:5000/api/customers?page=1&limit=5"
curl "http://localhost:5000/api/customers/CUST-001"
```

### 2. Trigger ingestion into PostgreSQL

```bash
curl -X POST "http://localhost:8000/api/ingest"
```

### 3. Query the ingested data from FastAPI

```bash
curl "http://localhost:8000/api/health"
curl "http://localhost:8000/api/customers?page=1&limit=5"
curl "http://localhost:8000/api/customers/CUST-001"
```

## Expected Behavior

- The Flask API always serves customer data from `mock-server/data/customers.json`
- The FastAPI ingestion endpoint automatically reads all pages from the Flask API
- PostgreSQL stores customer rows in the `public.customers` table
- Re-running ingestion updates existing rows instead of creating duplicates

## Docker Notes And Troubleshooting

### 1. `docker` or `docker-compose` command not found

Docker Desktop is not installed or not added to your system PATH. Start Docker Desktop first, then open a new terminal and re-run:

```bash
docker compose up --build
```

### 2. Containers start but FastAPI ingestion fails

The most common cause is startup timing. This project already includes Docker health checks for:

- PostgreSQL
- Flask mock server
- FastAPI service

If you still see errors, rebuild from scratch:

```bash
docker compose down -v
docker compose up --build
```

### 3. Port already in use

If ports `5000`, `5432`, or `8000` are already occupied, stop the conflicting service or change the mapped ports in [`docker-compose.yml`](C:\Users\nites\Downloads\Amit Backend\docker-compose.yml).

### 4. Ingestion endpoint returns a database error

Make sure PostgreSQL is healthy and the `DATABASE_URL` in [`docker-compose.yml`](C:\Users\nites\Downloads\Amit Backend\docker-compose.yml) matches the service credentials:

```yaml
DATABASE_URL: postgresql://postgres:password@postgres:5432/customer_db
```

### 5. Clean reset

If you want a fresh database:

```bash
docker compose down -v
docker compose up --build
```

## Submission Checklist

- [x] Flask mock server serves customer data from JSON
- [x] Pagination works on Flask and FastAPI endpoints
- [x] FastAPI ingests data from Flask into PostgreSQL
- [x] `dlt` integration is included in the ingestion pipeline
- [x] Docker Compose orchestrates all three services
- [x] README is included and copy-paste ready

## Quick Demo Commands

```bash
docker compose up --build
curl "http://localhost:5000/api/customers?page=1&limit=5"
curl -X POST "http://localhost:8000/api/ingest"
curl "http://localhost:8000/api/customers?page=1&limit=5"
```
