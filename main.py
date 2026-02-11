import logging
import os
import random  # <-- Tasodifiy kod yaratish uchun kerak
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = os.getenv("BOT_TOKEN")

if not API_TOKEN:
    print("DIQQAT! BOT_TOKEN topilmadi. Railway Variables bo'limiga kiring.")
else:
    print("Bot tokeni qabul qilindi!")

ADMIN_ID = 123456789  # <-- O'Z ID RAQAMINGIZNI YOZING

# --- BOTNI ISHGA TUSHIRISH ---
logging.basicConfig(level=logging.INFO)

if API_TOKEN:
    bot = Bot(token=API_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
else:
    exit()

# --- XOTIRA ---
menu = {}

# --- HOLATLAR ---
class AdminState(StatesGroup):
    name = State()
    price = State()
    delete = State()

# --- ADMIN PANEL QISMI ---

@dp.message_handler(commands=['admin'], user_id=ADMIN_ID)
async def admin_start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Ovqat qo'shish", "➖ Ovqat o'chirish")
    markup.add("📋 Menyuni ko'rish")
    await message.answer("Admin panelga xush kelibsiz!", reply_markup=markup)

# 1. Ovqat qo'shish
@dp.message_handler(text="➕ Ovqat qo'shish", user_id=ADMIN_ID)
async def add_food_start(message: types.Message):
    await AdminState.name.set()
    await message.answer("Ovqat nomini kiriting (masalan: Lavash):")

@dp.message_handler(state=AdminState.name)
async def add_food_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await AdminState.price.set()
    await message.answer("Narxini kiriting (faqat raqam, masalan: 25000):")

@dp.message_handler(state=AdminState.price)
async def add_food_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam kiriting!")
        return
    
    async with state.proxy() as data:
        name = data['name']
        price = int(message.text)
        menu[name] = price
    
    await state.finish()
    await message.answer(f"✅ {name} menyuga {price} so'm narx bilan qo'shildi.")

# 2. Ovqat o'chirish
@dp.message_handler(text="➖ Ovqat o'chirish", user_id=ADMIN_ID)
async def delete_food_start(message: types.Message):
    if not menu:
        await message.answer("Menyu bo'm-bo'sh.")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for food in menu:
        markup.add(food)
    markup.add("🔙 Bekor qilish")
    
    await AdminState.delete.set()
    await message.answer("O'chirmoqchi bo'lgan ovqatni tanlang:", reply_markup=markup)

@dp.message_handler(state=AdminState.delete)
async def delete_food_finish(message: types.Message, state: FSMContext):
    food = message.text
    if food in menu:
        del menu[food]
        await message.answer(f"🗑 {food} menyudan o'chirildi.", reply_markup=types.ReplyKeyboardRemove())
    elif food == "🔙 Bekor qilish":
        await message.answer("Bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("Bunday ovqat topilmadi.")
    await state.finish()

# 3. Menyuni ko'rish
@dp.message_handler(text="📋 Menyuni ko'rish", user_id=ADMIN_ID)
async def show_menu(message: types.Message):
    if not menu:
        await message.answer("Menyu bo'sh.")
    else:
        msg = "📋 JO'RIY MENYU:\n\n"
        for k, v in menu.items():
            msg += f"🔹 {k} - {v} so'm\n"
        await message.answer(msg)

# --- FOYDALANUVCHI QISMI ---

@dp.message_handler(commands=['start'])
async def user_start(message: types.Message):
    if not menu:
        await message.answer("Hozircha menyu bo'sh. Iltimos keyinroq kiring.")
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for food, price in menu.items():
        # Callback format: buy:ovqat_nomi
        btn = InlineKeyboardButton(text=f"{food} - {price} so'm", callback_data=f"buy:{food}")
        markup.add(btn)
    
    await message.answer("Assalomu alaykum! Buyurtma berish uchun taomni tanlang:", reply_markup=markup)

# Buyurtmani qabul qilish va KOD yaratish
@dp.callback_query_handler(lambda c: c.data.startswith('buy:'))
async def process_order(callback_query: types.CallbackQuery):
    food_name = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    full_name = callback_query.from_user.full_name

    # Tasodifiy 4 xonali kod yaratamiz (Masalan: 4812)
    order_code = random.randint(1000, 9999)
    
    await bot.answer_callback_query(callback_query.id, text="Buyurtma qabul qilindi!")
    await bot.send_message(user_id, f"✅ {food_name} buyurtmangiz adminga yuborildi.\n\nTayyor bo'lganda sizga maxsus kod yuboramiz.")

    # Adminga xabar yuborish (Kod bilan)
    admin_markup = InlineKeyboardMarkup()
    # Callback format: ready:user_id:food_name:code
    btn_ready = InlineKeyboardButton("🟡 Tayyor (Mijozni chaqirish)", callback_data=f"ready:{user_id}:{food_name}:{order_code}")
    btn_cancel = InlineKeyboardButton("❌ Bekor qilish", callback_data=f"cancel:{user_id}")
    admin_markup.add(btn_ready, btn_cancel)
    
    msg = (f"❗️ YANGI BUYURTMA!\n\n"
           f"👤 Mijoz: {full_name} (@{username})\n"
           f"🍽 Taom: {food_name}\n"
           f"🔐 MAXFIY KOD: {order_code}")  # Admin kodni oldindan ko'rib turadi
    
    await bot.send_message(ADMIN_ID, msg, reply_markup=admin_markup)

# --- OSHXONACHI (ADMIN) UCHUN STATUSLAR ---

# 1. Tayyor bo'lganda mijozga kodni yuborish
@dp.callback_query_handler(lambda c: c.data.startswith('ready:'))
async def notify_user_ready(callback_query: types.CallbackQuery):
    data = callback_query.data.split(":")
    user_id = data[1]
    food_name = data[2]
    order_code = data[3]
    
    try:
        # Mijozga kodni yuborish
        await bot.send_message(
            int(user_id), 
            f"📢 DIQQAT! Buyurtmangiz tayyor!\n\n"
            f"🍔 Taom: **{food_name}**\n"
            f"🔢 OLIB KETISH KODI: **{order_code}**\n\n"
            f"Kassaga borib shu kodni ayting va taomingizni oling."
        )
        await bot.answer_callback_query(callback_query.id, text="Mijozga kod yuborildi ✅")
        
        # Admin xabarini o'zgartirish
        finish_markup = InlineKeyboardMarkup()
        btn_finish = InlineKeyboardButton("✅ Berib yuborildi (Yopish)", callback_data="finish_order")
        finish_markup.add(btn_finish)

        await callback_query.message.edit_text(
            callback_query.message.text + "\n\n✅ TAYYOR! MIJOZGA XABAR BORDI.\nMijoz kelib kodni aytsa, tekshirib 'Berib yuborildi' ni bosing.",
            reply_markup=finish_markup
        )
    except Exception:
        await bot.answer_callback_query(callback_query.id, text="Mijozga yuborib bo'lmadi (bloklagan).")

# 2. Buyurtmani yopish (Berib yuborgandan keyin)
@dp.callback_query_handler(text="finish_order")
async def finish_order_handler(callback_query: types.CallbackQuery):
    await callback_query.message.delete()
    await bot.answer_callback_query(callback_query.id, text="Buyurtma yopildi.")

# 3. Bekor qilish
@dp.callback_query_handler(lambda c: c.data.startswith('cancel:'))
async def cancel_order(callback_query: types.CallbackQuery):
    user_id = callback_query.data.split(":")[1]
    await bot.send_message(int(user_id), "❌ Uzr, buyurtmangiz bekor qilindi.")
    await callback_query.message.edit_text("❌ BUYURTMA BEKOR QILINDI.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
