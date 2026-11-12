"""A tiny local API with enough real behavior for positive, negative and DB tests.

There are no users, payments, external services or production security features.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

PRICES = {"MOUSE-01": 799, "CABLE-02": 299, "LAMP-03": 1199}
STATUSES = {"pending", "packed", "shipped", "cancelled"}
NEXT = {"pending": {"packed", "cancelled"}, "packed": {"shipped", "cancelled"}, "shipped": set(), "cancelled": set()}

class OrderCreate(BaseModel):
    customer: str = Field(min_length=2, max_length=80)
    sku: str
    quantity: int = Field(ge=1, le=10)

class StatusUpdate(BaseModel):
    status: str

@contextmanager
def connection(db_path):
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()

def create_app(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connection(db_path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT NOT NULL,
            sku TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )""")
    app = FastAPI(title="Orders QA Lab", version="1.0.0", description="Local sample API for functional/API/database testing")

    @app.get('/health')
    def health():
        return {"status": "ok"}

    @app.post('/orders', status_code=201)
    def create_order(order: OrderCreate):
        if not order.customer.strip():
            raise HTTPException(status_code=422, detail="Customer name cannot be blank")
        if order.sku not in PRICES:
            raise HTTPException(status_code=400, detail="Unknown product SKU")
        with connection(db_path) as db:
            cursor = db.execute("INSERT INTO orders(customer,sku,quantity,total,status) VALUES (?,?,?,?,?)",
                                (order.customer.strip(), order.sku, order.quantity, PRICES[order.sku] * order.quantity, "pending"))
            row = db.execute("SELECT * FROM orders WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict(row)

    @app.get('/orders')
    def list_orders(status: str | None = Query(default=None)):
        if status is not None and status not in STATUSES:
            raise HTTPException(status_code=400, detail="Unknown order status")
        with connection(db_path) as db:
            if status:
                rows = db.execute("SELECT * FROM orders WHERE status=? ORDER BY id", (status,)).fetchall()
            else:
                rows = db.execute("SELECT * FROM orders ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    @app.get('/orders/{order_id}')
    def get_order(order_id: int):
        with connection(db_path) as db:
            row = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return dict(row)

    @app.patch('/orders/{order_id}/status')
    def change_status(order_id: int, change: StatusUpdate):
        if change.status not in STATUSES:
            raise HTTPException(status_code=400, detail="Unknown order status")
        with connection(db_path) as db:
            row = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Order not found")
            if change.status not in NEXT[row['status']]:
                raise HTTPException(status_code=409, detail="Invalid status transition")
            db.execute("UPDATE orders SET status=? WHERE id=?", (change.status, order_id))
            updated = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return dict(updated)

    return app

app = create_app(os.getenv("ORDER_DB", str(Path(__file__).resolve().parents[1] / "data" / "orders.db")))
