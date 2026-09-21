"""Order database tools backed by the existing SQLite schema."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from database.db import DEFAULT_DB_PATH, DatabaseError, connect_db


class OrderToolError(RuntimeError):
    """Raised when an order tool cannot complete its database operation."""


def get_order(
    order_id: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Get an order and its product details from the available tables.

    The current schema has no order_items or customers table. The existing
    orders.product_id and quantity columns are represented as one item.
    """
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("order_id must be a non-empty string")

    connection: sqlite3.Connection | None = None
    try:
        connection = connect_db(db_path)
        row = connection.execute(
            """
            SELECT o.order_id, o.customer_id, o.status, o.quantity,
                   o.product_id, p.name, p.price
            FROM orders AS o
            LEFT JOIN products AS p ON p.product_id = o.product_id
            WHERE o.order_id = ?
            """,
            (order_id.strip(),),
        ).fetchone()
        if row is None:
            return {"success": False, "error": "Order not found"}

        quantity = row["quantity"] or 0
        price = row["price"]
        item = {
            "product_id": row["product_id"],
            "name": row["name"],
            "quantity": quantity,
            "price": price,
        }
        total_amount = price * quantity if price is not None else None
        return {
            "success": True,
            "order": {
                "order_id": row["order_id"],
                "customer_id": row["customer_id"],
                "status": row["status"],
                "items": [item],
                "total_amount": total_amount,
            },
        }
    except (sqlite3.Error, DatabaseError) as exc:
        raise OrderToolError("Unable to retrieve order") from exc
    finally:
        if connection is not None:
            connection.close()


def track_order(
    order_id: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Get order tracking fields available in the current orders table.

    The current schema has no shipments table, so carrier and estimated_delivery
    are returned as None instead of being fabricated.
    """
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("order_id must be a non-empty string")

    connection: sqlite3.Connection | None = None
    try:
        connection = connect_db(db_path)
        row = connection.execute(
            """
            SELECT order_id, status, tracking_number
            FROM orders
            WHERE order_id = ?
            """,
            (order_id.strip(),),
        ).fetchone()
        if row is None:
            return {"success": False, "error": "Order not found"}
        return {
            "success": True,
            "order_id": row["order_id"],
            "status": row["status"],
            "tracking_number": row["tracking_number"],
            "carrier": None,
            "estimated_delivery": None,
        }
    except (sqlite3.Error, DatabaseError) as exc:
        raise OrderToolError("Unable to track order") from exc
    finally:
        if connection is not None:
            connection.close()
