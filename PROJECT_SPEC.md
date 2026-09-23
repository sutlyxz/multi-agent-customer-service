# Project Specification

## Objective

กำหนดขอบเขต, Architecture, workflow, JSON contract และหน้าที่ของ Agents สำหรับระบบ Multi-Agent Customer Service โดยเอกสารนี้ใช้เป็น specification กลางสำหรับการพัฒนาและทดสอบระบบ

ระบบปัจจุบันมี implementation ของ Agents, Tools, SQLite และ LangGraph แล้ว โดย Gemini ใช้เป็น LLM สำหรับ Intent Agent และ Resolution Agent ในโหมดจริง ส่วน Demo Mode สามารถใช้ Mock Agent แทน Gemini เพื่อทดสอบ workflow โดยไม่ใช้ API quota

## Agents

ระบบมี Agents ทั้งหมด 5 ตัว:

1. Intent Agent
2. Product Agent
3. Order Agent
4. Resolution Agent
5. Orchestrator

หน้าที่หลัก:

- **Intent Agent**: วิเคราะห์ข้อความของลูกค้าและสกัด intent/entities
- **Product Agent**: ค้นหาข้อมูลสินค้าและสต็อกผ่าน Product Tools
- **Order Agent**: ตรวจสอบสถานะคำสั่งซื้อและข้อมูล tracking ผ่าน Order Tools
- **Resolution Agent**: สร้างคำตอบสุดท้ายจากผลลัพธ์ที่ตรวจสอบแล้ว
- **Orchestrator**: ควบคุมการ routing, เรียก specialist agents, รวบรวมผลลัพธ์ และส่งต่อให้ Resolution Agent

---

## Architecture And Workflow

```text
Customer
    |
    v
Intent Agent
    |
    v
Orchestrator
    |---------------------------|
    v                           v
Product Agent             Order Agent
    |                           |
    |-----------|---------------|
                v
        Collect Results
                |
                v
        Resolution Agent
                |
                v
             Customer
```

### ลำดับการทำงานมาตรฐาน

1. Workflow รับ `user_message` จาก Customer และส่งให้ Intent Agent
2. Intent Agent วิเคราะห์ `intent` และ `entities` เท่านั้น
3. Orchestrator อ่าน `intent` และกำหนด routing
4. Orchestrator สร้าง input/task จาก `entities` และส่งให้ Product Agent และ/หรือ Order Agent
5. Product Agent และ Order Agent เรียก Tools ที่เกี่ยวข้องและส่งผลลัพธ์กลับมา
6. Workflow รวบรวมผลลัพธ์ของ specialist agents ไว้ใน `agent_results`
7. Resolution Agent ได้รับ `customer_message` และ `results`
8. Resolution Agent สร้างคำตอบสุดท้ายจากข้อมูลใน `results` เท่านั้น
9. Workflow ส่ง `final_response` กลับไปยัง Customer

### การรองรับ Multi-Intent

หาก Intent Agent ตรวจพบมากกว่า 1 intent Orchestrator สามารถเรียก Product Agent และ Order Agent สำหรับข้อความเดียวกันได้ และเรียก Resolution Agent เพียงครั้งเดียวหลังจากรวบรวมผลลัพธ์ทั้งหมด

---

## Routing

| Intent | Agent ที่เรียก | Input/Task |
| --- | --- | --- |
| `product_inquiry` | Product Agent | `product_name`, `size`, `color` |
| `order_tracking` | Order Agent | `order_id` |
| `return_request` | Orchestrator/Resolution Agent | ยังไม่มี specialist action ใน MVP |
| `general_question` | Resolution Agent | ไม่มี specialist action ใน MVP |

สำหรับ `return_request` และ `general_question` ระบบปัจจุบันยังไม่มี specialist action เฉพาะทาง และจะส่งบริบทที่มีให้ Resolution Agent

---

# Shared State

Workflow ใช้ shared state เพื่อส่งข้อมูลระหว่าง nodes:

```python
from typing import TypedDict, Optional

class AgentState(TypedDict):
    user_message: str
    intent: Optional[str]
    product_name: Optional[str]
    size: Optional[str]
    color: Optional[str]
    order_id: Optional[str]
    product_result: Optional[dict]
    order_result: Optional[dict]
    agent_results: list
    final_response: Optional[str]
```

> หมายเหตุ: ใน implementation จริง `intent` สามารถเป็น `string` หรือ `list` ของ strings เพื่อรองรับ multi-intent

---

# JSON Contracts

## 1. Intent Agent

### หน้าที่

วิเคราะห์ข้อความของลูกค้าเท่านั้น

Intent Agent:

- ไม่ตอบลูกค้าโดยตรง
- ไม่ค้น database
- ไม่เรียก Product/Order tools
- ไม่ทำ order action
- คืนผลเป็น structured output

### Input

```json
{
  "user_message": "รองเท้า Nike Air Max สีดำไซส์ 42 มีไหม"
}
```

### Output

```json
{
  "intent": "product_inquiry",
  "entities": {
    "product_name": "Nike Air Max",
    "size": "42",
    "color": "black",
    "order_id": null
  }
}
```

สำหรับ multi-intent:

```json
{
  "intent": [
    "product_inquiry",
    "order_tracking"
  ],
  "entities": {
    "product_name": "Nike Air Max",
    "size": "42",
    "color": "black",
    "order_id": "ORD001"
  }
}
```

### Supported Intent

- `product_inquiry`
- `order_tracking`
- `return_request`
- `general_question`

### Entity Rules

| Field | Type | Description |
| --- | --- | --- |
| `product_name` | string or null | ชื่อสินค้าที่ลูกค้าระบุ |
| `size` | string or null | ขนาดสินค้าที่ลูกค้าระบุ |
| `color` | string or null | สีสินค้าที่ลูกค้าระบุ |
| `order_id` | string or null | หมายเลขคำสั่งซื้อที่ลูกค้าระบุ |

Intent Agent มี normalization สำหรับสีภาษาไทยที่ใช้ในระบบ เช่น `ดำ`/`สีดำ` → `black`, `ขาว`/`สีขาว` → `white`, `แดง`/`สีแดง` → `red`, `น้ำเงิน`/`สีน้ำเงิน` → `blue`, `เขียว`/`สีเขียว` → `green`, `เหลือง`/`สีเหลือง` → `yellow`

ไม่ควรเปลี่ยนแปลงชื่อสินค้าและ Order ID ที่ลูกค้าระบุ

---

# 2. Product Agent

## หน้าที่

ค้นหาข้อมูลสินค้าโดยเรียก Product Tool และไม่เข้าถึง database โดยตรง

### Input

```json
{
  "product_name": "Nike Air Max",
  "size": "42",
  "color": "black"
}
```

### Output เมื่อพบสินค้า

```json
{
  "found": true,
  "product_id": "P001",
  "variant_id": null,
  "name": "Nike Air Max",
  "size": "42",
  "color": "black",
  "price": 3500.0,
  "stock": 5
}
```

### Output เมื่อไม่พบสินค้า

```json
{
  "found": false,
  "product_id": null,
  "variant_id": null,
  "name": null,
  "size": null,
  "color": null,
  "price": null,
  "stock": 0
}
```

เมื่อ `found=false` ห้ามสร้างข้อมูลสินค้า ราคา หรือ stock ขึ้นเอง

---

# 3. Order Agent

## หน้าที่

ตรวจสอบข้อมูลคำสั่งซื้อผ่าน Order Tools โดยไม่เข้าถึง database โดยตรง

### Input

```json
{
  "order_id": "ORD001"
}
```

### Output เมื่อพบคำสั่งซื้อ

```json
{
  "success": true,
  "order_id": "ORD001",
  "status": "shipped",
  "tracking_number": "TH123456",
  "carrier": null,
  "estimated_delivery": null,
  "error": null
}
```

### Output เมื่อไม่พบคำสั่งซื้อ

```json
{
  "success": false,
  "order_id": "ORD999",
  "status": null,
  "tracking_number": null,
  "carrier": null,
  "estimated_delivery": null,
  "error": "Order not found"
}
```

---

# 4. Resolution Agent

## หน้าที่

สร้างคำตอบสุดท้ายให้ลูกค้าจากข้อมูลที่ได้รับจาก Agents ก่อนหน้าเท่านั้น

Resolution Agent:

- ใช้ `customer_message` เป็นบริบท
- ใช้ `results` เป็นข้อมูลหลัก
- ห้ามสร้างข้อมูลสินค้า/Order/Tracking ที่ไม่มีใน results
- ห้าม hallucinate
- คืนคำตอบใน field `response`

### Input

```json
{
  "customer_message": "รองเท้า Nike Air Max ไซส์ 42 มีไหม และ Order ORD001 อยู่ไหน",
  "results": [
    {
      "agent": "product_agent",
      "data": {
        "found": true,
        "product_id": "P001",
        "variant_id": null,
        "name": "Nike Air Max",
        "size": "42",
        "color": "black",
        "price": 3500.0,
        "stock": 5
      }
    },
    {
      "agent": "order_agent",
      "data": {
        "success": true,
        "order_id": "ORD001",
        "status": "shipped",
        "tracking_number": "TH123456",
        "carrier": null,
        "estimated_delivery": null,
        "error": null
      }
    }
  ]
}
```

### Output

```json
{
  "response": "พบ Nike Air Max ไซส์ 42 สีดำ ราคา 3500 บาท มีสินค้า 5 ชิ้น และ Order ORD001 อยู่ในสถานะ shipped เลขพัสดุ TH123456"
}
```

---

# 5. Orchestrator

## หน้าที่

Orchestrator เป็นตัวควบคุม workflow ไม่ใช่ตัวค้น database และไม่สร้างข้อมูลทางธุรกิจขึ้นเอง

หน้าที่:

1. รับผลจาก Intent Agent
2. อ่าน intent
3. เลือก specialist Agent
4. สร้าง input/task จาก entities
5. รองรับ multi-intent
6. รวบรวมผลลัพธ์
7. ส่ง `customer_message` และ `results` ให้ Resolution Agent

### ตัวอย่าง Input

```json
{
  "user_message": "มี Nike Air Max ไซส์ 42 ไหม และ Order ORD001 อยู่ไหน"
}
```

### ตัวอย่าง Tasks

```json
[
  {
    "agent": "product_agent",
    "input": {
      "product_name": "Nike Air Max",
      "size": "42",
      "color": "black"
    }
  },
  {
    "agent": "order_agent",
    "input": {
      "order_id": "ORD001"
    }
  }
]
```

Orchestrator จะรวบรวมผลลัพธ์เป็น `agent_results` แล้วส่งต่อให้ Resolution Agent

---

# Shared Result Contract

ภายใน workflow ผลลัพธ์ที่ส่งให้ Resolution Agent ใช้รูปแบบ:

```json
{
  "agent": "product_agent",
  "data": {}
}
```

หรือ

```json
{
  "agent": "order_agent",
  "data": {}
}
```

สำหรับ intent ที่ยังไม่มี specialist action:

```json
{
  "agent": "orchestrator",
  "data": {
    "intent": "return_request",
    "supported": false,
    "message": "This capability is not supported yet."
  }
}
```

---

# Error Handling

ระบบปัจจุบันใช้ exception สำหรับ input ที่ไม่ถูกต้องและความล้มเหลวของ Agent/Workflow เช่น:

- `ProductAgentError`
- `OrderAgentError`
- `ResolutionAgentError`
- `OrchestratorError`
- `ValueError`

เมื่อ Agent ได้รับ input ที่ไม่ถูกต้อง Agent จะไม่ควรสร้างข้อมูลปลอม และ workflow จะหยุดพร้อม error ที่เกี่ยวข้อง

> หมายเหตุ: `Common Error Format` แบบ `{success:false, error:{code,message,details}}` จาก specification เดิมยังไม่ได้ถูกใช้เป็น contract กลางใน implementation ปัจจุบัน จึงไม่ควรระบุว่าเป็น requirement ที่ระบบทำได้แล้วจนกว่าจะมีการ refactor error handling ให้ใช้รูปแบบเดียวกันจริง

---

# Success Format

Contract ที่ใช้จริงในปัจจุบัน:

| Agent | Success Output |
| --- | --- |
| Intent Agent | `IntentResult` ที่มี `intent` และ `entities` |
| Product Agent | object ที่มี `found` และข้อมูลสินค้า |
| Order Agent | object ที่มี `success` และข้อมูล order |
| Resolution Agent | `ResolutionResult` ที่มี `response` |
| Orchestrator | updated `AgentState` ที่มี `intent`, results และ `final_response` |

Orchestrator ใน implementation ปัจจุบันไม่ได้คืน envelope แบบ `{ "success": true, "data": {...} }` แต่คืน shared `AgentState` จาก LangGraph

---

# Tools And Data Access

Agents ไม่ควร query database โดยตรง

```text
Product Agent
      |
      v
Product Tools
      |
      v
SQLite Database
```

```text
Order Agent
      |
      v
Order Tools
      |
      v
SQLite Database
```

Tools ที่มีในระบบ:

- `search_product()`
- `check_stock()`
- `get_order()`
- `track_order()`

หน้าที่ของ Agent คือเลือกและเรียก Tool ที่เหมาะสม ไม่ใช่เขียน SQL หรือเปิด database connection โดยตรง

---

# Database Scope

ระบบปัจจุบันใช้ SQLite เป็น database สำหรับข้อมูลตัวอย่างและการทดสอบ

ตารางหลัก:

- `products`
- `orders`
- `customers` สามารถใช้เป็นข้อมูลประกอบระบบเมื่อจำเป็น

ข้อมูลตัวอย่างปัจจุบัน:

### Products

```text
P001 | Nike Air Max | 42 | black | 3500.0 | 5
P002 | Nike Air Max | 43 | black | 3500.0 | 2
P003 | Adidas Ultra | 42 | white | 2900.0 | 8
```

### Orders

```text
ORD001 | C001 | P001 | 1 | shipped    | TH123456
ORD002 | C002 | P003 | 2 | processing | null
```

Database เป็น data source สำหรับ Tools และไม่ใช่หน้าที่ของ LLM Agent ที่จะสร้างข้อมูลเอง

---

# Workflow Implementation

Workflow ปัจจุบันใช้ LangGraph:

```text
START
  |
  v
Intent Agent
  |
  v
Orchestrator
  |
  +----> Product Agent ----+
  |                        |
  +----> Order Agent ------+
  |                        |
  +----> Collect Results --+
             |
             v
      Resolution Agent
             |
             v
            END
```

สำหรับ `product_inquiry` จะ route ไป Product Agent

สำหรับ `order_tracking` จะ route ไป Order Agent

สำหรับ multi-intent จะสามารถ route ไป Product Agent และ Order Agent แล้วรวบรวมผลก่อนส่งให้ Resolution Agent

---

# Demo Mode

เนื่องจาก Intent Agent และ Resolution Agent ในโหมดจริงใช้ Gemini API ระบบมี Demo Mode สำหรับทดสอบ workflow โดยไม่เรียก Gemini API

Demo Mode:

- ใช้ `DemoIntentAgent`
- ใช้ `DemoResolutionAgent`
- ใช้ Product Agent จริง
- ใช้ Order Agent จริง
- ใช้ SQLite จริง
- ใช้ LangGraph จริง

ดังนั้น Demo Mode ยังสามารถทดสอบ Multi-Agent workflow ได้โดยไม่ขึ้นกับ API quota

---

# Technology Scope

ระบบปัจจุบันใช้:

- Python
- LangGraph
- LangChain
- Google Gemini API
- `langchain-google-genai`
- Pydantic
- SQLite
- python-dotenv
- pytest

เทคโนโลยีที่สามารถพัฒนาเพิ่มภายหลัง:

- ChromaDB / RAG
- Backend API
- Frontend

การเพิ่มส่วนเหล่านี้ต้องไม่เปลี่ยนหน้าที่หลักและ contract ของ Agents

---

# Testing Scope

ระบบมี automated tests สำหรับตรวจสอบ:

- Intent Agent structured output
- Product Agent
- Order Agent
- Resolution Agent
- Multi-intent routing
- Full LangGraph workflow
- Product not found
- Order not found

เป้าหมายคือยืนยันว่าแต่ละ Agent ทำงานตาม contract และ workflow ส่งข้อมูลระหว่าง Agents ได้ถูกต้อง

---

# Explicitly Out Of Scope For Current MVP

สิ่งต่อไปนี้ยังไม่ใช่ความรับผิดชอบของ core Multi-Agent workflow:

- การชำระเงินจริง
- การคืนเงินจริง
- การแก้ไข order จริง
- การยกเลิก order จริง
- การจัดส่งจริง
- Authentication
- Deployment configuration

Backend API, Frontend และ RAG สามารถพัฒนาเพิ่มเติมภายหลัง โดยต้องไม่ทำให้ contract และหน้าที่หลักของ Agents ขัดกับ specification นี้

---

# Multi-Intent Example

### Customer Input

```text
มี Nike Air Max ไซส์ 42 สีดำไหม และ Order ORD001 อยู่ไหน
```

### Step 1: Intent Agent

```json
{
  "intent": [
    "product_inquiry",
    "order_tracking"
  ],
  "entities": {
    "product_name": "Nike Air Max",
    "size": "42",
    "color": "black",
    "order_id": "ORD001"
  }
}
```

### Step 2: Orchestrator

```json
[
  {
    "agent": "product_agent",
    "input": {
      "product_name": "Nike Air Max",
      "size": "42",
      "color": "black"
    }
  },
  {
    "agent": "order_agent",
    "input": {
      "order_id": "ORD001"
    }
  }
]
```

### Step 3: Specialist Agents

Product Agent:

```json
{
  "found": true,
  "product_id": "P001",
  "variant_id": null,
  "name": "Nike Air Max",
  "size": "42",
  "color": "black",
  "price": 3500.0,
  "stock": 5
}
```

Order Agent:

```json
{
  "success": true,
  "order_id": "ORD001",
  "status": "shipped",
  "tracking_number": "TH123456",
  "carrier": null,
  "estimated_delivery": null,
  "error": null
}
```

### Step 4: Resolution Agent

ได้รับ `customer_message` และ `results` จาก specialist agents แล้วสร้างคำตอบโดยอ้างอิงเฉพาะข้อมูลที่ได้รับ

### Step 5: Final Response

ตัวอย่าง:

```text
พบ Nike Air Max ไซส์ 42 สีดำ ราคา 3,500 บาท มีสินค้า 5 ชิ้น
และ Order ORD001 อยู่ในสถานะ shipped เลขพัสดุ TH123456
```

---

# Contract Summary

| Agent | Input Required | Output | ข้อจำกัดหลัก |
| --- | --- | --- | --- |
| Intent Agent | `user_message` | `intent`, `entities` | วิเคราะห์เท่านั้น |
| Product Agent | `product_name` | `found`, product data | ห้ามสร้างข้อมูลสินค้า |
| Order Agent | `order_id` | `success`, order data | ตรวจสอบ order เท่านั้น |
| Resolution Agent | `customer_message`, `results` | `response` | ตอบจาก results เท่านั้น |
| Orchestrator | shared workflow state + Intent result | updated `AgentState` | route, fan-out, aggregate |

---

# Core Principles

1. **Agents มีหน้าที่แยกกันชัดเจน**
2. **Intent Agent วิเคราะห์ ไม่ทำ action**
3. **Specialist Agents ใช้ Tools ในการเข้าถึงข้อมูล**
4. **Agents ไม่ควรเข้าถึง database โดยตรง**
5. **Orchestrator เป็นตัวควบคุมการ routing**
6. **รองรับ multi-intent**
7. **Resolution Agent ตอบจาก verified results เท่านั้น**
8. **ห้ามสร้างข้อมูลสินค้า Order หรือ tracking ที่ไม่มีในผลลัพธ์**
9. **Workflow ต้องสามารถทดสอบแบบ deterministic ได้ผ่าน mock agents**
10. **การเพิ่ม Backend, Frontend หรือ RAG ต้องไม่ทำลาย contract หลักของ Agents**
