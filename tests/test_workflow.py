from agents.intent import IntentResult, IntentEntities
from agents.resolution import ResolutionResult
from workflow import build_workflow


class MockIntentAgent:
    def analyze(self, user_message: str):
        return IntentResult(
            intent="product_inquiry",
            entities=IntentEntities(
                product_name="Nike Air Max",
                size="42",
                color="black",
                order_id=None,
            ),
        )


class MockResolutionAgent:
    def run(self, resolution_input):
        return ResolutionResult(
            response="พบสินค้า Nike Air Max ไซส์ 42 สี black ราคา 3500 บาท มีสินค้า 5 ชิ้น"
        )


def test_product_workflow():
    graph = build_workflow(
        intent_agent=MockIntentAgent(),
        resolution_agent=MockResolutionAgent(),
    )

    result = graph.invoke({
        "user_message": "อยากรู้ว่า Nike Air Max ไซส์ 42 สีดำมีของไหม",
        "intent": None,
        "product_name": None,
        "size": None,
        "color": None,
        "order_id": None,
        "product_result": None,
        "order_result": None,
        "agent_results": [],
        "final_response": None,
    })

    assert result["intent"] == "product_inquiry"
    assert result["product_result"]["found"] is True
    assert result["product_result"]["product_id"] == "P001"
    assert result["product_result"]["stock"] == 5

    assert result["final_response"] == (
        "พบสินค้า Nike Air Max ไซส์ 42 สี black ราคา 3500 บาท มีสินค้า 5 ชิ้น"
    )


# =========================
# Order Workflow
# =========================

class MockOrderIntentAgent:
    def analyze(self, user_message: str):
        return IntentResult(
            intent="order_tracking",
            entities=IntentEntities(
                product_name=None,
                size=None,
                color=None,
                order_id="ORD001",
            ),
        )


class MockOrderResolutionAgent:
    def run(self, resolution_input):
        return ResolutionResult(
            response="ออเดอร์ ORD001 อยู่ในสถานะ shipped และหมายเลขติดตามคือ TH123456"
        )


def test_order_workflow():
    graph = build_workflow(
        intent_agent=MockOrderIntentAgent(),
        resolution_agent=MockOrderResolutionAgent(),
    )

    result = graph.invoke({
        "user_message": "ออเดอร์ ORD001 ถึงไหนแล้ว",
        "intent": None,
        "product_name": None,
        "size": None,
        "color": None,
        "order_id": None,
        "product_result": None,
        "order_result": None,
        "agent_results": [],
        "final_response": None,
    })

    assert result["intent"] == "order_tracking"

    assert result["order_result"]["success"] is True
    assert result["order_result"]["order_id"] == "ORD001"
    assert result["order_result"]["status"] == "shipped"
    assert result["order_result"]["tracking_number"] == "TH123456"

    assert result["final_response"] == (
        "ออเดอร์ ORD001 อยู่ในสถานะ shipped และหมายเลขติดตามคือ TH123456"
    )

# =========================
# Multi-Intent Workflow
# =========================

class MockMultiIntentAgent:
    def analyze(self, user_message: str):
        return IntentResult(
            intent=[
                "product_inquiry",
                "order_tracking",
            ],
            entities=IntentEntities(
                product_name="Nike Air Max",
                size="42",
                color="black",
                order_id="ORD001",
            ),
        )


class MockMultiResolutionAgent:
    def run(self, resolution_input):
        return ResolutionResult(
            response=(
                "Nike Air Max ไซส์ 42 สี black มีสินค้า 5 ชิ้น "
                "และออเดอร์ ORD001 อยู่ในสถานะ shipped "
                "หมายเลขติดตามคือ TH123456"
            )
        )


def test_multi_intent_workflow():
    graph = build_workflow(
        intent_agent=MockMultiIntentAgent(),
        resolution_agent=MockMultiResolutionAgent(),
    )

    result = graph.invoke({
        "user_message": (
            "Nike Air Max ไซส์ 42 สีดำมีไหม "
            "และออเดอร์ ORD001 ถึงไหนแล้ว"
        ),
        "intent": None,
        "product_name": None,
        "size": None,
        "color": None,
        "order_id": None,
        "product_result": None,
        "order_result": None,
        "agent_results": [],
        "final_response": None,
    })

    # Intent Agent ต้องตรวจพบ 2 intents
    assert result["intent"] == [
        "product_inquiry",
        "order_tracking",
    ]

    # Product Agent ต้องทำงาน
    assert result["product_result"]["found"] is True
    assert result["product_result"]["product_id"] == "P001"
    assert result["product_result"]["stock"] == 5

    # Order Agent ต้องทำงาน
    assert result["order_result"]["success"] is True
    assert result["order_result"]["order_id"] == "ORD001"
    assert result["order_result"]["status"] == "shipped"
    assert result["order_result"]["tracking_number"] == "TH123456"

    # Resolution Agent ต้องได้รับผลจากทั้งสอง Agent
    assert result["final_response"] == (
        "Nike Air Max ไซส์ 42 สี black มีสินค้า 5 ชิ้น "
        "และออเดอร์ ORD001 อยู่ในสถานะ shipped "
        "หมายเลขติดตามคือ TH123456"
    )

# =========================
# Error Handling - Product Not Found
# =========================

class MockProductNotFoundIntentAgent:
    def analyze(self, user_message: str):
        return IntentResult(
            intent="product_inquiry",
            entities=IntentEntities(
                product_name="iPhone 99",
                size="99",
                color="pink",
                order_id=None,
            ),
        )


class MockProductNotFoundResolutionAgent:
    def run(self, resolution_input):
        return ResolutionResult(
            response="ไม่พบสินค้าที่คุณกำลังค้นหา"
        )


def test_product_not_found_workflow():
    graph = build_workflow(
        intent_agent=MockProductNotFoundIntentAgent(),
        resolution_agent=MockProductNotFoundResolutionAgent(),
    )

    result = graph.invoke({
        "user_message": "มี iPhone 99 ไซส์ 99 สีชมพูไหม",
        "intent": None,
        "product_name": None,
        "size": None,
        "color": None,
        "order_id": None,
        "product_result": None,
        "order_result": None,
        "agent_results": [],
        "final_response": None,
    })

    assert result["intent"] == "product_inquiry"

    assert result["product_result"]["found"] is False
    assert result["product_result"]["product_id"] is None
    assert result["product_result"]["stock"] == 0

    assert result["final_response"] == (
        "ไม่พบสินค้าที่คุณกำลังค้นหา"
    )

# =========================
# Error Handling - Order Not Found
# =========================

class MockOrderNotFoundIntentAgent:
    def analyze(self, user_message: str):
        return IntentResult(
            intent="order_tracking",
            entities=IntentEntities(
                product_name=None,
                size=None,
                color=None,
                order_id="ORD999",
            ),
        )


class MockOrderNotFoundResolutionAgent:
    def run(self, resolution_input):
        return ResolutionResult(
            response="ไม่พบหมายเลขคำสั่งซื้อ ORD999 ในระบบ"
        )


def test_order_not_found_workflow():
    graph = build_workflow(
        intent_agent=MockOrderNotFoundIntentAgent(),
        resolution_agent=MockOrderNotFoundResolutionAgent(),
    )

    result = graph.invoke({
        "user_message": "ขอติดตามออเดอร์ ORD999",
        "intent": None,
        "product_name": None,
        "size": None,
        "color": None,
        "order_id": None,
        "product_result": None,
        "order_result": None,
        "agent_results": [],
        "final_response": None,
    })

    assert result["intent"] == "order_tracking"

    assert result["order_result"]["success"] is False
    assert result["order_result"]["order_id"] == "ORD999"
    assert result["order_result"]["status"] is None
    assert result["order_result"]["tracking_number"] is None

    assert result["final_response"] == (
        "ไม่พบหมายเลขคำสั่งซื้อ ORD999 ในระบบ"
    )