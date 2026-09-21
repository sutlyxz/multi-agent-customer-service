"""Deterministic tests for the multi-agent customer service workflow."""

from __future__ import annotations

import pytest

from agents.intent import IntentAgent
from agents.order import OrderAgent
from agents.product import ProductAgent
from agents.resolution import ResolutionAgent
from state import AgentState
from workflow import build_workflow


def assert_equal_with_context(actual: object, expected: object, label: str) -> None:
    """Show expected and actual values when a contract assertion fails."""
    assert actual == expected, (
        f"{label}\nExpected: {expected!r}\nActual: {actual!r}"
    )


class FakeStructuredOutput:
    """Minimal runnable returned by a fake structured-output model."""

    def __init__(self, response: object) -> None:
        self.response = response
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> object:
        self.prompts.append(prompt)
        return self.response


class FakeIntentModel:
    """Fake LangChain model for testing Intent Agent parsing."""

    def __init__(self, response: object) -> None:
        self.output = FakeStructuredOutput(response)

    def with_structured_output(
        self,
        schema: object,
        **kwargs: object,
    ) -> FakeStructuredOutput:
        return self.output


class FakeResolutionModel:
    """Fake LangChain model that records resolution context."""

    def __init__(self, response: str = "verified response") -> None:
        self.output = FakeStructuredOutput({"response": response})

    def with_structured_output(
        self,
        schema: object,
        **kwargs: object,
    ) -> FakeStructuredOutput:
        return self.output


class FakeIntentAgent:
    """Deterministic Intent Agent replacement for workflow tests."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[str] = []

    def analyze(self, user_message: str) -> object:
        self.calls.append(user_message)
        return self.result


class FakeResolutionAgent:
    """Deterministic Resolution Agent replacement for workflow tests."""

    def __init__(self, response: str = "verified response") -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def run(self, payload: dict[str, object]) -> object:
        self.calls.append(payload)
        return type(
            "ResolutionOutput",
            (),
            {"response": self.response},
        )()


def initial_state(user_message: str) -> AgentState:
    """Create a complete shared state for direct workflow tests."""
    return {
        "user_message": user_message,
        "intent": None,
        "product_name": None,
        "size": None,
        "color": None,
        "order_id": None,
        "product_result": None,
        "order_result": None,
        "agent_results": [],
        "final_response": None,
    }


@pytest.mark.parametrize(
    ("message", "intent", "entities"),
    [
        (
            "รองเท้า Nike Air Max สีดำไซส์ 42 มีไหม",
            "product_inquiry",
            {
                "product_name": "Nike Air Max",
                "size": "42",
                "color": "black",
                "order_id": None,
            },
        ),
        (
            "Order ORD001 อยู่ไหน",
            "order_tracking",
            {
                "product_name": None,
                "size": None,
                "color": None,
                "order_id": "ORD001",
            },
        ),
    ],
)
def test_intent_agent_returns_structured_result(
    message: str,
    intent: str,
    entities: dict[str, str | None],
) -> None:
    """Intent Agent extracts supported intent and missing entities as null."""
    model = FakeIntentModel(
        {
            "intent": intent,
            "entities": entities,
        }
    )

    result = IntentAgent(llm=model).analyze(message)

    assert_equal_with_context(
        result.intent,
        intent,
        "Intent mismatch",
    )

    assert_equal_with_context(
        result.entities.model_dump(),
        entities,
        "Entity extraction mismatch",
    )

    assert model.output.prompts


def test_product_agent_found_product() -> None:
    """Product Agent returns the deterministic Nike mock product."""
    result = ProductAgent().run(
        {
            "product_name": "Nike Air Max",
            "size": "42",
            "color": "black",
        }
    )

    expected = {
        "found": True,
        "product_id": "P001",
        "variant_id": None,
        "name": "Nike Air Max",
        "size": "42",
        "color": "black",
        "price": 3500.0,
        "stock": 5,
    }

    assert_equal_with_context(
        result,
        expected,
        "Product result mismatch",
    )


def test_product_agent_handles_missing_size_and_color() -> None:
    """Product Agent accepts optional size/color fields."""
    result = ProductAgent().run(
        {
            "product_name": "Adidas",
            "size": None,
            "color": None,
        }
    )

    expected = {
        "found": False,
        "product_id": None,
        "variant_id": None,
        "name": None,
        "size": None,
        "color": None,
        "price": None,
        "stock": 0,
    }

    assert_equal_with_context(
        result,
        expected,
        "Missing-attribute product mismatch",
    )


def test_order_agent_found_order() -> None:
    """Order Agent returns ORD001 shipment data."""
    result = OrderAgent().run(
        {
            "order_id": "ORD001",
        }
    )

    expected = {
        "success": True,
        "order_id": "ORD001",
        "status": "shipped",
        "tracking_number": "TH123456",
        "carrier": None,
        "estimated_delivery": None,
        "error": None,
    }

    assert_equal_with_context(
        result,
        expected,
        "Order result mismatch",
    )


def test_order_agent_not_found_has_no_tracking_number() -> None:
    """Unknown orders return an explicit error without fabricated tracking data."""
    result = OrderAgent().run(
        {
            "order_id": "ORD999",
        }
    )

    expected = {
        "success": False,
        "order_id": "ORD999",
        "status": None,
        "tracking_number": None,
        "carrier": None,
        "estimated_delivery": None,
        "error": "Order not found",
    }

    assert_equal_with_context(
        result,
        expected,
        "Missing order result mismatch",
    )

    assert result["tracking_number"] is None


def test_resolution_agent_uses_all_agent_results() -> None:
    """Resolution receives product and order results and returns structured text."""
    model = FakeResolutionModel()
    agent = ResolutionAgent(llm=model)

    results = [
        {
            "agent": "product_agent",
            "data": {
                "name": "Nike Air Max",
                "stock": 5,
            },
        },
        {
            "agent": "order_agent",
            "data": {
                "order_id": "ORD001",
                "status": "shipped",
            },
        },
    ]

    response = agent.run(
        {
            "customer_message": "มีสินค้าไหม และออเดอร์อยู่ไหน",
            "results": results,
        }
    )

    assert_equal_with_context(
        response.response,
        "verified response",
        "Response mismatch",
    )

    prompt = model.output.prompts[0]

    assert "Nike Air Max" in prompt
    assert "ORD001" in prompt
    assert "shipped" in prompt


def test_orchestrator_routes_multi_intent_to_both_agents() -> None:
    """Orchestrator calls Product and Order paths and forwards both results."""
    resolution = FakeResolutionAgent("multi-intent resolved")

    from agents.orchestrator import Orchestrator

    result = Orchestrator(
        resolution_agent=resolution,
    ).run(
        initial_state("มีสินค้าไหม และออเดอร์อยู่ไหน"),
        {
            "intent": [
                "product_inquiry",
                "order_tracking",
            ],
            "entities": {
                "product_name": "Nike Air Max",
                "size": "42",
                "color": "black",
                "order_id": "ORD001",
            },
        },
    )

    assert_equal_with_context(
        [item["agent"] for item in result["agent_results"]],
        [
            "product_agent",
            "order_agent",
        ],
        "Multi-intent routing mismatch",
    )

    assert result["product_result"] is not None
    assert result["order_result"] is not None

    assert resolution.calls[0]["results"] == result["agent_results"]


def test_full_workflow_product_inquiry() -> None:
    """Full LangGraph path routes product inquiry to Product then Resolution."""
    message = "รองเท้า Nike Air Max สีดำไซส์ 42 มีไหม"

    intent = FakeIntentAgent(
        {
            "intent": "product_inquiry",
            "entities": {
                "product_name": "Nike Air Max",
                "size": "42",
                "color": "black",
                "order_id": None,
            },
        }
    )

    resolution = FakeResolutionAgent("product resolved")

    graph = build_workflow(
        intent_agent=intent,
        product_agent=ProductAgent(),
        order_agent=OrderAgent(),
        resolution_agent=resolution,
    )

    result = graph.invoke(
        initial_state(message)
    )

    assert_equal_with_context(
        result["intent"],
        "product_inquiry",
        "Workflow intent mismatch",
    )

    assert_equal_with_context(
        result["product_result"]["product_id"],
        "P001",
        "Workflow product mismatch",
    )

    assert_equal_with_context(
        [item["agent"] for item in result["agent_results"]],
        ["product_agent"],
        "Workflow product routing mismatch",
    )

    assert_equal_with_context(
        result["final_response"],
        "product resolved",
        "Workflow response mismatch",
    )


def test_full_workflow_order_not_found() -> None:
    """Full LangGraph path preserves Order not found without hallucinated tracking."""
    message = "Order ORD999 อยู่ไหน"

    intent = FakeIntentAgent(
        {
            "intent": "order_tracking",
            "entities": {
                "product_name": None,
                "size": None,
                "color": None,
                "order_id": "ORD999",
            },
        }
    )

    resolution = FakeResolutionAgent(
        "ไม่พบข้อมูลคำสั่งซื้อ"
    )

    graph = build_workflow(
        intent_agent=intent,
        product_agent=ProductAgent(),
        order_agent=OrderAgent(),
        resolution_agent=resolution,
    )

    result = graph.invoke(
        initial_state(message)
    )

    expected_order_result = {
        "success": False,
        "order_id": "ORD999",
        "status": None,
        "tracking_number": None,
        "carrier": None,
        "estimated_delivery": None,
        "error": "Order not found",
    }

    assert_equal_with_context(
        result["order_result"],
        expected_order_result,
        "Workflow missing-order mismatch",
    )

    assert result["order_result"]["tracking_number"] is None

    assert_equal_with_context(
        result["final_response"],
        "ไม่พบข้อมูลคำสั่งซื้อ",
        "Workflow response mismatch",
    )