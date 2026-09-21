# Multi-Agent Customer Service

โครงสร้างเริ่มต้นสำหรับส่วน AI Agents และ Agent Workflow ของระบบ Customer Service / Order Automation

## Scope

โปรเจกต์นี้ครอบคลุมเฉพาะโครงสร้างสำหรับ:

- Intent Agent
- Orchestrator
- Product Agent
- Order Agent
- Resolution Agent
- Shared state และ workflow ของ LangGraph
- Prompt definitions

ยังไม่มี implementation จริงของ agent หรือ workflow รวมถึงไม่มี database, frontend, backend, RAG หรือ API

## File Responsibilities

| File | หน้าที่ |
| --- | --- |
| `agents/intent.py` | Placeholder สำหรับจำแนก intent ของลูกค้า |
| `agents/product.py` | Placeholder สำหรับจัดการคำถามเกี่ยวกับสินค้า |
| `agents/order.py` | Placeholder สำหรับจัดการคำขอเกี่ยวกับคำสั่งซื้อ |
| `agents/resolution.py` | Placeholder สำหรับสร้างคำตอบหรือแนวทางแก้ไขสุดท้าย |
| `agents/orchestrator.py` | Placeholder สำหรับควบคุมการส่งต่องานระหว่าง agents |
| `state.py` | จุดวาง schema ของ shared state ที่ workflow ใช้ร่วมกัน |
| `workflow.py` | จุดวางโครงสร้าง LangGraph workflow |
| `prompts.py` | จุดวาง prompts ที่ agents ใช้ร่วมกัน |
| `app.py` | จุดเริ่มต้นของแอปพลิเคชันในอนาคต |
| `tests/README.md` | ขอบเขตพื้นที่สำหรับเพิ่ม tests |
| `PROJECT_SPEC.md` | สเปกและ architecture ของส่วน agents/workflow |
| `.env.example` | ตัวอย่างตัวแปร environment สำหรับ OpenAI API key |
| `requirements.txt` | Dependency ที่จำเป็นสำหรับ agent/workflow stack |
| `.gitignore` | ไฟล์และโฟลเดอร์ที่ไม่ควรอยู่ใน version control |

## Setup

สร้าง virtual environment และติดตั้ง dependency จาก `requirements.txt` เมื่อเริ่ม implementation จริง

```bash
python -m venv .venv
pip install -r requirements.txt
```