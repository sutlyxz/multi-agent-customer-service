"""Tests for database access tools using the seeded SQLite database."""

from __future__ import annotations

from tools.order_tools import get_order, track_order
from tools.product_tools import check_stock, search_product


def test_search_product_found() -> None:
    result = search_product("Nike Air Max", "42", "black")
    assert result == {
        "found": True,
        "product_id": "P001",
        "variant_id": None,
        "name": "Nike Air Max",
        "size": "42",
        "color": "black",
        "price": 3500.0,
        "stock": 5,
    }


def test_search_product_not_found() -> None:
    assert search_product("Adidas Ultra", "42", "black") == {
        "found": False,
        "data": None,
        "error": "Product not found",
    }


def test_check_stock_reports_missing_variant_schema() -> None:
    result = check_stock("V001")
    assert result["success"] is False
    assert result["variant_id"] == "V001"
    assert "product_variants" in result["error"]


def test_get_order_found() -> None:
    result = get_order("ORD001")
    assert result["success"] is True
    assert result["order"] == {
        "order_id": "ORD001",
        "customer_id": "C001",
        "status": "shipped",
        "items": [{
            "product_id": "P001",
            "name": "Nike Air Max",
            "quantity": 1,
            "price": 3500.0,
        }],
        "total_amount": 3500.0,
    }


def test_get_order_not_found() -> None:
    assert get_order("ORD999") == {
        "success": False,
        "error": "Order not found",
    }


def test_track_order_found() -> None:
    assert track_order("ORD001") == {
        "success": True,
        "order_id": "ORD001",
        "status": "shipped",
        "tracking_number": "TH123456",
        "carrier": None,
        "estimated_delivery": None,
    }
