"""Product Agent backed by the SQLite product tool."""

from __future__ import annotations

from typing import Mapping, TypedDict

from tools.product_tools import search_product as search_product_tool


class ProductInput(TypedDict, total=False):
    """Input contract for a product lookup."""

    product_name: str
    size: str | None
    color: str | None


class ProductResult(TypedDict):
    """Output contract returned by the Product Agent."""

    found: bool
    product_id: str | None
    variant_id: str | None
    name: str | None
    size: str | None
    color: str | None
    price: int | float | None
    stock: int


class ProductAgentError(ValueError):
    """Raised when a product lookup request is invalid."""


class ProductAgent:
    """Look up products and stock using the SQLite product tool."""

    def run(self, product_input: Mapping[str, object]) -> ProductResult:
        """Process a product lookup request."""

        if not isinstance(product_input, Mapping):
            raise ProductAgentError("product_input must be a mapping")

        product_name = product_input.get("product_name")
        size = product_input.get("size")
        color = product_input.get("color")

        if not isinstance(product_name, str) or not product_name.strip():
            raise ProductAgentError(
                "product_name must be a non-empty string"
            )

        if size is not None and not isinstance(size, str):
            raise ProductAgentError("size must be a string or null")

        if color is not None and not isinstance(color, str):
            raise ProductAgentError("color must be a string or null")

        result = search_product_tool(
            product_name,
            size,
            color,
        )

        if not result["found"]:
            return {
                "found": False,
                "product_id": None,
                "variant_id": None,
                "name": None,
                "size": None,
                "color": None,
                "price": None,
                "stock": 0,
            }

        return {
            "found": True,
            "product_id": result["product_id"],
            "variant_id": result["variant_id"],
            "name": result["name"],
            "size": result["size"],
            "color": result["color"],
            "price": result["price"],
            "stock": result["stock"],
        }