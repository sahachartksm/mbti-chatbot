# 🧠 MBTI Personality Chatbot

Chatbot ทายลักษณะนิสัยโดยอิงทฤษฎี **MBTI (Myers-Briggs Type Indicator)** 16 แบบ  
ตอบคำถามผ่านเว็บ → AI วิเคราะห์ → แสดงผลประเภทบุคลิกภาพ + คำอธิบายละเอียด

---

## 🏛️ Tech Stack

| ส่วน | เทคโนโลยี |
|------|-----------|
| **Frontend** | Angular 17 (standalone components, signals) |
| **Backend API** | Go 1.22 (net/http + chi router) |
| **AI Service** | Python 3.11 (FastAPI + scikit-learn + sentence-transformers) |
| **Database** | MongoDB 7 (ผ่าน Docker Compose) |
| **ภาษาคำถาม** | ไทย/อังกฤษ (toggle ได้) |

```
┌──────────┐   REST   ┌──────────┐  HTTP  ┌─────────────┐
│ Angular  │ ───────▶ │  Go API  │ ─────▶ │ Python AI   │
│  :4200   │          │  :8080   │        │   :8000     │
└──────────┘          └────┬─────┘        └─────────────┘
                           │
                           ▼
                      ┌────────┐
                      │MongoDB │
                      │ :27017 │
                      └────────┘
```

---

## 📚 ลำดับการอ่านเอกสาร (สำหรับคนใหม่)

แนะนำอ่านตามลำดับนี้:

| # | ไฟล์ | เนื้อหา |
|---|------|---------|
| 1 | **[README.md](./README.md)** (ไฟล์นี้) | ภาพรวม + วิธี setup + run |
| 2 | [docs/01-architecture.md](./docs/01-architecture.md) | สถาปัตยกรรม + data flow |
| 3 | [docs/05-mbti-theory.md](./docs/05-mbti-theory.md) | ทฤษฎี MBTI 4 dimensions + 16 types |
| 4 | [docs/02-ai-model.md](./docs/02-ai-model.md) | Model ที่ใช้ + วิธีเทรน + รายละเอียด |
| 5 | [docs/03-api.md](./docs/03-api.md) | REST API reference |
| 6 | [docs/04-code-walkthrough.md](./docs/04-code-walkthrough.md) | ไล่โค้ดทีละส่วน (backend, AI, frontend) |
| 7 | [docs/06-troubleshooting.md](./docs/06-troubleshooting.md) | แก้ปัญหาที่พบบ่อย |

---

## ✅ Prerequisites

ติดตั้งให้ครบก่อนเริ่ม (เช็คด้วยคำสั่งในวงเล็บ):

| Tool | Version | ตรวจสอบ |
|------|---------|---------|
| **Docker Desktop** | latest | `docker --version` และ `docker compose version` |
| **Go** | 1.22+ | `go version` |
| **Node.js** | 20 LTS+ | `node -v` |
| **npm** | 10+ | `npm -v` |
| **Python** | 3.11 (แนะนำ 3.11 หลีกเลี่ยง 3.12 เพราะบาง lib ยังไม่รองรับ) | `python --version` |
| **Angular CLI** | 17 | `ng version` หรือ `npm i -g @angular/cli@17` |

> Windows: แนะนำให้รัน Go และ Python บน **PowerShell** หรือ **cmd** — Angular และ Docker ใช้ได้ทุก shell

---

## 🚀 Quick Start (ครั้งแรก)

### Step 1 — Clone / เข้า project folder
```bash
cd C:\Users\test1\Desktop\chatbot
```

### Step 2 — ตั้งค่า environment
คัดลอกไฟล์ตัวอย่าง:
```bash
# Windows (PowerShell/cmd)
copy .env.example .env

# Linux/Mac
cp .env.example .env
```
เปิด `.env` แล้วเปลี่ยนค่าตามต้องการ (ค่า default ใช้ได้เลย)

### Step 3 — รัน MongoDB ด้วย Docker Compose
```bash
docker compose up -d
```
ตรวจสอบว่ารันอยู่:
```bash
docker compose ps
# ควรเห็น chatbot-mongo STATUS: running (healthy)
```
ปิดเมื่อเลิกใช้งาน:
```bash
docker compose down
# ถ้าต้องการลบ data ด้วย
docker compose down -v
```

### Step 4 — เตรียม AI Service (Python)

#### 4.1 สร้าง virtual environment + ติดตั้ง dependencies
```bash
cd ai-service
python -m venv venv

# activate (Windows PowerShell)
venv\Scripts\Activate.ps1
# activate (Windows cmd)
venv\Scripts\activate.bat
# activate (Linux/Mac)
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

#### 4.2 เทรนโมเดล (ครั้งแรกเท่านั้น หรือเมื่อต้องการ re-train)
```bash
python train.py
```
จะได้ไฟล์ `models/mbti_model.pkl` และ `models/scaler.pkl`
> รายละเอียดการเทรน ดู [docs/02-ai-model.md](./docs/02-ai-model.md)

#### 4.3 รัน AI service
```bash
# ยังอยู่ใน ai-service/ กับ venv activated
uvicorn app:app --reload --port 8000
```
ทดสอบ: เปิด <http://localhost:8000/docs> (Swagger UI)

### Step 5 — รัน Backend (Go)

เปิด **terminal ใหม่**:
```bash
cd C:\Users\test1\Desktop\chatbot\backend

# ติดตั้ง deps ครั้งแรก
go mod download

# รัน
go run .
```
ควรเห็น:
```
✓ MongoDB connected
✓ AI service reachable
🚀 Go server listening on :8080
```
ทดสอบ: `curl http://localhost:8080/api/health`

### Step 6 — รัน Frontend (Angular)

เปิด **terminal ใหม่อีก**:
```bash
cd C:\Users\test1\Desktop\chatbot\frontend

# ติดตั้ง deps ครั้งแรก
npm install

# รัน dev server
npm start
# หรือ
ng serve
```
เปิดเบราว์เซอร์: <http://localhost:4200>

### Step 7 — ใช้งาน!
1. กด "เริ่มทำแบบทดสอบ"
2. ตอบคำถาม 20 ข้อ (ตัวเลือก 2-5)
3. กด "ดูผลลัพธ์"
4. ระบบจะแสดง MBTI type + คะแนนแต่ละมิติ + คำอธิบายลักษณะนิสัย

---

## 🧾 สรุปคำสั่งที่ใช้บ่อย (cheat sheet)

```bash
# MongoDB
docker compose up -d          # เริ่ม
docker compose logs -f mongo  # ดู log
docker compose down           # หยุด
docker compose down -v        # หยุด + ลบ data

# AI Service (ต้อง cd ai-service + activate venv ก่อน)
uvicorn app:app --reload --port 8000
python train.py               # re-train

# Backend (ต้อง cd backend)
go run .
go test ./...                 # test
go build -o chatbot.exe .     # build binary

# Frontend (ต้อง cd frontend)
npm start                     # dev mode
npm run build                 # production build → dist/
npm test                      # unit test
```

---

## 🗂️ โครงสร้างโปรเจค

```
chatbot/
├── README.md                 ← อ่านก่อน (ไฟล์นี้)
├── docker-compose.yml        ← MongoDB
├── .env.example              ← ตัวอย่าง config
├── .gitignore
│
├── docs/                     ← เอกสารทั้งหมด
│   ├── 01-architecture.md
│   ├── 02-ai-model.md
│   ├── 03-api.md
│   ├── 04-code-walkthrough.md
│   ├── 05-mbti-theory.md
│   └── 06-troubleshooting.md
│
├── backend/                  ← Go API server
│   ├── go.mod
│   ├── main.go
│   ├── config/
│   ├── db/
│   ├── handlers/
│   ├── models/
│   ├── ai/
│   └── questions/
│
├── ai-service/               ← Python AI/ML
│   ├── requirements.txt
│   ├── app.py                ← FastAPI entrypoint
│   ├── train.py              ← train ML model
│   ├── predictor.py          ← inference
│   ├── questions_map.py      ← question → dimension
│   ├── data/
│   │   └── training_data_generator.py
│   └── models/               ← saved .pkl files
│
└── frontend/                 ← Angular SPA
    ├── package.json
    ├── angular.json
    └── src/
        ├── index.html
        ├── main.ts
        ├── styles.scss
        └── app/
            ├── app.config.ts
            ├── app.routes.ts
            ├── app.component.*
            ├── services/
            └── components/
                ├── chat/
                └── result/
```

---

## 🔁 Development Workflow (หลัง setup แล้ว)

เปิด terminal 3 หน้าต่างเลย (แนะนำใช้ Windows Terminal หรือ VSCode integrated terminal แบ่ง split):

| Terminal | Command |
|----------|---------|
| 1 | `docker compose up` (อยู่ที่ root) |
| 2 | `cd ai-service && venv\Scripts\activate && uvicorn app:app --reload --port 8000` |
| 3 | `cd backend && go run .` |
| 4 | `cd frontend && npm start` |

> Tip: สร้าง script `dev.ps1` รวบรวมคำสั่งได้

---

## 🧪 ทดสอบว่าทุกอย่างพร้อม

```bash
# 1. MongoDB
docker compose ps

# 2. AI service
curl http://localhost:8000/health
# → {"status":"ok","model_loaded":true}

# 3. Backend
curl http://localhost:8080/api/health
# → {"status":"ok","mongo":"up","ai":"up"}

# 4. Frontend
# เปิดเบราว์เซอร์ http://localhost:4200
```

---

## 🚨 ปัญหาที่พบบ่อย

ดู [docs/06-troubleshooting.md](./docs/06-troubleshooting.md) — รวมเคสและทางแก้

## 📖 ทฤษฎี + วิธีเทรน AI

ดู [docs/02-ai-model.md](./docs/02-ai-model.md) — เลือกใช้ **Logistic Regression (scikit-learn)** + **sentence-transformers (all-MiniLM-L6-v2)** สำหรับ free-text answers

---

## 📄 License
MIT (ปรับแต่งได้ตามต้องการ)
