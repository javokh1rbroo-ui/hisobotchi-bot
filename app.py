import asyncio
import logging
import os
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
)
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from db import (
    init_db, add_transaction, delete_last_transaction, get_balance,
    get_monthly_report, get_recent_transactions, CATEGORIES,
)
from auth import verify_init_data

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")  # Railway public domen, masalan https://xxx.up.railway.app

# ============ AIOGRAM BOT QISMI ============

class AddTx(StatesGroup):
    choosing_category = State()
    entering_amount = State()
    entering_comment = State()


router = Router()


def _webapp_url_valid() -> bool:
    return WEBAPP_URL.strip().startswith(("http://", "https://"))


def main_menu_kb():
    rows = [
        [KeyboardButton(text="➕ Kirim qo'shish"), KeyboardButton(text="➖ Chiqim qo'shish")],
        [KeyboardButton(text="📊 Oylik hisobot"), KeyboardButton(text="💰 Balans")],
        [KeyboardButton(text="↩️ Oxirgisini bekor qilish")],
    ]
    if _webapp_url_valid():
        rows.insert(0, [KeyboardButton(text="📱 Mini-ilovani ochish", web_app=WebAppInfo(url=WEBAPP_URL.strip()))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def categories_kb(t_type: str):
    buttons = [[InlineKeyboardButton(text=c, callback_data=f"cat:{t_type}:{c}")] for c in CATEGORIES[t_type]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def months_kb():
    from datetime import datetime
    now = datetime.now()
    buttons, row = [], []
    for i in range(6):
        y, m = now.year, now.month - i
        while m <= 0:
            m += 12
            y -= 1
        row.append(InlineKeyboardButton(text=f"{y}-{m:02d}", callback_data=f"rep:{y}:{m}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    text = "Assalomu alaykum! Men sizning shaxsiy moliya botingizman.\n\n"
    if _webapp_url_valid():
        text += "📱 Pastdagi tugma orqali to'liq interfeysli mini-ilovani oching, yoki menyudan foydalaning."
    else:
        text += "Kirim va chiqimlaringizni kiritib boring, men oylik hisobotni tayyorlab beraman."
    await message.answer(text, reply_markup=main_menu_kb())


@router.message(F.text == "➕ Kirim qo'shish")
async def start_add_income(message: Message, state: FSMContext):
    await state.update_data(t_type="kirim")
    await state.set_state(AddTx.choosing_category)
    await message.answer("Kategoriyani tanlang:", reply_markup=categories_kb("kirim"))


@router.message(F.text == "➖ Chiqim qo'shish")
async def start_add_expense(message: Message, state: FSMContext):
    await state.update_data(t_type="chiqim")
    await state.set_state(AddTx.choosing_category)
    await message.answer("Kategoriyani tanlang:", reply_markup=categories_kb("chiqim"))


@router.callback_query(AddTx.choosing_category, F.data.startswith("cat:"))
async def category_chosen(callback: CallbackQuery, state: FSMContext):
    _, t_type, category = callback.data.split(":", 2)
    await state.update_data(category=category)
    await state.set_state(AddTx.entering_amount)
    await callback.message.answer(f"«{category}» tanlandi.\nSummani kiriting (masalan: 25000):")
    await callback.answer()


@router.message(AddTx.entering_amount)
async def amount_entered(message: Message, state: FSMContext):
    text = message.text.replace(" ", "").replace(",", "")
    if not text.replace(".", "", 1).isdigit():
        await message.answer("Iltimos, faqat raqam kiriting (masalan: 25000).")
        return
    await state.update_data(amount=float(text))
    await state.set_state(AddTx.entering_comment)
    await message.answer("Izoh qo'shmoqchimisiz? (o'tkazib yuborish uchun «-» yozing)")


@router.message(AddTx.entering_comment)
async def comment_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    comment = "" if message.text.strip() == "-" else message.text.strip()
    add_transaction(message.from_user.id, data["t_type"], data["amount"], data["category"], comment)
    label = "Kirim" if data["t_type"] == "kirim" else "Chiqim"
    await message.answer(
        f"✅ {label} qo'shildi: {data['amount']:,.0f} so'm — {data['category']}",
        reply_markup=main_menu_kb(),
    )
    await state.clear()


@router.message(F.text == "↩️ Oxirgisini bekor qilish")
async def undo_last(message: Message):
    ok = delete_last_transaction(message.from_user.id)
    await message.answer("Oxirgi yozuv o'chirildi." if ok else "O'chiriladigan yozuv topilmadi.")


@router.message(F.text == "💰 Balans")
async def show_balance(message: Message):
    kirim, chiqim, balans = get_balance(message.from_user.id)
    await message.answer(
        f"💰 <b>Umumiy balans</b>\n\nKirim: {kirim:,.0f} so'm\nChiqim: {chiqim:,.0f} so'm\nQoldiq: {balans:,.0f} so'm",
        parse_mode="HTML",
    )


@router.message(F.text == "📊 Oylik hisobot")
async def choose_month(message: Message):
    await message.answer("Qaysi oy uchun hisobot kerak?", reply_markup=months_kb())


@router.callback_query(F.data.startswith("rep:"))
async def show_report(callback: CallbackQuery):
    _, year, month = callback.data.split(":")
    year, month = int(year), int(month)
    rows = get_monthly_report(callback.from_user.id, year, month)
    if not rows:
        await callback.message.answer(f"{year}-{month:02d} uchun ma'lumot topilmadi.")
        await callback.answer()
        return
    kirim_lines, chiqim_lines = [], []
    total_kirim = total_chiqim = 0.0
    for t_type, category, total, count in rows:
        line = f"  • {category}: {total:,.0f} so'm ({count} ta)"
        if t_type == "kirim":
            kirim_lines.append(line); total_kirim += total
        else:
            chiqim_lines.append(line); total_chiqim += total
    text = f"📊 <b>{year}-{month:02d} oyi hisoboti</b>\n\n"
    if kirim_lines:
        text += "<b>Kirimlar:</b>\n" + "\n".join(kirim_lines) + f"\n  Jami: {total_kirim:,.0f} so'm\n\n"
    if chiqim_lines:
        text += "<b>Chiqimlar:</b>\n" + "\n".join(chiqim_lines) + f"\n  Jami: {total_chiqim:,.0f} so'm\n\n"
    text += f"<b>Sof natija: {total_kirim - total_chiqim:,.0f} so'm</b>"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.message(Command("hisobot"))
async def cmd_hisobot(message: Message):
    await choose_month(message)


@router.message(Command("balans"))
async def cmd_balans(message: Message):
    await show_balance(message)


# ============ FASTAPI + MINI APP API QISMI ============

class TxIn(BaseModel):
    type: str
    amount: float
    category: str
    comment: str = ""


def _authed_user(x_init_data: str = Header(default="")):
    user = verify_init_data(x_init_data, BOT_TOKEN)
    if not user:
        raise HTTPException(status_code=401, detail="Noto'g'ri yoki eskirgan Telegram ma'lumoti")
    return user


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    bot_task = None
    if BOT_TOKEN:
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)
        bot_task = asyncio.create_task(dp.start_polling(bot))
    yield
    if bot_task:
        bot_task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/api/categories")
def api_categories():
    return CATEGORIES


@app.get("/api/balance")
def api_balance(x_init_data: str = Header(default="")):
    user = _authed_user(x_init_data)
    kirim, chiqim, balans = get_balance(user["id"])
    return {"kirim": kirim, "chiqim": chiqim, "balans": balans}


@app.get("/api/report")
def api_report(year: int, month: int, x_init_data: str = Header(default="")):
    user = _authed_user(x_init_data)
    rows = get_monthly_report(user["id"], year, month)
    return [
        {"type": r[0], "category": r[1], "total": r[2], "count": r[3]} for r in rows
    ]


@app.get("/api/recent")
def api_recent(x_init_data: str = Header(default="")):
    user = _authed_user(x_init_data)
    rows = get_recent_transactions(user["id"])
    return [
        {"id": r[0], "type": r[1], "amount": r[2], "category": r[3], "comment": r[4], "created_at": r[5]}
        for r in rows
    ]


@app.post("/api/transaction")
def api_add_transaction(tx: TxIn, x_init_data: str = Header(default="")):
    user = _authed_user(x_init_data)
    if tx.type not in ("kirim", "chiqim"):
        raise HTTPException(status_code=400, detail="type 'kirim' yoki 'chiqim' bo'lishi kerak")
    add_transaction(user["id"], tx.type, tx.amount, tx.category, tx.comment)
    return {"ok": True}


# Mini App fayllari — barchasi repo ildizida, papkasiz
@app.get("/")
def index_page():
    return FileResponse("index.html")


@app.get("/style.css")
def style_file():
    return FileResponse("style.css", media_type="text/css")


@app.get("/app.js")
def app_js_file():
    return FileResponse("app.js", media_type="application/javascript")
