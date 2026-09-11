# Hisobchi — Telegram Mini App

Kirim/chiqimlarni kuzatadigan, to'liq interfeysli (Mini App) Telegram moliya boti.

## Fayllar

- `app.py` — bot (aiogram) + veb-server (FastAPI) bitta joyda
- `db.py` — ma'lumotlar bazasi funksiyalari (SQLite)
- `auth.py` — Telegram Mini App autentifikatsiyasini tekshirish
- `static/` — Mini App interfeysi (HTML/CSS/JS)

## Railway'da joylashtirish (yangilash)

Eski `bot.py` fayli endi kerak emas — uni repo'dan o'chirib, yuqoridagi fayllarni yuklang
(yoki eski fayl qolsa ham muammo emas, Procfile endi `app.py`ni ishga tushiradi).

### 1. Fayllarni GitHub repo'ga yuklang
`app.py`, `db.py`, `auth.py`, `requirements.txt`, `Procfile` va butun `static/` papkasini
(`index.html`, `style.css`, `app.js`) repo'ga qo'shing.

### 2. Railway'da Public Domain oching
Bot service sahifasida **Settings → Networking → Generate Domain** tugmasini bosing.
Sizga shunga o'xshash manzil beriladi: `https://hisobchi-bot-production.up.railway.app`

### 3. Environment Variables
**Variables** bo'limida ikkita o'zgaruvchi bo'lishi kerak:
- `BOT_TOKEN` — bot tokeningiz (avval qo'shilgan)
- `WEBAPP_URL` — 2-qadamda olingan domen (masalan `https://hisobchi-bot-production.up.railway.app`)

### 4. Deploy
Railway avtomatik qayta ishga tushiradi. **Deployments**'da "Success" chiqishini kuting.

### 5. Tekshirish
Telegram'da botga `/start` yuboring — endi "📱 Mini-ilovani ochish" tugmasi chiqadi.
Bosganingizda to'liq interfeys (balans, qo'shish, hisobot, tarix) ochiladi.

## Mahalliy ishga tushirish (kompyuterda, ixtiyoriy)

```bash
pip install -r requirements.txt
export BOT_TOKEN="tokeningiz"
export WEBAPP_URL="https://..."   # ochiq domen kerak, mahalliy localhost ishlamaydi
uvicorn app:app --reload
```
