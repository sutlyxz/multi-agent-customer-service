"""Create and seed the customer service SQLite database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

try:
    from database.db import DEFAULT_DB_PATH, DatabaseError, connect_db, create_tables
except ModuleNotFoundError:
    from db import DEFAULT_DB_PATH, DatabaseError, connect_db, create_tables


PRODUCTS: tuple[tuple[str, str, str, str, float, int], ...] = (
    ("P001", "Nike Air Max", "42", "black", 3500.0, 5),
    ("P002", "Nike Air Max", "43", "black", 3500.0, 2),
    ("P003", "Adidas Ultra", "42", "white", 2900.0, 8),
)

ORDERS: tuple[tuple[str, str, str, int, str, str | None], ...] = (
    ("ORD001", "C001", "P001", 1, "shipped", "TH123456"),
    ("ORD002", "C002", "P003", 2, "processing", None),
)


def seed_mock_data(
    connection: sqlite3.Connection,
    products: tuple[tuple[str, str, str, str, float, int], ...] = PRODUCTS,
    orders: tuple[tuple[str, str, str, int, str, str | None], ...] = ORDERS,
) -> None:
    """Insert or replace the supplied mock products and orders."""
    try:
        connection.executemany(
            """
            INSERT OR REPLACE INTO products
                (product_id, name, size, color, price, stock)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            products,
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO orders
                (order_id, customer_id, product_id, quantity, status, tracking_number)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            orders,
        )
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise DatabaseError("Unable to seed mock data") from exc


def seed_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    """Create tables, seed mock data, close the connection, and return the path."""
    path = Path(db_path)
    connection = connect_db(path)
    try:
        create_tables(connection)
        seed_mock_data(connection)
    finally:
        connection.close()
    return path


def main() -> None:
    """Create and seed the default customer service database."""
    try:
        path = seed_database()
        print(f"Database seeded successfully: {path}")
    except DatabaseError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
