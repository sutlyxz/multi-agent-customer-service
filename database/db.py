"""SQLite connection and schema management for customer service data."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from sqlite3 import Connection


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "customer_service.db"


class DatabaseError(RuntimeError):
    """Raised when the SQLite data layer cannot complete an operation."""


def connect_db(db_path: str | Path = DEFAULT_DB_PATH) -> Connection:
    """Open a SQLite connection to the configured database file."""
    path = Path(db_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        return connection
    except (OSError, sqlite3.Error) as exc:
        raise DatabaseError(f"Unable to connect to SQLite database: {path}") from exc


def create_tables(connection: Connection) -> None:
    """Create the products and orders tables if they do not exist."""
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                size TEXT,
                color TEXT,
                price REAL,
                stock INTEGER
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT,
                product_id TEXT,
                quantity INTEGER,
                status TEXT,
                tracking_number TEXT
            );
            """
        )
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise DatabaseError("Unable to create database tables") from exc


def initialize_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    """Create the database file and tables, then return its path."""
    path = Path(db_path)
    connection = connect_db(path)
    try:
        create_tables(connection)
    finally:
        connection.close()
    return path
