import logging
import os
import random
import uuid
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = os.getenv("BOT_TOKEN")

# --- ADMIN ID NI O'ZGARTIRISH KERAK ---
# Hozircha shu raqam tursin, pastda botning o'zi sizga IDingizni aytadi
ADMIN_ID = 1406969675 

# --- BOTNI ISHGA TUSHIRISH ---
logging.basicConfig(level=logging.INFO)

# Token tekshiruvi (xatolik bo'lsa ham bot o'chmaydi, log yozadi)
if not API_TOKEN:
    print("DIQQAT! BOT_TOKEN topilmadi!")
    bot = Bot(token="123456:FAKE_TOKEN") # Fake token to prevent crash import
else:
    bot = Bot(token=API_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- MA'LUMOTLAR BAZASI (RAM) ---
menu = {}  # { "Lavash": 25000 }
orders = {} # { "order_id": {...} }

# --- HOLATLAR ---
class AdminState(StatesGroup):
    name = State()
    price = State()
    delete = State()

# ================= TUGMALAR =================
def main_menu_btn(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    # Agar foydalanuvchi ADMIN bo'lsa, unga admin tugmalari chiqadi
    if user_id == ADMIN_ID:
        markup.add("➕ Ovqat qo'shish", "➖ Ovqat o'chirish")
        markup.add("📋 Menyuni ko'rish")
    else:
        # Oddiy odamga faqat buyurtma tugmasi (Aslida menyu startda chiqadi)
        markup.add("📞 Biz bilan aloqa")
    return markup

# ================= START BUYRUG'I =================
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    
    # DIQQAT: Bu yerda IDingizni ko'rsatadi
    text = f"Assalomu alaykum! Xush kelibsiz.\n\n🆔 Sizning ID raqamingiz: `{user_id}`"
    
    if user_id != ADMIN_ID:
        text += "\n\n⚠️ Siz hozir **ADMIN EMASSIZ**.\nAdmin bo'lish uchun `main.py` faylidagi `ADMIN_ID` ni shu raqamga o'zgartiring!"
    else:
        text += "\n\n✅ Siz **ADMIN** sifatida tanildingiz."

    # Menyuni chiqarish
    markup = InlineKeyboardMarkup(row_width=1)
    if not menu:
        text += "\n\nMenyu hozircha bo'sh."
    else:
        text += "\n\n👇 Buyurtma berish uchun tanlang:"
        for food, price in menu.items():
            markup.add(InlineKeyboardButton(f"{food} - {price} so'm", callback_data=f"buy:{food}"))

    await message.answer(text, reply_markup=main_menu_btn(user_id))
    if markup.inline_keyboard:
        await message.answer("Taomlar:", reply_markup=markup)


# ================= ADMIN: OVQAT QO'SHISH =================
@dp.message_handler(text="➕ Ovqat qo'shish")
async def add_food_start(message: types.Message):
    # Admin tekshiruvi
    if message.from_user.id != ADMIN_ID:
        await message.answer(f"Siz admin emassiz! Sizning ID: {message.from_user.id}")
        return

    await AdminState.name.set()
    await message.answer("Yangi ovqat nomini yozing (masalan: Burger):", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=AdminState.name)
async def add_food_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await AdminState.price.set()
    await message.answer("Narxini yozing (faqat raqam, masalan: 15000):")

@dp.message_handler(state=AdminState.price)
async def add_food_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam yozing!")
        return
    
    async with state.proxy() as data:
        name = data['name']
        price = int(message.text)
        menu[name] = price
    
    await state.finish()
    await message.answer(f"✅ **{name}** menyuga qo'shildi!", reply_markup=main_menu_btn(message.from_user.id))


# ================= ADMIN: MENYU KO'RISH =================
@dp.message_handler(text="📋 Menyuni ko'rish")
async def show_menu_handler(message: types.Message):
    if not menu:
        await message.answer("Menyu bo'sh.")
        return
    
    msg = "📜 **MENYU:**\n"
    for k, v in menu.items():
        msg += f"▫️ {k} — {v} so'm\n"
    await message.answer(msg)


# ================= ADMIN: OVQAT O'CHIRISH =================
@dp.message_handler(text="➖ Ovqat o'chirish")
async def delete_food_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    if not menu:
        await message.answer("O'chiradigan hech narsa yo'q.")
        return

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for food in menu:
        markup.add(food)
    markup.add("Bekor qilish")
    
    await AdminState.delete.set()
    await message.answer("Qaysi ovqatni o'chiramiz?", reply_markup=markup)

@dp.message_handler(state=AdminState.delete)
async def delete_food_finish(message: types.Message, state: FSMContext):
    food = message.text
    if food in menu:
        del menu[food]
        await message.answer(f"🗑 {food} o'chirildi.", reply_markup=main_menu_btn(message.from_user.id))
    else:
        await message.answer("Bekor qilindi.", reply_markup=main_menu_btn(message.from_user.id))
    
    await state.finish()


# ================= MIJOZ: BUYURTMA BERISH =================
@dp.callback_query_handler(lambda c: c.data.startswith('buy:'))
async def buy_process(call: types.CallbackQuery):
    food = call.data.split(":")[1]
    user_id = call.from_user.id
    name = call.from_user.full_name
    
    # ID va Kod generatsiya
    order_id = str(uuid.uuid4())[:8]
    secret_code = random.randint(1000, 9999)
    
    orders[order_id] = {
        'user_id': user_id,
        'food': food,
        'code': secret_code,
        'name': name
    }
    
    # Mijozga javob
    await call.answer("Buyurtma qabul qilindi ✅")
    await bot.send_message(user_id, f"✅ **{food}** buyurtma qilindi.\nTayyor bo'lganda KOD keladi...")
    
    # Adminga xabar
    admin_markup = InlineKeyboardMarkup()
    admin_markup.add(InlineKeyboardButton("🟡 Tayyor (Kod yuborish)", callback_data=f"ready:{order_id}"))
    admin_markup.add(InlineKeyboardButton("❌ Bekor qilish", callback_data=f"cancel:{order_id}"))
    
    await bot.send_message(ADMIN_ID, f"🆕 **YANGI BUYURTMA!**\n\n👤 {name}\n🍔 {food}\n🆔 ID: `{order_id}`", reply_markup=admin_markup)


# ================= STATUSLAR =================
@dp.callback_query_handler(lambda c: c.data.startswith('ready:'))
async def ready_process(call: types.CallbackQuery):
    order_id = call.data.split(":")[1]
    if order_id not in orders:
        await call.answer("Eski buyurtma (topilmadi).", show_alert=True)
        return
    
    data = orders[order_id]
    
    # Mijozga kod yuborish
    try:
        await bot.send_message(data['user_id'], f"📢 **DIQQAT!**\n\n🍔 {data['food']} tayyor!\n🔢 KODINGIZ: **{data['code']}**\n\nBoring oling.")
    except:
        pass
    
    # Admin panelini yangilash
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Berib yubordim", callback_data=f"done:{order_id}"))
    
    await call.message.edit_text(f"✅ **MIJOZGA XABAR BORDI!**\n\nKOD: **{data['code']}**\nMijozdan shu kodni so'rang.", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data.startswith('done:'))
async def done_process(call: types.CallbackQuery):
    order_id = call.data.split(":")[1]
    if order_id in orders:
        del orders[order_id]
    await call.message.edit_text("✅ Buyurtma yopildi.")

@dp.callback_query_handler(lambda c: c.data.startswith('cancel:'))
async def cancel_process(call: types.CallbackQuery):
    order_id = call.data.split(":")[1]
    if order_id in orders:
        try:
            await bot.send_message(orders[order_id]['user_id'], "❌ Buyurtmangiz bekor qilindi.")
        except:
            pass
        del orders[order_id]
    await call.message.edit_text("❌ Bekor qilindi.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
