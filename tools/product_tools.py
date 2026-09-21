"""Product database tools backed by the existing SQLite schema."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from database.db import DEFAULT_DB_PATH, DatabaseError, connect_db


class ProductToolError(RuntimeError):
    """Raised when a product tool cannot complete its database operation."""


def search_product(
    name: str,
    size: str | None = None,
    color: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Search products by name and optional size/color using the real schema.

    The current database has no product_variants table, so variant_id is returned
    as None rather than being fabricated.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    if size is not None and not isinstance(size, str):
        raise ValueError("size must be a string or null")
    if color is not None and not isinstance(color, str):
        raise ValueError("color must be a string or null")

    query = """
        SELECT product_id, name, size, color, price, stock
        FROM products
        WHERE LOWER(name) = LOWER(?)
    """
    parameters: list[object] = [name.strip()]
    if size is not None:
        query += " AND size = ?"
        parameters.append(size.strip())
    if color is not None:
        query += " AND LOWER(color) = LOWER(?)"
        parameters.append(color.strip())
    query += " ORDER BY product_id LIMIT 1"

    connection: sqlite3.Connection | None = None
    try:
        connection = connect_db(db_path)
        row = connection.execute(query, parameters).fetchone()
        if row is None:
            return {"found": False, "data": None, "error": "Product not found"}
        return {
            "found": True,
            "product_id": row["product_id"],
            "variant_id": None,
            "name": row["name"],
            "size": row["size"],
            "color": row["color"],
            "price": row["price"],
            "stock": row["stock"],
        }
    except (sqlite3.Error, DatabaseError) as exc:
        raise ProductToolError("Unable to search products") from exc
    finally:
        if connection is not None:
            connection.close()


def check_stock(
    variant_id: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Check stock by variant ID when the required table exists.

    The inspected database has no product_variants table, so this reports the
    unavailable capability instead of treating a product ID as a variant ID.
    """
    if not isinstance(variant_id, str) or not variant_id.strip():
        raise ValueError("variant_id must be a non-empty string")

    connection: sqlite3.Connection | None = None
    try:
        connection = connect_db(db_path)
        table = connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = ?",
            ("product_variants",),
        ).fetchone()
        if table is None:
            return {
                "success": False,
                "variant_id": variant_id,
                "error": "product_variants table is not available",
            }
        row = connection.execute(
            "SELECT stock FROM product_variants WHERE variant_id = ?",
            (variant_id,),
        ).fetchone()
        if row is None:
            return {
                "success": False,
                "variant_id": variant_id,
                "error": "Variant not found",
            }
        return {"success": True, "variant_id": variant_id, "stock": row["stock"]}
    except (sqlite3.Error, DatabaseError) as exc:
        raise ProductToolError("Unable to check stock") from exc
    finally:
        if connection is not None:
            connection.close()
