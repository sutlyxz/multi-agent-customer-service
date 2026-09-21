# Project Specification

## Objective

กำหนด JSON contract และ workflow สำหรับระบบ Multi-Agent Customer Service โดยเอกสารนี้กำหนดเฉพาะขอบเขต, รูปแบบข้อมูล และการส่งต่องานระหว่าง Agents ยังไม่มี implementation ของ Agent

## Agents

ระบบมี Agents เท่านี้เท่านั้น:

1. Intent Agent
2. Product Agent
3. Order Agent
4. Resolution Agent
5. Orchestrator

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
    |---------------------------|
                      v
            Resolution Agent
                      |
                      v
                Customer
```

ลำดับการทำงานมาตรฐาน:

1. Orchestrator รับ `user_message` และส่งให้ Intent Agent
2. Intent Agent วิเคราะห์ `intent` และ `entities` เท่านั้น
3. Orchestrator อ่าน intent แล้วเลือก Agent ที่เหมาะสม
4. Orchestrator สร้าง task จาก entities และส่งให้ Product Agent หรือ Order Agent
5. Orchestrator รวบรวมผลลัพธ์ทั้งหมดไว้ใน `results`
6. Orchestrator ส่ง `customer_message` และ `results` ให้ Resolution Agent
7. Resolution Agent สร้างคำตอบสุดท้ายจากข้อมูลใน `results` เท่านั้น

การ routing:

| Intent | Agent ที่เรียก | Task ที่ส่ง |
| --- | --- | --- |
| `product_inquiry` | Product Agent | `product_name`, `size`, `color` |
| `order_tracking` | Order Agent | `order_id` |
| `return_request` | Resolution Agent | ไม่มี action agent ใน MVP; ส่ง intent และข้อมูลที่มีใน `results` |
| `general_question` | Resolution Agent | ไม่มี action agent; ส่ง intent และข้อมูลที่มีใน `results` |

สำหรับ multi-intent ให้ Orchestrator สร้าง task แยกตาม intent ที่พบ, เรียก Product Agent และ/หรือ Order Agent ตามความเหมาะสม, รวบรวมผลลัพธ์ทั้งหมด แล้วเรียก Resolution Agent เพียงครั้งเดียว

`intent` เป็น string เมื่อพบ intent เดียว และเป็น array ของค่า intent เมื่อพบหลาย intent เพื่อรองรับ multi-intent โดยใช้ค่าในรายการ MVP เท่านั้น

## JSON Contract

### 1. Intent Agent

หน้าที่คือวิเคราะห์ข้อความเท่านั้น ห้ามตอบลูกค้า, ค้น database หรือทำ order action

#### Input

Required fields:

```json
{
   "user_message": "ขอเช็กเสื้อสีดำไซซ์ M"
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `user_message` | string | Yes | ข้อความต้นฉบับจากลูกค้า ต้องไม่เป็นค่าว่าง |

#### Output

```json
{
   "intent": "product_inquiry",
   "entities": {
      "product_name": "เสื้อ",
      "size": "M",
      "color": "ดำ",
      "order_id": null
   }
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `intent` | string or array of strings | Yes | ค่าเดียวหรือหลายค่าจาก intent ที่รองรับใน MVP |
| `entities` | object | Yes | ข้อมูลที่สกัดได้จากข้อความ |
| `entities.product_name` | string or null | No | ชื่อสินค้า |
| `entities.size` | string or null | No | ขนาดสินค้า |
| `entities.color` | string or null | No | สีสินค้า |
| `entities.order_id` | string or null | No | หมายเลขคำสั่งซื้อ |

Intent ที่รองรับใน MVP:

- `product_inquiry`
- `order_tracking`
- `return_request`
- `general_question`

### 2. Product Agent

รับผิดชอบการค้นหาข้อมูลสินค้าเท่านั้น โดยไม่มี order action

#### Input

```json
{
   "product_name": "เสื้อ",
   "size": "M",
   "color": "ดำ"
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `product_name` | string | Yes | ชื่อสินค้าที่ต้องการค้นหา |
| `size` | string or null | No | ขนาดสินค้า ถ้าไม่มีข้อมูลให้เป็น `null` |
| `color` | string or null | No | สีสินค้า ถ้าไม่มีข้อมูลให้เป็น `null` |

#### Output

เมื่อค้นพบสินค้า:

```json
{
   "found": true,
   "product_id": "SKU-001",
   "name": "เสื้อ",
   "price": 499,
   "stock": 12
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `found` | boolean | Yes | ระบุว่าพบสินค้าหรือไม่ |
| `product_id` | string or null | Yes | รหัสสินค้า; เป็น `null` เมื่อไม่พบ |
| `name` | string or null | Yes | ชื่อสินค้า; เป็น `null` เมื่อไม่พบ |
| `price` | number or null | Yes | ราคาสินค้า; เป็น `null` เมื่อไม่พบ |
| `stock` | integer or null | Yes | จำนวนคงเหลือ; เป็น `null` เมื่อไม่พบ |

เมื่อ `found` เป็น `false` ค่า field สินค้าที่เหลือทั้งหมดต้องเป็น `null` และห้ามสร้างข้อมูลสินค้าเอง

### 3. Order Agent

รับผิดชอบการตรวจสอบข้อมูลคำสั่งซื้อเท่านั้น

#### Input

```json
{
   "order_id": "ORD-1001"
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `order_id` | string | Yes | หมายเลขคำสั่งซื้อ |

#### Output

เมื่อค้นพบคำสั่งซื้อ:

```json
{
   "success": true,
   "data": {
      "order_id": "ORD-1001",
      "status": "shipped",
      "tracking_number": "TH123456789"
   }
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `success` | boolean | Yes | ระบุว่าการตรวจสอบสำเร็จหรือไม่ |
| `data` | object or null | Yes | ข้อมูลคำสั่งซื้อเมื่อสำเร็จ; เป็น `null` เมื่อไม่สำเร็จ |
| `data.order_id` | string | Yes เมื่อ `success=true` | หมายเลขคำสั่งซื้อ |
| `data.status` | string | Yes เมื่อ `success=true` | สถานะคำสั่งซื้อ |
| `data.tracking_number` | string or null | Yes เมื่อ `success=true` | หมายเลขติดตามพัสดุ ถ้ายังไม่มีให้เป็น `null` |

### 4. Resolution Agent

มีหน้าที่สร้างคำตอบสุดท้ายจากข้อมูลที่ได้รับเท่านั้น ห้ามสร้างข้อมูลที่ไม่มีใน `results`

#### Input

```json
{
   "customer_message": "ช่วยเช็กเสื้อสีดำไซซ์ M และออเดอร์ ORD-1001",
   "results": [
      {
         "agent": "Product Agent",
         "result": {
            "found": true,
            "product_id": "SKU-001",
            "name": "เสื้อ",
            "price": 499,
            "stock": 12
         }
      }
   ]
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `customer_message` | string | Yes | ข้อความต้นฉบับที่ใช้เป็นบริบทในการตอบ |
| `results` | array | Yes | ผลลัพธ์จาก Agents ก่อนหน้า อาจเป็น array ว่างได้ |

#### Output

```json
{
   "response": "พบเสื้อ ราคา 499 บาท มีสินค้า 12 ชิ้น"
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `response` | string | Yes | คำตอบสุดท้ายที่อ้างอิงได้เฉพาะข้อมูลใน `results` |

### 5. Orchestrator

Orchestrator ไม่วิเคราะห์ข้อมูลเชิงธุรกิจและไม่สร้างข้อมูลผลลัพธ์เอง มีหน้าที่อ่าน intent, เลือก Agent, สร้าง task, รองรับหลาย intent, รวบรวมผลลัพธ์ และส่งต่อให้ Resolution Agent

#### Input

```json
{
   "user_message": "ช่วยเช็กเสื้อสีดำไซซ์ M และออเดอร์ ORD-1001"
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `user_message` | string | Yes | ข้อความจากลูกค้า |

#### Output เมื่อสำเร็จ

```json
{
   "success": true,
   "data": {
      "intent": ["product_inquiry", "order_tracking"],
      "results": [
         {
            "agent": "Product Agent",
            "result": {
               "found": true,
               "product_id": "SKU-001",
               "name": "เสื้อ",
               "price": 499,
               "stock": 12
            }
         },
         {
            "agent": "Order Agent",
            "result": {
               "success": true,
               "data": {
                  "order_id": "ORD-1001",
                  "status": "shipped",
                  "tracking_number": "TH123456789"
               }
            }
         }
      ],
      "response": "เสื้อราคา 499 บาท มีสินค้า 12 ชิ้น และออเดอร์ ORD-1001 อยู่ระหว่างจัดส่ง"
   }
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `success` | boolean | Yes | ระบุว่างานทั้งหมดสำเร็จหรือไม่ |
| `data` | object | Yes เมื่อ `success=true` | ผลลัพธ์รวมจาก workflow |
| `data.intent` | string or array | Yes เมื่อ `success=true` | intent ที่ Orchestrator ใช้ routing |
| `data.results` | array | Yes เมื่อ `success=true` | ผลลัพธ์จาก Product Agent และ/หรือ Order Agent |
| `data.response` | string | Yes เมื่อ `success=true` | response จาก Resolution Agent |

## Common Error Format

ทุก Agent และ Orchestrator ที่ทำงานไม่สำเร็จต้องส่งรูปแบบ error เดียวกัน:

```json
{
   "success": false,
   "error": {
      "code": "MISSING_REQUIRED_FIELD",
      "message": "order_id is required",
      "details": {
         "field": "order_id"
      }
   }
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `success` | boolean | Yes | ต้องเป็น `false` |
| `error` | object | Yes | รายละเอียดข้อผิดพลาด |
| `error.code` | string | Yes | รหัสข้อผิดพลาด เช่น `INVALID_INPUT`, `MISSING_REQUIRED_FIELD`, `AGENT_FAILURE` |
| `error.message` | string | Yes | คำอธิบายข้อผิดพลาดที่อ่านได้ |
| `error.details` | object or null | No | รายละเอียดเพิ่มเติมที่ไม่เป็นความลับ |

## Success Format

- Intent Agent ใช้ object ที่มี `intent` และ `entities`
- Product Agent ใช้ object ที่มี `found` และข้อมูลสินค้า หรือค่า `null` เมื่อไม่พบ
- Order Agent ใช้ object ที่มี `success` และ `data`
- Resolution Agent ใช้ object ที่มี `response`
- Orchestrator ใช้ envelope `{ "success": true, "data": {...} }` และต้องมี `intent`, `results`, `response` ใน `data`
- ห้ามใช้ success format ปะปนกับ error format ใน response เดียวกัน

## Multi-Intent Example

Input ของ Orchestrator:

```json
{
   "user_message": "มีเสื้อสีดำไซซ์ M ไหม และออเดอร์ ORD-1001 ถึงไหนแล้ว"
}
```

Intent Agent output:

```json
{
   "intent": ["product_inquiry", "order_tracking"],
   "entities": {
      "product_name": "เสื้อ",
      "size": "M",
      "color": "ดำ",
      "order_id": "ORD-1001"
   }
}
```

Orchestrator ต้องสร้างและส่งสอง tasks:

```json
[
   {
      "agent": "Product Agent",
      "input": {
         "product_name": "เสื้อ",
         "size": "M",
         "color": "ดำ"
      }
   },
   {
      "agent": "Order Agent",
      "input": {
         "order_id": "ORD-1001"
      }
   }
]
```

จากนั้นส่งผลลัพธ์ทั้งสองรายการไปยัง Resolution Agent ใน `results` เดียวกัน ห้ามตัดทอนผลลัพธ์หรือสร้างข้อมูลเพิ่มเติม

## Contract Summary

| Agent | Input Required | Input Optional | Output Success | ข้อจำกัดหลัก |
| --- | --- | --- | --- | --- |
| Intent Agent | `user_message` | ไม่มี | `intent`, `entities` | วิเคราะห์เท่านั้น ห้ามตอบลูกค้า/ค้น database/order action |
| Product Agent | `product_name` | `size`, `color` | `found`, `product_id`, `name`, `price`, `stock` | ห้ามสร้างข้อมูลสินค้าเมื่อไม่พบ |
| Order Agent | `order_id` | ไม่มี | `success`, `data` | ตรวจสอบคำสั่งซื้อเท่านั้น |
| Resolution Agent | `customer_message`, `results` | ไม่มี | `response` | ตอบจาก `results` เท่านั้น ห้าม hallucinate |
| Orchestrator | `user_message` | ไม่มี | `success`, `data.intent`, `data.results`, `data.response` | route, fan-out multi-intent, aggregate และส่งต่อ |

## Technology Scope

- Python
- LangGraph
- LangChain
- OpenAI API
- python-dotenv

## Explicitly Out Of Scope

- Agent implementation
- Database
- Frontend framework
- Backend framework
- RAG
- API
- Authentication
- Deployment configuration