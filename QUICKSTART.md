# ⚡ Quick Start (สรุปสั้น)

> อ่านเวอร์ชันเต็มได้ที่ [README.md](./README.md)

## ครั้งแรก — ตั้งค่าให้ครบ (one-time setup)

```powershell
# 0) เข้า project
cd C:\Users\test1\Desktop\chatbot

# 1) คัดลอก env
copy .env.example .env

# 2) เริ่ม MongoDB
docker compose up -d

# 3) ติดตั้ง + เทรน AI service
cd ai-service
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python train.py
cd ..

# 4) ติดตั้ง Go deps
cd backend
go mod download
cd ..

# 5) ติดตั้ง Angular deps
cd frontend
npm install
cd ..
```

## รันทุกครั้งที่ dev — เปิด 4 terminal

**Terminal 1 — MongoDB** (root folder)
```powershell
docker compose up
```

**Terminal 2 — AI service** (`ai-service/`)
```powershell
venv\Scripts\Activate.ps1
uvicorn app:app --reload --port 8000
```

**Terminal 3 — Go backend** (`backend/`)
```powershell
go run .
```

**Terminal 4 — Angular** (`frontend/`)
```powershell
npm start
```

เปิดเบราว์เซอร์: <http://localhost:4200>

## เช็คว่าทุกอย่าง up

```powershell
curl http://localhost:8000/health   # AI
curl http://localhost:8080/api/health   # Backend
```

ปัญหา → ดู [docs/06-troubleshooting.md](./docs/06-troubleshooting.md)
