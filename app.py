from dotenv import load_dotenv

from agents.order import OrderAgent
from agents.product import ProductAgent
from workflow import build_workflow


class DemoIntentAgent:
    """
    Deterministic Intent Agent for local demo.
    ใช้แทน Gemini ชั่วคราวเพื่อไม่ใช้ API quota
    """

    def analyze(self, user_message: str) -> dict:
        message = user_message.lower()

        # Order tracking
        if "order" in message or "ออเดอร์" in message:
            import re

            match = re.search(r"ORD\d+", user_message, re.IGNORECASE)

            return {
                "intent": "order_tracking",
                "entities": {
                    "product_name": None,
                    "size": None,
                    "color": None,
                    "order_id": match.group(0).upper() if match else None,
                },
            }

        # Product inquiry
        if (
            "มีไหม" in message
            or "มีของไหม" in message
            or "สินค้า" in message
            or "ราคา" in message
        ):
            product_name = None
            size = None
            color = None

            if "nike air max" in message:
                product_name = "Nike Air Max"

            elif "adidas ultra" in message:
                product_name = "Adidas Ultra"

            if "42" in message:
                size = "42"

            elif "43" in message:
                size = "43"

            if "ดำ" in message:
                color = "black"

            elif "ขาว" in message:
                color = "white"

            return {
                "intent": "product_inquiry",
                "entities": {
                    "product_name": product_name,
                    "size": size,
                    "color": color,
                    "order_id": None,
                },
            }

        # General question
        return {
            "intent": "general_question",
            "entities": {
                "product_name": None,
                "size": None,
                "color": None,
                "order_id": None,
            },
        }


class DemoResolutionAgent:
    """
    Deterministic Resolution Agent for local demo.
    ไม่เรียก Gemini
    """

    def run(self, payload: dict) -> object:
        results = payload.get("results", [])

        responses = []

        for result in results:
            agent = result.get("agent")
            data = result.get("data", {})

            # Product Agent result
            if agent == "product_agent":

                if data.get("found"):
                    name = data.get("name")
                    size = data.get("size")
                    color = data.get("color")
                    price = data.get("price")
                    stock = data.get("stock")

                    responses.append(
                        f"พบสินค้า {name} "
                        f"ไซส์ {size} "
                        f"สี {color} "
                        f"ราคา {price:.0f} บาท "
                        f"มีสินค้า {stock} ชิ้น"
                    )

                else:
                    responses.append(
                        "ไม่พบสินค้าที่ตรงกับข้อมูลที่ค้นหา"
                    )

            # Order Agent result
            elif agent == "order_agent":

                if data.get("success"):
                    order_id = data.get("order_id")
                    status = data.get("status")
                    tracking = data.get("tracking_number")

                    response = (
                        f"คำสั่งซื้อ {order_id} "
                        f"สถานะ {status}"
                    )

                    if tracking:
                        response += f" เลขพัสดุ {tracking}"

                    responses.append(response)

                else:
                    responses.append(
                        f"ไม่พบข้อมูลคำสั่งซื้อ "
                        f"{data.get('order_id')}"
                    )

            # Unsupported intent
            elif agent == "orchestrator":
                message = data.get("message")

                if message:
                    responses.append(message)

        if not responses:
            response = (
                "ขออภัย ระบบยังไม่สามารถตอบคำถามนี้ได้"
            )
        else:
            response = "\n".join(responses)

        return type(
            "ResolutionOutput",
            (),
            {"response": response},
        )()


def print_trace(result: dict) -> None:
    """แสดงการทำงานของ Multi-Agent Workflow"""

    print("\n" + "=" * 60)
    print("AGENT TRACE")
    print("=" * 60)

    print("\n[1] Intent Agent")

    print(f"Intent: {result.get('intent')}")

    print("Entities:")
    print(f"  product_name = {result.get('product_name')}")
    print(f"  size         = {result.get('size')}")
    print(f"  color        = {result.get('color')}")
    print(f"  order_id     = {result.get('order_id')}")

    print("\n[2] Orchestrator")

    intent = result.get("intent")

    if isinstance(intent, list):
        print("Routing to multiple agents:")
        for item in intent:
            print(f"  → {item}")
    else:
        if intent == "product_inquiry":
            print("Routing → Product Agent")

        elif intent == "order_tracking":
            print("Routing → Order Agent")

        else:
            print("Routing → Resolution Agent")

    product_result = result.get("product_result")

    if product_result is not None:
        print("\n[3] Product Agent")
        print("  → search_product()")
        print(f"  → found      = {product_result.get('found')}")
        print(f"  → product_id = {product_result.get('product_id')}")
        print(f"  → stock      = {product_result.get('stock')}")

    order_result = result.get("order_result")

    if order_result is not None:
        print("\n[3] Order Agent")
        print("  → track_order()")
        print(f"  → order_id   = {order_result.get('order_id')}")
        print(f"  → status     = {order_result.get('status')}")
        print(
            f"  → tracking   = "
            f"{order_result.get('tracking_number')}"
        )

    print("\n[4] Resolution Agent")
    print("  → Combining verified agent results")

    print("\n" + "=" * 60)


def main() -> None:
    load_dotenv()

    # ใช้ Mock Agent แทน Gemini ชั่วคราว
    intent_agent = DemoIntentAgent()
    resolution_agent = DemoResolutionAgent()

    # ใช้ Agent จริงสำหรับ Product / Order
    product_agent = ProductAgent()
    order_agent = OrderAgent()

    graph = build_workflow(
        intent_agent=intent_agent,
        product_agent=product_agent,
        order_agent=order_agent,
        resolution_agent=resolution_agent,
    )

    print("=" * 60)
    print("Multi-Agent Customer Service Demo")
    print("=" * 60)
    print("โหมด: DEMO (ไม่ใช้ Gemini API)")
    print("พิมพ์ exit เพื่อออกจากโปรแกรม")

    while True:
        print("\n" + "-" * 60)

        user_message = input("Customer: ").strip()

        if user_message.lower() == "exit":
            print("\nจบการทำงาน")
            break

        if not user_message:
            continue

        try:
            result = graph.invoke(
                {
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
            )

            print_trace(result)

            print("\nAssistant:")
            print(result["final_response"])

        except Exception as exc:
            print("\nเกิดข้อผิดพลาด:")
            print(type(exc).__name__)
            print(exc)


if __name__ == "__main__":
    main()