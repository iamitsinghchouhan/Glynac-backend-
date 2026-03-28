import json
from pathlib import Path

from flask import Flask, jsonify, request


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "customers.json"

app = Flask(__name__)


def load_customers() -> list[dict]:
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def paginate(items: list[dict], page: int, limit: int) -> tuple[list[dict], int]:
    start = (page - 1) * limit
    end = start + limit
    return items[start:end], len(items)


@app.get("/api/health")
def health_check():
    return jsonify({"status": "ok"})


@app.get("/api/customers")
def list_customers():
    page = max(request.args.get("page", default=1, type=int), 1)
    limit = max(request.args.get("limit", default=10, type=int), 1)

    customers = load_customers()
    page_items, total = paginate(customers, page, limit)

    return jsonify(
        {
            "data": page_items,
            "total": total,
            "page": page,
            "limit": limit,
        }
    )


@app.get("/api/customers/<customer_id>")
def get_customer(customer_id: str):
    customers = load_customers()
    customer = next(
        (item for item in customers if item["customer_id"] == customer_id),
        None,
    )

    if customer is None:
        return jsonify({"detail": "Customer not found"}), 404

    return jsonify(customer)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
