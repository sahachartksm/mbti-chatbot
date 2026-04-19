# 10 — LLM / Ollama Setup Guide

> โหมดใหม่: ให้ผู้ใช้ **พิมพ์คำตอบเป็นข้อความอิสระ** (ไทย/อังกฤษ) 10 ข้อ แล้วส่งให้ LLM วิเคราะห์ MBTI ในบทบาท **นักจิตวิทยาขั้นสูง**
>
> เอกสารนี้บอกทุกคำสั่งที่ต้องพิมพ์เอง เพราะ IDE ติดตั้ง/รัน Ollama ให้ไม่ได้

---

## 1. ทำไมต้องใช้ LLM

โหมดเดิม (เลือกตัวเลือก a/b/c) ใช้ rule-based + scikit-learn + SBERT — แม่นในระดับแบบสอบถาม แต่**ไม่สามารถวิเคราะห์ข้อความอิสระเชิงลึก**ได้

โหมดใหม่: LLM อ่านคำตอบเป็นประโยคจริงของผู้ใช้ → ตีความเหมือนนักจิตวิทยา → ให้เหตุผลกำกับ และคะแนน 4 แกน

---

## 2. รุ่น LLM ที่แนะนำ

| Model | ขนาด | RAM | ความเหมาะสมกับงานนี้ |
|-------|------|-----|----------------------|
| **`scb10x/llama3.1-typhoon2-8b-instruct`** ⭐ | 8B (~5 GB) | 8 GB+ | **แนะนำ** — ภาษาไทยดี, reasoning ลึกพอจะเล่นบท "นักจิตวิทยา" |
| `scb10x/typhoon2-qwen2.5-7b-instruct` | 7B (~4.5 GB) | 8 GB+ | ทางเลือก — Qwen2.5 logic แรง |
| `scb10x/llama3.2-typhoon2-3b-instruct` | 3B (~2 GB) | 4 GB+ | เบาที่สุด, เหมาะถ้า RAM น้อย แต่วิเคราะห์จะตื้นกว่า |

ถ้ามี GPU / RAM เยอะ ใช้ `scb10x/llama3.1-typhoon2-70b-instruct` ได้ (แต่ไม่จำเป็น)

> **ค่า default ในโปรเจกต์**: `scb10x/llama3.1-typhoon2-8b-instruct` — เปลี่ยนได้ผ่าน env `LLM_MODEL`

---

## 3. ติดตั้ง Ollama (ทำเอง)

### Windows

ดาวน์โหลดจาก https://ollama.com/download/windows แล้วติดตั้งตามปกติ

Ollama จะรันเป็น service ที่ `http://localhost:11434` โดยอัตโนมัติ

### macOS / Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### ตรวจสอบ

```cmd
ollama --version
curl http://localhost:11434/api/tags
```

ถ้าตอบ JSON = ใช้ได้

---

## 4. Pull รุ่น LLM (ทำเองใน terminal)

```cmd
ollama pull scb10x/llama3.1-typhoon2-8b-instruct
```

ถ้าเครื่องเบา ใช้ 3B แทน:

```cmd
ollama pull scb10x/llama3.2-typhoon2-3b-instruct
```

ทดสอบว่าโหลดได้:

```cmd
ollama run scb10x/llama3.1-typhoon2-8b-instruct "สวัสดี ทดสอบ"
```

(กด `Ctrl+D` ออกจาก chat)

---

## 5. ตั้งค่า env ในโปรเจกต์

เปิด `.env` (copy จาก `.env.example` ถ้ายังไม่มี) แล้วเพิ่ม/แก้ 2 บรรทัด:

```env
# ---- LLM (Ollama) ----
# URL ของ Ollama — สำหรับรัน ai-service ใน Docker ให้ใช้ host.docker.internal
OLLAMA_URL=http://host.docker.internal:11434
LLM_MODEL=scb10x/llama3.1-typhoon2-8b-instruct
```

ถ้ารัน ai-service แบบ native (ไม่ใช้ Docker):

```env
OLLAMA_URL=http://localhost:11434
```

---

## 6. รันระบบ

### แบบ Docker Compose (แนะนำ)

> ⚠️ Ollama ต้องรันอยู่บน host **นอก** Docker — Compose จะเชื่อมผ่าน `host.docker.internal`

```cmd
docker compose up -d mongo
docker compose up ai backend frontend
```

เปิด `http://localhost:4200`

### แบบ native (ไม่ใช้ Docker)

**Terminal 1 — MongoDB:**
```cmd
docker compose up -d mongo
```

**Terminal 2 — AI Service:**
```cmd
cd ai-service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

**Terminal 3 — Backend:**
```cmd
cd backend
go run .
```

**Terminal 4 — Frontend:**
```cmd
cd frontend
npm install
npm start
```

---

## 7. ทดสอบว่า LLM ทำงาน

```cmd
curl http://localhost:8000/health
```

ควรได้:

```json
{"status":"ok","llm_ready":true,"llm_model":"scb10x/llama3.1-typhoon2-8b-instruct"}
```

ถ้า `llm_ready: false`:
- ตรวจว่า Ollama กำลังรัน: `ollama list`
- ตรวจว่า pull model ครบ: ชื่อ model ใน `.env` ต้องตรงกับที่ `ollama list` ขึ้น
- ตรวจว่า `OLLAMA_URL` ถูก — ถ้า ai-service อยู่ใน Docker ต้องใช้ `host.docker.internal`

---

## 8. แก้ปัญหาเบื้องต้น

### "connection refused" / Ollama ไม่ตอบ

Ollama service ยังไม่ขึ้น — สั่ง:

```cmd
ollama serve
```

(หรือ restart Ollama Desktop ถ้าอยู่บน Windows)

### `host.docker.internal` ใช้ไม่ได้บน Linux

เพิ่มใน `docker-compose.yml` → `services.ai`:

```yaml
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

(บน Windows/Mac ไม่ต้องตั้ง Docker ทำให้อัตโนมัติ)

### LLM ตอบช้ามาก (> 2 นาที)

- ใช้ model เล็กลง (3B)
- ติดตั้ง Ollama เวอร์ชัน GPU (CUDA/Metal) ถ้ามี GPU
- ลด `num_ctx` หรือ `max_tokens` ใน `ai-service/llm_analyzer.py`

### Timeout ใน frontend

- เพิ่ม timeout ใน `backend/handlers/analyze.go` → ปัจจุบันตั้ง 180s ถ้ายังไม่พอเพิ่มอีก
- เพิ่ม timeout ใน `backend/ai/client.go` → `http.Client{Timeout: 180 * time.Second}`

---

## 9. คำสั่งที่ใช้บ่อย

```cmd
:: ดู model ทั้งหมด
ollama list

:: ลบ model
ollama rm scb10x/llama3.2-typhoon2-3b-instruct

:: ดู log
ollama logs

:: ทดสอบ chat ตรง ๆ
ollama run scb10x/llama3.1-typhoon2-8b-instruct

:: restart Ollama service (Windows)
net stop ollama && net start ollama
```

---

## 10. สรุป checklist

- [ ] ติดตั้ง Ollama
- [ ] `ollama pull scb10x/llama3.1-typhoon2-8b-instruct`
- [ ] เพิ่ม `OLLAMA_URL` + `LLM_MODEL` ใน `.env`
- [ ] `docker compose up` หรือรัน native
- [ ] เปิด `http://localhost:4200` → ทดสอบกรอก 10 ข้อ → กดส่ง → ดูผล

---

# 🛠️ สิ่งที่ต้องทำเอง (Manual Setup) — กรณีใช้ `scb10x/llama3.1-typhoon2-8b-instruct`

> ส่วนนี้คือ **ขั้นตอนละเอียดทีละข้อ** สำหรับรุ่น 8B ที่แนะนำ
> — IDE / AI ทำให้ไม่ได้ คุณต้องพิมพ์คำสั่งเองใน terminal

## ขั้น 0 · เตรียมเครื่องให้พร้อม (สำคัญ — ทำก่อนเริ่ม)

รุ่น 8B กินทรัพยากรมากกว่า 3B ตรวจสอบเครื่องของคุณก่อน:

### ข้อกำหนดขั้นต่ำ

- **RAM**: ต้องมีอย่างน้อย **8 GB ว่าง** ขณะรัน model (แนะนำ 16 GB+)
- **Disk**: เหลือที่ว่างอย่างน้อย **6 GB** สำหรับดาวน์โหลด model
- **CPU**: รุ่นใดก็ได้ แต่ถ้ามี **GPU NVIDIA** จะเร็วกว่ามาก (ต้องการ CUDA driver)
- **Internet**: ดาวน์โหลดครั้งแรก ~5 GB

ตรวจ RAM ว่างบน Windows:

```cmd
wmic OS get FreePhysicalMemory /Value
```

(ค่าเป็น KB — ต้องมากกว่า ~8,000,000)

ถ้า RAM ไม่พอ ให้ใช้รุ่น 3B แทน โดยเปลี่ยน `LLM_MODEL` ในขั้น 5 เป็น:

```env
LLM_MODEL=scb10x/llama3.2-typhoon2-3b-instruct
```

---

## ขั้น 1 · ติดตั้ง Ollama

### Windows

1. ดาวน์โหลด installer: https://ollama.com/download/windows
2. ดับเบิลคลิกไฟล์ `.exe` ที่โหลดมา
3. คลิก **Install** (จะติดตั้งเป็น Windows service อัตโนมัติ เปิดทุกครั้งที่บูตเครื่อง)
4. หลังติดตั้ง จะมีไอคอน Ollama ที่ system tray (มุมขวาล่าง)

### ตรวจว่าติดตั้งสำเร็จ

เปิด **Command Prompt ใหม่** (สำคัญ — เพื่อให้ PATH อัปเดต) แล้วพิมพ์:

```cmd
ollama --version
```

ควรได้ผลลัพธ์ประมาณ `ollama version is 0.x.x`

ต่อมาตรวจว่า service รัน:

```cmd
curl http://localhost:11434/api/tags
```

ถ้าได้ JSON ตอบกลับ (เช่น `{"models":[]}`) = service ทำงาน ✅

ถ้า `curl: (7) Failed to connect`:

```cmd
:: เปิด service แบบ manual
ollama serve
```

(เปิดทิ้งไว้อีก tab หนึ่ง)

---

## ขั้น 2 · ดาวน์โหลดรุ่น 8B (~5 GB)

ใน Command Prompt:

```cmd
ollama pull scb10x/llama3.1-typhoon2-8b-instruct
```

**ข้อควรรู้:**

- ใช้เวลา 5-30 นาที ขึ้นกับความเร็วเน็ต
- แสดง progress bar 4-5 layers รวม ~5 GB
- ถ้าหลุดกลางทาง **รัน `ollama pull` ซ้ำ** — มันจะทำต่อจากที่ค้าง ไม่โหลดใหม่ทั้งหมด
- ถ้าขึ้น `Error: pull model manifest: file does not exist` = สะกดชื่อ model ผิด ให้ copy มาทั้งบรรทัด

### ตรวจว่าโหลดสำเร็จ

```cmd
ollama list
```

ต้องเห็นบรรทัดที่มีคำว่า `scb10x/llama3.1-typhoon2-8b-instruct` พร้อมขนาด ~5 GB

---

## ขั้น 3 · ทดสอบ model ทำงาน (สำคัญ — ก่อนต่อเข้าโปรเจกต์)

```cmd
ollama run scb10x/llama3.1-typhoon2-8b-instruct
```

จะได้ prompt `>>> ` พิมพ์ทดสอบ:

```
>>> สวัสดี คุณเป็นใคร?
```

ถ้า model ตอบกลับเป็นภาษาไทย = ✅ ใช้ได้

**หมายเหตุ:** ครั้งแรกที่รันจะช้า (โหลด model เข้า RAM ~15-30s) หลังจากนั้นจะเร็ว

กด `Ctrl+D` (หรือพิมพ์ `/bye`) เพื่อออก

### ถ้า Ollama หน่วงมาก / ค้าง

- CPU อย่างเดียว: 8B บน CPU ตอบ ~30-60 วิ ต่อครั้ง **ปกติ**
- ถ้าหน่วงกว่านี้มาก → RAM ไม่พอ, ลด model เป็น 3B
- เช็คว่ามี GPU NVIDIA: `nvidia-smi` ถ้ามี, Ollama จะใช้อัตโนมัติ

---

## ขั้น 4 · Copy `.env` และแก้ค่า

ที่ root ของโปรเจกต์ (`c:\Users\test1\Desktop\chatbot`):

```cmd
copy .env.example .env
```

เปิด `.env` ด้วย editor ใด ๆ แล้วตรวจให้มี 2 บรรทัดนี้ (ใส่ให้ถูก):

```env
OLLAMA_URL=http://host.docker.internal:11434
LLM_MODEL=scb10x/llama3.1-typhoon2-8b-instruct
```

> ⚠️ **ต้องตรงกันเป๊ะ** กับชื่อจาก `ollama list` ไม่มีช่องว่างท้ายบรรทัด

ถ้าจะรัน ai-service **แบบ native (ไม่ใช้ Docker)** ให้เปลี่ยนเป็น:

```env
OLLAMA_URL=http://localhost:11434
```

---

## ขั้น 5 · รันโปรเจกต์ (เลือก A หรือ B)

### 🅰 ทางเลือก A — Docker Compose (แนะนำ)

เปิด Command Prompt ที่ root โปรเจกต์ แล้ว:

```cmd
:: หยุด container เก่า (ถ้ามี) เพราะ env เปลี่ยนแล้ว
docker compose down

:: build ใหม่เพราะ requirements.txt เพิ่ม httpx
docker compose build ai backend

:: เปิด MongoDB ก่อน
docker compose up -d mongo

:: รอ 5 วิ แล้วเปิดที่เหลือ (เห็น log แบบ foreground)
docker compose up ai backend frontend
```

เปิด browser: http://localhost:4200

### 🅱 ทางเลือก B — Native (ไม่ใช้ Docker)

ต้องเปิด 4 terminal พร้อมกัน:

**Terminal 1 — MongoDB (Docker อย่างเดียว):**

```cmd
docker compose up -d mongo
```

**Terminal 2 — AI Service:**

```cmd
cd c:\Users\test1\Desktop\chatbot\ai-service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
set OLLAMA_URL=http://localhost:11434
set LLM_MODEL=scb10x/llama3.1-typhoon2-8b-instruct
uvicorn app:app --reload --port 8000
```

**Terminal 3 — Backend Go:**

```cmd
cd c:\Users\test1\Desktop\chatbot\backend
set MONGO_URI=mongodb://admin:admin123@localhost:27017/mbti?authSource=admin
set AI_SERVICE_URL=http://localhost:8000
go run .
```

**Terminal 4 — Frontend:**

```cmd
cd c:\Users\test1\Desktop\chatbot\frontend
npm install
npm start
```

เปิด browser: http://localhost:4200

---

## ขั้น 6 · ตรวจว่า LLM พร้อมใช้งาน (สำคัญ)

ก่อนทดสอบจริง เปิด browser ไปที่:

```
http://localhost:8000/health
```

ต้องได้ JSON แบบนี้:

```json
{
  "status": "ok",
  "llm_reachable": true,
  "llm_model_present": true,
  "llm_model": "scb10x/llama3.1-typhoon2-8b-instruct",
  "llm_url": "http://host.docker.internal:11434",
  "llm_ready": true
}
```

ถ้า `llm_ready: true` ✅ ไปขั้น 7 ได้เลย

### กรณีผิดพลาด

| ค่าที่เจอ | สาเหตุ | วิธีแก้ |
|-----------|--------|---------|
| `llm_reachable: false` | ai-service ติดต่อ Ollama ไม่ได้ | ตรวจว่า `ollama serve` ทำงาน / URL ใน `.env` ถูก |
| `llm_reachable: true, llm_model_present: false` | ยังไม่ได้ pull model | รัน `ollama pull scb10x/llama3.1-typhoon2-8b-instruct` |
| connection refused ที่ port 8000 | ai-service ยังไม่ขึ้น | ดู log ของ `docker compose` หรือ terminal 2 |

---

## ขั้น 7 · ทดสอบ flow เต็มระบบ

1. เปิด http://localhost:4200
2. คลิก **"🚀 เริ่มทำแบบทดสอบ"**
3. ระบบพาไปหน้าคำถาม 10 ข้อปลายเปิด
4. กรอกคำตอบยาว ๆ ของจริง (อย่างน้อย 30-50 คำต่อข้อ) เพื่อให้ LLM วิเคราะห์ได้ลึก
5. ลองพิมพ์แล้วรอ 2-3 วิ — ควรเห็นป้าย **"✓ บันทึกอัตโนมัติแล้ว"** ที่มุมบน
6. ทดสอบปุ่ม **"🗑️ ล้างคำตอบทั้งหมด"** → ต้องมี dialog ยืนยัน
7. กรอกครบ 10 ข้อ → ปุ่ม **"✨ ส่งคำตอบให้ AI วิเคราะห์"** จะกดได้ → ต้องมี dialog ยืนยัน
8. กดยืนยัน → ระบบจะขึ้น **"AI กำลังสวมบทนักจิตวิทยา..."**
9. **รอ 30-90 วินาที** (8B บน CPU จะนานขึ้น) — อย่าปิดหน้า
10. ระบบพาไปหน้าผล MBTI พร้อม:
    - ตัวอักษร 4 ตัว + nickname
    - **พื้นหลังเปลี่ยนสีตามกลุ่ม MBTI** (Sentinels=ฟ้า, Analysts=ม่วง, Diplomats=เขียว, Explorers=เหลือง)
    - Bar 4 มิติ + บทวิเคราะห์เชิงลึก

---

## ขั้น 8 · เก็บงาน / ปิดระบบ

```cmd
:: ถ้าใช้ Docker Compose
docker compose down

:: ถ้ารัน native — กด Ctrl+C ใน terminal 2, 3, 4
:: MongoDB ปิดเอง:
docker compose stop mongo
```

Ollama ยังเปิดอยู่เบื้องหลังเสมอ (ไม่ต้องปิด) — กินเฉพาะ RAM เมื่อมีการเรียกใช้

---

## 🆘 Troubleshooting เฉพาะรุ่น 8B

### ❌ "LLM call failed: ReadTimeout"

8B บน CPU ตอบช้ากว่า 3B มาก เพิ่ม timeout ใน `.env`:

```env
LLM_TIMEOUT=300
```

แล้ว restart ai-service: `docker compose restart ai`

### ❌ "out of memory" / เครื่องแฮงก์ตอน LLM กำลังตอบ

RAM ไม่พอสำหรับ 8B **เปลี่ยนเป็น 3B ทันที**:

```cmd
ollama pull scb10x/llama3.2-typhoon2-3b-instruct
```

แก้ `.env`:

```env
LLM_MODEL=scb10x/llama3.2-typhoon2-3b-instruct
```

Restart: `docker compose restart ai`

### ❌ ผลวิเคราะห์ตื้น / ไม่ match คำตอบของเรา

- ลองเขียนคำตอบยาวขึ้น (อย่างน้อย 50 คำต่อข้อ)
- เพิ่ม `LLM_TEMPERATURE=0.5` ใน `.env` เพื่อให้ model กล้าตีความมากขึ้น
- ถ้ายังไม่ดีพอ ให้ใช้รุ่นใหญ่กว่า: `scb10x/llama3.1-typhoon2-70b-instruct` (ต้อง RAM 64 GB+)

### ❌ Ollama ใช้ CPU 100% ตลอดเวลา

8B บน CPU เป็นเรื่องปกติช่วงที่ LLM กำลังตอบ — ควรหยุดเองหลัง response เสร็จ ถ้าไม่หยุด ให้ restart:

```cmd
net stop ollama
net start ollama
```

### ❌ `ollama: command not found` (หลังติดตั้งแล้ว)

ปิด Command Prompt เก่าแล้วเปิดใหม่ — Windows ยังไม่รีเฟรช PATH
ถ้ายังไม่ได้ ให้ logout แล้ว login ใหม่

---

## 📋 Checklist สรุป (รุ่น 8B เท่านั้น)

- [ ] RAM ว่าง 8 GB+ และ Disk ว่าง 6 GB+
- [ ] ติดตั้ง Ollama จาก https://ollama.com/download
- [ ] `ollama --version` ตอบได้
- [ ] `ollama pull scb10x/llama3.1-typhoon2-8b-instruct` สำเร็จ
- [ ] `ollama list` เห็นชื่อ model
- [ ] `ollama run scb10x/llama3.1-typhoon2-8b-instruct` ตอบได้
- [ ] `copy .env.example .env` และแก้ `LLM_MODEL` + `OLLAMA_URL`
- [ ] `docker compose build ai backend`
- [ ] `docker compose up mongo ai backend frontend`
- [ ] `http://localhost:8000/health` → `llm_ready: true`
- [ ] เปิด `http://localhost:4200` → ทำแบบทดสอบจริง → เห็นผล MBTI พร้อมสีพื้นหลังเปลี่ยน
