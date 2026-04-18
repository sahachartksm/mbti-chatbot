# 08 — Docker Compose: รัน Stack ทั้งหมดด้วยคำสั่งเดียว

> **เขียนเมื่อ:** 2026-04-18 เวลา 17:00 (UTC+07:00)
> **Context:** เดิม docker-compose มีแค่ MongoDB → ขยายให้รันครบทั้ง 4 services ด้วย `docker compose up`

---

## 🎯 เป้าหมาย

**ก่อน:**
```
Terminal 1: docker compose up      (mongo เท่านั้น)
Terminal 2: cd ai-service && venv\Scripts\activate && uvicorn ...
Terminal 3: cd backend && go run .
Terminal 4: cd frontend && npm start
```
ต้องเปิด 4 terminals + จำคำสั่ง + install tools ทุกตัวเอง

**หลัง:**
```
Terminal 1: docker compose up --build
```
จบ — ทุกอย่างขึ้นมาตามลำดับ พร้อม hot reload

---

## 🏗️ Architecture

```
┌──────────────────────────────── Host (Windows) ────────────────────────────────┐
│                                                                                │
│  Browser                                                                       │
│    ├── localhost:4200  ◄──────────┐                                            │
│    ├── localhost:8080  ◄──────┐   │                                            │
│    ├── localhost:8000  ◄──┐   │   │                                            │
│    └── localhost:8081  ◄─┐│   │   │                                            │
│                          ││   │   │                                            │
│  ┌───────────────────────┼┼───┼───┼──── Docker Network (chatbot-net) ─────────┐│
│  │                       ▼│   │   │                                           ││
│  │  ┌─────────────┐ ┌────▼┐ ┌─▼───┐ ┌──────────┐                              ││
│  │  │chatbot-mongo│ │mongo│ │back │ │frontend  │                              ││
│  │  │    :27017   │ │-ui  │ │end  │ │ng serve  │                              ││
│  │  │             │ │:8081│ │:8080│ │  :4200   │                              ││
│  │  └──────┬──────┘ └──┬──┘ └──┬──┘ └─────┬────┘                              ││
│  │         │           │       │          │                                   ││
│  │         │  mongo    │       │          │                                   ││
│  │         ◄───────────┘       │          │                                   ││
│  │         │                   │          │                                   ││
│  │         │  mongo://mongo:27017         │                                   ││
│  │         ◄───────────────────┤          │                                   ││
│  │                             │          │                                   ││
│  │  ┌──────────────┐           │          │                                   ││
│  │  │  chatbot-ai  │           │          │                                   ││
│  │  │    :8000     │◄──────────┘          │                                   ││
│  │  │              │   http://ai:8000     │                                   ││
│  │  └──────────────┘                      │                                   ││
│  │         ▲                              │                                   ││
│  │         │ /api proxy                   │                                   ││
│  │         └──────────────────────────────┘                                   ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

**จุดสำคัญ:**
- Browser รันนอก Docker → ใช้ `localhost:PORT` (docker port forward)
- Container คุยกันเอง → ใช้ **service name** (`mongo`, `ai`, `backend`) ผ่าน Docker DNS ของ internal network

---

## 📝 Dockerfile ของแต่ละ service

### 1. `ai-service/Dockerfile` — ทำไมต้องเช็คว่าเทรนหรือยัง

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y gcc g++ curl
WORKDIR /app

# Layer 1: deps (cache-friendly — เปลี่ยน requirements.txt ค่อย rebuild)
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Layer 2: source
COPY . ./
RUN mkdir -p /app/models

# Entrypoint: train ถ้ายังไม่มีโมเดล
CMD ["sh", "-c", "[ -f models/mbti_model.pkl ] || python train.py; exec uvicorn app:app --host 0.0.0.0 --port 8000 --reload"]
```

**หลักการ:**
1. **Multi-layer caching** — deps แยกก่อน source → rebuild เร็วถ้าแก้แค่โค้ด
2. **Lazy training** — container boot ครั้งแรกจะ train; ครั้งต่อไป model .pkl อยู่ใน volume แล้ว ข้ามได้
3. **`--host 0.0.0.0`** — บังคับให้ listen ทุก interface ไม่ใช่แค่ loopback (ไม่งั้น port forward ไม่ work)
4. **`--reload`** — uvicorn auto-restart เมื่อโค้ดเปลี่ยน (ต้อง pair กับ volume mount)

### 2. `backend/Dockerfile` — ง่ายที่สุด

```dockerfile
FROM golang:1.23-alpine
RUN apk add --no-cache git curl
WORKDIR /app

COPY go.mod go.sum* ./
RUN go mod download 2>/dev/null || true

COPY . ./
RUN go mod tidy      # gen go.sum ถ้ายังไม่มี

CMD ["sh", "-c", "go mod tidy && go run ."]
```

**หลักการ:**
- `go run .` compile + run ใน command เดียว
- **ไม่มี hot reload** — ถ้าจะ hot reload ต้อง install [`air`](https://github.com/air-verse/air) (เลือกใช้หรือไม่ก็ได้)

### 3. `frontend/Dockerfile` — ต้องบังคับ polling

```dockerfile
FROM node:20-alpine
WORKDIR /app

ENV CHOKIDAR_USEPOLLING=true
ENV WATCHPACK_POLLING=true

COPY package*.json ./
RUN npm install

COPY . ./

CMD ["npx", "ng", "serve", "--host", "0.0.0.0", "--port", "4200", "--poll", "1000"]
```

**หลักการ:**
- **`CHOKIDAR_USEPOLLING=true`** + **`--poll 1000`** — บังคับ polling file watcher
  - ทำไม? → Docker Desktop Windows + bind mount → inotify file events **ไม่ทำงาน**
  - Polling ทุก 1s ช้ากว่า inotify แต่ stable
- **`--host 0.0.0.0`** — เหตุผลเดียวกับ uvicorn

---

## 🐳 `docker-compose.yml` — โครงสร้างและเหตุผล

### Block 1: Services (4 ตัว + 1 UI)

```yaml
services:
  mongo:          # database
  mongo-express:  # admin UI (optional)
  ai:             # FastAPI + sklearn + SBERT
  backend:        # Go chi server
  frontend:       # Angular dev server
```

### Block 2: Dependency chain (startup order)

```yaml
mongo:
  healthcheck: [mongosh ping]     # สุขภาพ check

ai:
  healthcheck: [curl /health]      # รอ model load + SBERT ready

backend:
  depends_on:
    mongo: { condition: service_healthy }
    ai:    { condition: service_healthy }    # รอ mongo + ai healthy ก่อน

frontend:
  depends_on:
    backend: { condition: service_started }  # รอแค่ backend start (ไม่ต้อง healthy)
```

**ผลลัพธ์:** `docker compose up` จะ boot ตามลำดับ: mongo → ai → backend → frontend โดยอัตโนมัติ

### Block 3: Volumes — 2 จุดประสงค์

```yaml
volumes:
  # 1. Persistent data (ไม่หายเมื่อ container recreate)
  mongo_data:       # Mongo database files
  ai_models:        # Trained .pkl (ไม่ต้อง retrain ทุกครั้ง)
  hf_cache:         # SBERT model cache (~90MB download ครั้งเดียว)
  
  # 2. Dep caches (build เร็วขึ้น)
  go_mod_cache:     # Go module downloads
  go_build_cache:   # Go compiled artifacts
```

### Block 4: Bind mounts — hot reload

```yaml
ai:
  volumes:
    - ./ai-service:/app                # แก้โค้ดบน host → container เห็นทันที
    - /app/venv                        # anonymous volume ซ่อน host venv/
    - ai_models:/app/models            # named volume override bind mount
```

**Trick ที่น่ารู้:** `/app/venv` (anonymous volume) วางทับ bind mount เพื่อ **ซ่อน** host folder จาก container เช่น host มี `venv/` จาก native dev แต่ไม่อยากเอาเข้า container

### Block 5: Network — internal DNS

```yaml
networks:
  chatbot-net:
    driver: bridge
```

ทุก service join network นี้ → เรียกกันด้วย service name ได้: `http://ai:8000`, `mongodb://mongo:27017`

---

## 🔥 Hot reload mechanism

| Service | วิธีทำ | Latency |
|---|---|---|
| **ai** (Python) | uvicorn `--reload` + `WATCHFILES_FORCE_POLLING=true` | ~1s |
| **frontend** (Angular) | `--poll 1000` + `CHOKIDAR_USEPOLLING=true` | ~2s |
| **backend** (Go) | ไม่มี (ต้อง `docker compose restart backend`) | manual |
| **mongo** | n/a | - |

**ทำไม Go ไม่มี hot reload out-of-the-box?** 
- Go compiled binary ต้อง recompile จึงต้องใช้ tool อย่าง `air`, `reflex`, `realize`
- Scope นี้ยอมรับ manual restart เพื่อความเรียบง่าย

---

## 🎭 Environment variables flow

```
.env (บน host)
    │
    │ docker-compose อ่าน + expand ${VAR}
    ▼
docker-compose.yml  environment:
    ├── mongo:    MONGO_INITDB_ROOT_USERNAME=${MONGO_USER}
    ├── backend:  MONGO_URI=mongodb://admin:admin123@mongo:27017/...
    ├── backend:  AI_SERVICE_URL=http://ai:8000
    └── frontend: API_TARGET=http://backend:8080
    │
    ▼
Container env (process.env.XXX)
    │
    ▼
Application code
```

### จุดสำคัญ

- **AI_SERVICE_URL สำหรับ backend ใน docker** = `http://ai:8000` (ไม่ใช่ `localhost:8000`)
- **MONGO_URI host ส่วน** = `mongo` (service name) ไม่ใช่ `localhost`
- **Browser เห็น** = `localhost:PORT` เสมอ (ภายนอก docker)

---

## 🆚 เปรียบเทียบ Docker vs Native dev

| หัวข้อ | Native | Docker |
|---|---|---|
| **เริ่มใช้งาน** | 4 terminals + install ทุก tool | `docker compose up` |
| **Memory** | ~500 MB | ~2-3 GB |
| **CPU** | ต่ำ | กลาง (container overhead) |
| **First time setup** | ติดตั้ง Go, Python, Node, Mongo | ติดตั้ง Docker อย่างเดียว |
| **Hot reload** | เร็ว (inotify) | ช้าลงเล็กน้อย (polling) |
| **Onboard เพื่อนใหม่** | ต้องสอน install หลายอย่าง | clone + `docker compose up` |
| **Production parity** | ต่ำ — dev กับ prod environment ต่าง | สูง — same image |

**กฎ:** ถ้า dev คนเดียวบ่อย ๆ → native, ถ้า onboard ทีมหรือต้อง demo → docker

---

## 🚨 Gotchas ที่ต้องรู้

### 1. First build ช้ามาก (~10-15 นาที)
- torch 2.5+ คือ 2GB
- sentence-transformers pull tokenizers, transformers ฯลฯ
- npm install ~300MB

### 2. First startup ช้า (~1-2 นาที)
- `ai` container: train model + download SBERT
- `backend` รอ `ai` healthy (`start_period: 120s`)

### 3. File watching บน Windows
- **ต้อง** ใช้ polling (env vars + `--poll`)
- Native dev บน Windows file watching ดีกว่า docker

### 4. Anonymous volumes (`- /app/node_modules`)
- ใช้ซ่อน host folder จาก bind mount
- แต่เมื่อ container recreate → anonymous volume หายด้วย → ต้อง reinstall

### 5. `docker compose down` vs `down -v`
- `down` — ลบ container, keep volumes (data ยังอยู่)
- `down -v` — ลบ volumes ด้วย (data หาย — ระวัง!)

---

## 🔧 Commands cheat sheet

```cmd
docker compose up --build       # build + run (foreground)
docker compose up -d            # run background
docker compose logs -f          # stream logs ทุก service
docker compose logs -f ai       # เฉพาะ service เดียว
docker compose ps               # status
docker compose restart backend  # restart 1 service
docker compose exec ai bash     # shell ใน container (debug)
docker compose down             # stop ทุก service
docker compose down -v          # stop + ลบ data
docker compose build ai         # rebuild แค่ 1 image
```

---

## 🎓 Summary

**Docker compose คือ orchestrator** — declarative (YAML) กำหนดว่าต้องมี services อะไร, คุยกันยังไง, start order ยังไง, data เก็บที่ไหน

**Pattern ที่ใช้:**
1. แต่ละ service มี Dockerfile ของตัวเอง (single responsibility)
2. Compose glue ทุกอย่างเข้าด้วยกัน (networking, volumes, env, deps)
3. Bind mount source → hot reload (dev); multi-stage build → slim image (prod — TODO)
4. Healthcheck + depends_on condition → startup order ถูกต้อง

**Trade-off:** convenience ↔ resource usage. เลือกตาม use case

---

👉 อ้างอิง: [07-training-walkthrough.md](./07-training-walkthrough.md) สำหรับ progress log
