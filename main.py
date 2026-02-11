import logging
import os
import random
import uuid  # Har bir buyurtmaga unikal ID berish uchun
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = os.getenv("BOT_TOKEN")

# Token tekshiruvi
if not API_TOKEN:
    print("DIQQAT! Token topilmadi. Railway Variablesga kiritilganiga ishonch hosil qiling.")
else:
    print("Bot ishga tushdi!")

ADMIN_ID = 123456789  # <-- O'Z ID RAQAMINGIZNI YOZING

# --- BOTNI ISHGA TUSHIRISH ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN if API_TOKEN else "123:test") # Xatolik bermasligi uchun vaqtincha
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- XOTIRA (DATABASE O'RNIGA) ---
# Menyular
menu = {}
# Aktiv buyurtmalar: { 'order_id': {'user_id': 123, 'food': 'Lavash', 'code': 5544} }
orders = {}

# --- HOLATLAR ---
class AdminState(StatesGroup):
    name = State()
    price = State()
    delete = State()

# ================= ADMIN PANEL =================

@dp.message_handler(commands=['admin'], user_id=ADMIN_ID)
async def admin_start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Ovqat qo'shish", "➖ Ovqat o'chirish")
    markup.add("📋 Menyuni ko'rish")
    await message.answer("Admin panel boshqaruvi:", reply_markup=markup)

# 1. Ovqat qo'shish
@dp.message_handler(text="➕ Ovqat qo'shish", user_id=ADMIN_ID)
async def add_food_start(message: types.Message):
    await AdminState.name.set()
    await message.answer("Ovqat nomini yozing:")

@dp.message_handler(state=AdminState.name)
async def add_food_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await AdminState.price.set()
    await message.answer("Narxini yozing (faqat raqam):")

@dp.message_handler(state=AdminState.price)
async def add_food_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Raqam yozing!")
        return
    
    async with state.proxy() as data:
        name = data['name']
        price = int(message.text)
        menu[name] = price
    
    await state.finish()
    await message.answer(f"✅ {name} qo'shildi.")

# 2. Ovqat o'chirish
@dp.message_handler(text="➖ Ovqat o'chirish", user_id=ADMIN_ID)
async def delete_food_start(message: types.Message):
    if not menu:
        await message.answer("Menyu bo'sh.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for food in menu:
        markup.add(food)
    markup.add("🔙 Bekor qilish")
    await AdminState.delete.set()
    await message.answer("Tanlang:", reply_markup=markup)

@dp.message_handler(state=AdminState.delete)
async def delete_food_finish(message: types.Message, state: FSMContext):
    food = message.text
    if food in menu:
        del menu[food]
        await message.answer("O'chirildi.", reply_markup=types.ReplyKeyboardRemove())
    await state.finish()

# 3. Menyu ko'rish
@dp.message_handler(text="📋 Menyuni ko'rish", user_id=ADMIN_ID)
async def show_menu(message: types.Message):
    if not menu:
        await message.answer("Menyu bo'sh.")
        return
    msg = "📋 MENYU:\n\n"
    for k, v in menu.items():
        msg += f"🔹 {k} - {v} so'm\n"
    await message.answer(msg)


# ================= FOYDALANUVCHI QISMI =================

@dp.message_handler(commands=['start'])
async def user_start(message: types.Message):
    if not menu:
        await message.answer("Oshxona menyusi hozircha bo'sh.")
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for food, price in menu.items():
        # Callback faqat ovqat nomini oladi
        btn = InlineKeyboardButton(text=f"{food} - {price} so'm", callback_data=f"buy:{food}")
        markup.add(btn)
    
    await message.answer("Quyidagi taomlardan birini tanlang:", reply_markup=markup)

# --- BUYURTMA QILISH ---
@dp.callback_query_handler(lambda c: c.data.startswith('buy:'))
async def user_buy(call: types.CallbackQuery):
    food_name = call.data.split(":")[1]
    user_id = call.from_user.id
    full_name = call.from_user.full_name
    username = call.from_user.username

    # 1. Unikal ID va Maxfiy kod yaratamiz
    order_id = str(uuid.uuid4())[:8] # 8 xonali ID (texnik ID)
    secret_code = random.randint(1000, 9999) # 4 xonali mijoz kodi (oddiysi)

    # 2. Xotiraga saqlaymiz
    orders[order_id] = {
        'user_id': user_id,
        'food': food_name,
        'code': secret_code,
        'name': full_name,
        'username': username
    }

    # 3. Mijozga xabar
    await call.answer("Buyurtma qabul qilindi!")
    await bot.send_message(user_id, f"✅ **{food_name}** buyurtma qilindi.\n\n⏳ Iltimos kuting, taom tayyor bo'lganda sizga MAXFIY KOD yuboriladi.")

    # 4. Adminga xabar (Boshqaruv tugmalari bilan)
    markup = InlineKeyboardMarkup()
    # Callbackda faqat ID yuboramiz (xatolik bo'lmasligi uchun)
    btn_ready = InlineKeyboardButton("🟡 Tayyor (Mijozga kod yuborish)", callback_data=f"ready:{order_id}")
    btn_cancel = InlineKeyboardButton("❌ Bekor qilish", callback_data=f"cancel:{order_id}")
    markup.add(btn_ready)
    markup.add(btn_cancel)

    admin_msg = (
        f"❗️ YANGI BUYURTMA!\n\n"
        f"🆔 Zakaz ID: `{order_id}`\n"
        f"👤 Mijoz: {full_name} (@{username})\n"
        f"🍔 Taom: **{food_name}**\n\n"
        f"Tayyor bo'lganda tugmani bosing 👇"
    )
    await bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup, parse_mode="Markdown")


# ================= STATUSLARNI O'ZGARTIRISH =================

# 1. TAYYOR TUGMASI BOSILGANDA
@dp.callback_query_handler(lambda c: c.data.startswith('ready:'))
async def order_ready(call: types.CallbackQuery):
    order_id = call.data.split(":")[1]

    # Agar buyurtma xotirada bo'lmasa (server o'chib yongan bo'lsa)
    if order_id not in orders:
        await call.answer("Bu buyurtma topilmadi (eskirgan).", show_alert=True)
        return

    order = orders[order_id]
    user_id = order['user_id']
    secret_code = order['code']
    food_name = order['food']

    # --- MIJOZGA KODNI YUBORAMIZ ---
    try:
        await bot.send_message(
            user_id,
            f"😋 TAOM TAYYOR!\n\n"
            f"🍔 Buyurtma: **{food_name}**\n"
            f"🔢 SIZNING KODINGIZ: **{secret_code}**\n\n"
            f"❗️ Kassaga borib ushbu kodni ayting va taomingizni oling."
        )
    except:
        await call.answer("Mijozga xabar bormadi (bloklagan).")

    # --- ADMIN XABARINI O'ZGARTIRAMIZ ---
    markup = InlineKeyboardMarkup()
    btn_done = InlineKeyboardButton("✅ Berib yubordim (Yakunlash)", callback_data=f"done:{order_id}")
    markup.add(btn_done)

    new_text = (
        f"✅ MIJOZGA XABAR YUBORILDI!\n\n"
        f"👤 Mijoz: {order['name']}\n"
        f"🍔 Taom: {food_name}\n"
        f"🔑 **TEKSHIRISH KODI:** `{secret_code}`\n\n"
        f"Mijozdan kodni so'rang. Agar **{secret_code}** desa, taomni berib, pastdagi tugmani bosing."
    )
    await call.message.edit_text(new_text, reply_markup=markup, parse_mode="Markdown")


# 2. BERIB YUBORDIM (YAKUNLASH) TUGMASI
@dp.callback_query_handler(lambda c: c.data.startswith('done:'))
async def order_done(call: types.CallbackQuery):
    order_id = call.data.split(":")[1]

    if order_id in orders:
        del orders[order_id] # Xotiradan o'chiramiz

    await call.message.edit_text("✅ BUYURTMA YAKUNLANDI (Berib yuborildi).")
    await call.answer("Bajarildi!")


# 3. BEKOR QILISH TUGMASI
@dp.callback_query_handler(lambda c: c.data.startswith('cancel:'))
async def order_cancel(call: types.CallbackQuery):
    order_id = call.data.split(":")[1]

    if order_id in orders:
        user_id = orders[order_id]['user_id']
        try:
            await bot.send_message(user_id, "❌ Uzr, buyurtmangiz bekor qilindi.")
        except:
            pass
        del orders[order_id]

    await call.message.edit_text("❌ BUYURTMA BEKOR QILINDI.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
