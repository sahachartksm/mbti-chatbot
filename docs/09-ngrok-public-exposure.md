# 09 — เปิด App ให้คนนอกใช้ผ่าน ngrok + Angular Proxy

> **เขียนเมื่อ:** 2026-04-18 เวลา 17:00 (UTC+07:00)
> **Context:** ต้องการ demo chatbot ให้เพื่อนจากมือถือ/เครื่องอื่น — ใช้ ngrok tunnel ตัวเดียว expose ทั้ง stack

---

## 🎯 โจทย์

App มี 3 parts:
- Frontend (Angular) `:4200`
- Backend (Go) `:8080`
- AI (Python) `:8000`

แต่ **ngrok Free plan มีได้แค่ 1 tunnel** ต่อ session

**ทางออก:** ให้ Frontend ทำหน้าที่เป็น **reverse proxy** ให้ backend ด้วย — client มองเห็น URL เดียว

---

## 🏗️ สถาปัตยกรรม

```
┌─ เครื่องเพื่อน / มือถือ ─┐
│                          │
│   Browser                │
│   https://xxxx.ngrok-    │
│   free.dev               │
│                          │
└───────┬──────────────────┘
        │ all requests (HTML + /api/*)
        ▼
┌─────────────────────────────────────────┐
│          ngrok (Cloud tunnel)            │
│  rewrite Host: localhost:4200            │
└─────────┬───────────────────────────────┘
          │
          ▼
┌─────────────── Host Machine ──────────────────┐
│                                               │
│   ┌───────────────────────────────────────┐   │
│   │  Angular dev server  :4200            │   │
│   │  ├─ GET /             → index.html    │   │
│   │  ├─ GET /main.js      → JS bundle     │   │
│   │  ├─ GET /*.css        → styles        │   │
│   │  └─ /api/*            → proxy ───┐    │   │
│   └────────────────────────────────┬──┘    │   │
│                                    │       │   │
│                  proxy.conf.js     │       │   │
│                                    ▼       │   │
│   ┌────────────────────────────────────┐   │   │
│   │  Go backend  :8080                 │   │   │
│   │  ├─ /api/session/start             │   │   │
│   │  ├─ /api/session/:id/answer        │   │   │
│   │  └─ /api/session/:id/analyze ──┐   │   │   │
│   └────────────────────────────────┼───┘   │   │
│                                    │       │   │
│                                    ▼       │   │
│   ┌────────────────────────────────────┐   │   │
│   │  AI Python :8000                   │   │   │
│   │  └─ POST /predict                  │   │   │
│   └────────────────────────────────────┘   │   │
│                                            │   │
└────────────────────────────────────────────┘   │
                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🧩 ปัญหา 2 เรื่อง กับทางแก้

### ปัญหาที่ 1: Vite block ngrok hostname

**อาการ:**
```
Blocked request. This host ("xxxx.ngrok-free.dev") is not allowed.
To allow this host, add "xxxx.ngrok-free.dev" to server.allowedHosts.
```

**Root cause:** Angular 17 `application` builder ใช้ **Vite dev server** ซึ่งมี strict host check (กัน DNS rebinding attack) — default อนุญาตแค่ `localhost` / `127.0.0.1`

**ทางแก้ที่เลือก: ngrok rewrite Host header**

```cmd
ngrok http --host-header="localhost:4200" 4200
```

**กลไก:**
```
Browser sends:     Host: xxxx.ngrok-free.dev
ngrok rewrites:    Host: localhost:4200
Vite sees:         Host: localhost:4200  ✓ ผ่าน
```

**ทำไมเลือกวิธีนี้?**
- ไม่ต้องแก้โค้ด
- ngrok URL เปลี่ยนทุกครั้งที่ restart — ถ้า whitelist ใน `angular.json` ต้องแก้ทุกรอบ
- `--host-header=rewrite` จะใช้ upstream address อัตโนมัติ — flexible กว่า

**ทางเลือกอื่นที่ลองแล้ว:**
- `angular.json` `allowedHosts` → Angular 17 dev-server ยังไม่ forward ไป Vite (bug/missing feature; แก้ใน v18+)
- `--disable-host-check` → option นี้ Angular ลบไปแล้ว

### ปัญหาที่ 2: Frontend เรียก backend ไม่ได้จากเครื่องอื่น

**อาการ:** เปิด ngrok URL → UI โผล่ → กด "เริ่มทำแบบทดสอบ" → error

**Root cause:** `environment.development.ts` เดิมมี:
```ts
apiBase: 'http://localhost:8080/api'
```

เมื่อ browser ของเพื่อนเปิด ngrok URL → โหลด JS bundle มี hardcode `localhost:8080` → **`localhost` ของเครื่องเพื่อนไม่มี backend** → ERR_CONNECTION_REFUSED

**ทางแก้: Angular proxy + relative URL**

1. **Frontend เรียก relative `/api`**
   ```ts
   // environment.development.ts
   apiBase: '/api';
   ```

2. **Angular dev-server proxy `/api/*` → backend**
   ```js
   // proxy.conf.js
   module.exports = {
     '/api': {
       target: process.env.API_TARGET || 'http://localhost:8080',
       changeOrigin: true,
       secure: false,
     },
   };
   ```

3. **บอก Angular ให้ใช้ proxy**
   ```json
   // angular.json
   "serve": {
     "options": {
       "proxyConfig": "proxy.conf.js"
     }
   }
   ```

**ผลลัพธ์:**
- Browser → `https://xxxx.ngrok-free.dev/api/session/start`
- ngrok → `http://localhost:4200/api/session/start`
- Angular dev-server เห็น `/api/*` → proxy ไป `http://localhost:8080/api/session/start`
- Go backend ตอบกลับ

---

## 📐 ทำไม Vite expect object format ไม่ใช่ array

### Webpack dev-server format (เก่า)
```js
module.exports = [
  { context: ['/api'], target: 'http://localhost:8080', ... }
];
```

### Vite dev-server format (ใหม่ — ใช้อยู่)
```js
module.exports = {
  '/api': { target: 'http://localhost:8080', ... }
};
```

Angular 17 `application` builder ส่งต่อไป Vite — ใช้ **object format** เท่านั้น

### เหตุผลทาง design
- **Webpack:** context + target แยก → ยืดหยุ่นกำหนดหลาย paths ไปปลายทางเดียว
- **Vite:** key = path pattern → อ่านง่ายกว่าเมื่อมีหลาย routes
  ```js
  {
    '/api':    { target: 'http://localhost:8080' },
    '/ws':     { target: 'ws://localhost:8080', ws: true },
    '/static': { target: 'http://cdn.example.com' },
  }
  ```

---

## 🐳 Docker compatibility

proxy target ต่างกันใน native vs docker:
- **Native:** `http://localhost:8080`
- **Docker:** `http://backend:8080` (service name ใน chatbot-net)

**ทางแก้:** อ่านจาก env var

```js
const target = process.env.API_TARGET || 'http://localhost:8080';
```

```yaml
# docker-compose.yml
frontend:
  environment:
    API_TARGET: http://backend:8080
```

- Native → env ไม่มี → ใช้ default `http://localhost:8080` ✓
- Docker → env set → ใช้ `http://backend:8080` ✓
- Config ไฟล์เดียว จัดการได้ทั้งสอง scenarios

---

## 🎁 ข้อดีของ Proxy pattern ในภาพรวม

| เรื่อง | อธิบาย |
|---|---|
| **CORS-free** | Browser เห็น origin เดียว (`ngrok URL`) → ไม่มี cross-origin |
| **1 ngrok tunnel พอ** | Backend อยู่ข้างหลัง ไม่ต้อง expose แยก |
| **Security** | Backend ไม่ public — ป้องกัน direct access / DDoS |
| **Production parity** | Production ก็ใช้ pattern เดียว (nginx reverse proxy) |
| **เปลี่ยน backend URL ง่าย** | แก้ `proxy.conf.js` ที่เดียว ไม่ต้องแก้ frontend code |

---

## 🧪 ทดสอบว่า proxy ทำงาน

1. ngrok terminal — ดู Connections counter เพิ่มขึ้น
2. ngrok web UI: **http://127.0.0.1:4040**
   - ดู list requests
   - คลิก request `/api/*` → ดู Response body
   - ถ้าเป็น JSON `{...}` = proxy ทำงาน ✓
   - ถ้าเป็น HTML = proxy miss (Angular ส่ง index.html fallback)
3. Browser DevTools → Network tab
   - เห็น `POST https://xxxx.ngrok-free.dev/api/session/start` → Status 200

---

## 🚨 Common pitfalls

### 1. ลืม restart Angular dev server
`proxy.conf.js` / `angular.json` เปลี่ยน → **ต้อง restart** (hot reload ไม่ reload config)

### 2. Array format แทน object format
```js
// ❌ ไม่ work กับ Vite (Angular 17 application builder)
module.exports = [{ context: ['/api'], target: '...' }];

// ✅ ใช้ได้
module.exports = { '/api': { target: '...' } };
```

### 3. ngrok tunnel expire เมื่อปิด terminal
Free plan — ngrok URL เปลี่ยนทุกครั้ง restart เพราะ subdomain random

### 4. Static domain (bonus)
ngrok Free plan มี 1 static domain ต่อ account — ใช้ได้ฟรีตลอด:
```cmd
ngrok http --url=your-domain.ngrok-free.dev --host-header=rewrite 4200
```
หาได้ที่ https://dashboard.ngrok.com/cloud-edge/domains

---

## 🎓 Summary

**Pattern:** Frontend ทำหน้าที่ reverse proxy ระหว่าง ngrok ↔ backend

**Why it works:**
1. **Same origin** — browser ไม่ต้องเจอ CORS  
2. **Single tunnel** — ngrok Free พอใช้
3. **Host header rewrite** — bypass Vite's strict host check
4. **Relative URL** — client code ไม่ผูกกับ URL ไหน → portable ทุก environment (local, ngrok, prod)

**ใน real production** — แค่แทน Angular dev-server ด้วย **nginx** ก็ได้ pattern เดียวกัน:
```nginx
server {
  location /       { root /var/www/frontend; }
  location /api/   { proxy_pass http://backend:8080; }
}
```

---

👉 อ้างอิง:
- [08-docker-compose-unified.md](./08-docker-compose-unified.md) — docker setup
- [03-api.md](./03-api.md) — API endpoints ที่ถูก proxy
