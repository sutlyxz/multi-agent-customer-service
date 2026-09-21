"""Order Agent backed by the SQLite order tools."""

from __future__ import annotations

from typing import Mapping, TypedDict

from tools.order_tools import get_order, track_order


class OrderInput(TypedDict, total=False):
    order_id: str


class OrderResult(TypedDict):
    success: bool
    order_id: str | None
    status: str | None
    tracking_number: str | None
    carrier: str | None
    estimated_delivery: str | None
    error: str | None


class OrderAgentError(ValueError):
    """Raised when Order Agent receives invalid input."""


class OrderAgent:
    def run(self, order_input: Mapping[str, object]) -> OrderResult:
        if not isinstance(order_input, Mapping):
            raise OrderAgentError("order_input must be a mapping")

        order_id = order_input.get("order_id")

        if not isinstance(order_id, str) or not order_id.strip():
            raise OrderAgentError("order_id must be a non-empty string")

        result = track_order(order_id)

        if not result["success"]:
            return {
                "success": False,
                "order_id": order_id,
                "status": None,
                "tracking_number": None,
                "carrier": None,
                "estimated_delivery": None,
                "error": result["error"],
            }

        return {
            "success": True,
            "order_id": result["order_id"],
            "status": result["status"],
            "tracking_number": result["tracking_number"],
            "carrier": result["carrier"],
            "estimated_delivery": result["estimated_delivery"],
            "error": None,
        }