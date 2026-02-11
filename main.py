import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = 'BU_YERGA_BOT_TOKEN_QOYILADI' # BotFatherdan olgan tokeningiz
ADMIN_ID = 123456789  # O'z telegram ID raqamingizni yozing (userinfobot orqali bilsa bo'ladi)

# --- BOTNI ISHGA TUSHIRISH ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- XOTIRA (Menyu) ---
# Format: {"lavash": 25000, "burger": 15000}
menu = {}

# --- HOLATLAR (STATES) ---
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

# --- FOYDALANUVCHI QISMI ---

@dp.message_handler(commands=['start'])
async def user_start(message: types.Message):
    if not menu:
        await message.answer("Hozircha menyu bo'sh. Iltimos keyinroq kiring.")
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for food, price in menu.items():
        # Callback data format: buy:ovqat_nomi
        btn = InlineKeyboardButton(text=f"{food} - {price} so'm", callback_data=f"buy:{food}")
        markup.add(btn)
    
    await message.answer("Assalomu alaykum! Buyurtma berish uchun taomni tanlang:", reply_markup=markup)

# Buyurtmani qabul qilish
@dp.callback_query_handler(lambda c: c.data.startswith('buy:'))
async def process_order(callback_query: types.CallbackQuery):
    food_name = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    
    await bot.answer_callback_query(callback_query.id, text="Buyurtma yuborildi!")
    await bot.send_message(user_id, f"✅ {food_name} buyurtmangiz adminga yuborildi. Kuting...")

    # Adminga xabar yuborish
    admin_markup = InlineKeyboardMarkup()
    # Callback data format: ready:user_id:food_name
    btn_ready = InlineKeyboardButton("🟢 Tayyor (Xabar berish)", callback_data=f"ready:{user_id}:{food_name}")
    admin_markup.add(btn_ready)
    
    msg = f"❗️ YANGI BUYURTMA!\n\n👤 Mijoz: @{username}\n🍽 Taom: {food_name}\n🆔 ID: {user_id}"
    await bot.send_message(ADMIN_ID, msg, reply_markup=admin_markup)

# --- OSHXONACHI (ADMIN) UCHUN STATUS ---

@dp.callback_query_handler(lambda c: c.data.startswith('ready:'))
async def notify_user(callback_query: types.CallbackQuery):
    _, user_id, food_name = callback_query.data.split(":")
    
    # Mijozga xabar
    try:
        await bot.send_message(int(user_id), f"📢 DIQQAT!\n\nSiz buyurtma qilgan **{food_name}** tayyor bo'ldi! \nOlib ketishingiz yoki kurer kutishingiz mumkin.")
        await bot.answer_callback_query(callback_query.id, text="Mijozga xabar yuborildi ✅")
        await callback_query.message.edit_text(callback_query.message.text + "\n\n✅ TAYYORLANDI")
    except Exception as e:
        await bot.answer_callback_query(callback_query.id, text="Mijozga yuborib bo'lmadi (bloklagan bo'lishi mumkin).")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
