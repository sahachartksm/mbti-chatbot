# 06 — Troubleshooting

---

## 🐳 Docker / MongoDB

### ❌ `Ports are not available: port 27017`
มี MongoDB อื่นรันอยู่แล้ว
```bash
# Windows
netstat -ano | findstr :27017
# kill process_id นั้น หรือเปลี่ยน port ใน docker-compose.yml:
#   ports: ["27018:27017"]
# แล้วแก้ MONGO_URI ใน .env ให้ใช้ 27018
```

### ❌ `authentication failed`
user/pass ใน `.env` ไม่ตรงกับ container
```bash
docker compose down -v    # ลบ volume
docker compose up -d      # สร้างใหม่ด้วย user/pass ใน .env
```

### ❌ Mongo healthy แต่ backend connect ไม่ได้
- เช็ค `MONGO_URI` — ต้องเป็น `mongodb://user:pass@localhost:27017/mbti?authSource=admin`
- `authSource=admin` สำคัญมาก (user สร้างใน admin db)

---

## 🐹 Go Backend

### ❌ `package X is not in GOROOT`
```bash
cd backend
go mod download
go mod tidy
```

### ❌ `cannot connect to mongodb`
- Docker mongo up หรือยัง? `docker compose ps`
- URI ใน `.env` ถูกไหม? (ดูข้อข้างบน)
- Firewall block?

### ❌ `AI service unreachable`
- Python service รันอยู่ไหม? `curl http://localhost:8000/health`
- ถ้ายัง → ไปส่วน Python ด้านล่าง
- `AI_SERVICE_URL` ใน `.env` = `http://localhost:8000`

### ❌ CORS error ใน browser
- เช็ค `CORS_ORIGINS` ใน `.env` รวม `http://localhost:4200`
- restart backend หลังแก้ env

---

## 🐍 Python AI Service

### ❌ `pip install` ช้า / fail
```bash
# ใช้ mirror
pip install -r requirements.txt -i https://pypi.org/simple/
# หรือ
pip install --upgrade pip setuptools wheel
```

### ❌ Python 3.12+ ติดตั้ง `sentence-transformers` fail
ใช้ Python **3.11** (แนะนำ) — 3.12 บาง dep ยังไม่รองรับ
```bash
# สร้าง venv ด้วย python 3.11
py -3.11 -m venv venv
```

### ❌ `Model file not found: models/mbti_model.pkl`
ยังไม่ได้ train:
```bash
python train.py
```

### ❌ Download sentence-transformers ช้าหรือ fail
ครั้งแรกมันจะ download ~80MB จาก HuggingFace
- ถ้า network ช้า → set `USE_SENTENCE_TRANSFORMER=false` ใน `.env` (ใช้เฉพาะ rule + logreg)
- หรือ pre-download: `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`

### ❌ `uvicorn: command not found`
- venv ยังไม่ activate
- Windows PowerShell: `venv\Scripts\Activate.ps1`
- ถ้า script blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### ❌ PyTorch install ใหญ่มาก (GB-scale)
`sentence-transformers` ต้องใช้ PyTorch — CPU version ก็ ~200MB
```bash
# install CPU only (เล็กกว่า)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers --no-deps
pip install -r requirements.txt
```

---

## 🅰️ Angular Frontend

### ❌ `ng: command not found`
```bash
npm install -g @angular/cli@17
```

### ❌ `npm install` ช้า / fail
```bash
# ใช้ cache clean
npm cache clean --force
npm install
# หรือ set registry
npm config set registry https://registry.npmjs.org/
```

### ❌ Node version ไม่ตรง (EBADENGINE)
Angular 17 ต้อง Node 18.13+ / 20.9+ LTS
```bash
node -v
# ถ้าเก่า → update หรือใช้ nvm-windows / nvm
```

### ❌ เปิด http://localhost:4200 ได้แต่ "Cannot fetch questions"
- เช็ค Chrome DevTools → Console / Network → ดู error
- น่าจะ backend ไม่ทำงาน หรือ CORS

### ❌ Hot reload ไม่ work
- ลอง restart `ng serve`
- Windows + WSL ต้องตั้ง `WATCHPACK_POLLING=true` (rare)

---

## 🧪 Quick health checklist (run ทุกอันดูทีละตัว)

```bash
# 1. Docker running?
docker ps

# 2. Mongo reachable?
docker exec -it chatbot-mongo mongosh -u admin -p admin123 --eval "db.runCommand({ping:1})"

# 3. AI up?
curl http://localhost:8000/health

# 4. Go up?
curl http://localhost:8080/api/health

# 5. Angular dev server?
curl -I http://localhost:4200
```

ถ้าข้อไหนตก → ย้อนดู section นั้น ๆ

---

## 🔁 Reset ทุกอย่าง (nuclear option)

```bash
# ปิด dev servers ทั้งหมด

# ลบ mongo data
docker compose down -v

# ลบ go build cache
cd backend && go clean -cache -modcache

# ลบ python venv
cd ai-service && rmdir /s /q venv

# ลบ node_modules
cd frontend && rmdir /s /q node_modules
del package-lock.json

# แล้วเริ่ม setup ใหม่ตาม README step-by-step
```

---

## 💬 ยัง stuck?
- อ่าน log ทุก terminal ให้ครบก่อน (ส่วนใหญ่บอก error ตรงตัว)
- เช็ค `.env` ให้ครบ + ถูก
- ตรวจ firewall / antivirus block port ไม่
- ลอง restart Docker Desktop
