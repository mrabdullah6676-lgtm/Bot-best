import logging
import sqlite3
import random
import os
import yt_dlp
import threading
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

# --- SETTINGS (Aapka Token aur ID yahan fix hai) ---
TOKEN = "8607497062:AAEY1yzvZuZENPSUPWNr0ejf414OSDFegbU"
ADMIN_ID = 8021525024 

# --- FLASK SERVER (Render 24/7 Fix) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Alive and Running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- DATABASE SETUP ---
conn = sqlite3.connect('mega_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, 
    username TEXT, 
    wallet INTEGER DEFAULT 500, 
    bank INTEGER DEFAULT 0,
    last_work TEXT
)''')
conn.commit()

# --- HELPERS ---
def get_user(user_id, username="User"):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    if not res:
        cursor.execute('INSERT INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        res = cursor.fetchone()
    return list(res)

def update_user(user_id, column, value):
    cursor.execute(f'UPDATE users SET {column} = ? WHERE user_id = ?', (value, user_id))
    conn.commit()

# --- COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🔥 **The Ultimate Bot is Ready!**\n\n"
        "💰 **Economy:**\n"
        "• /bal - Check money\n"
        "• /work - Earn coins\n"
        "• /dep <amt> - Bank mein dalo\n"
        "• /with <amt> - Bank se nikalo\n"
        "• /rob - Loot someone (Reply)\n"
        "• /slots <amt> - Gamble coins\n\n"
        "📥 **Downloader:**\n"
        "• /download <link/naam> - Get any video (50 🪙)"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def bal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id, update.effective_user.username)
    await update.message.reply_text(f"💰 **Wallet:** {user[2]} 🪙\n🏦 **Bank:** {user[3]} 🪙")

async def work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    now = datetime.now()
    if user[4] and (now - datetime.fromisoformat(user[4])).total_seconds() < 3600:
        remain = 60 - int((now - datetime.fromisoformat(user[4])).total_seconds() // 60)
        return await update.message.reply_text(f"⏳ {remain} mins baad aana!")
    
    earn = random.randint(300, 1000)
    update_user(uid, 'wallet', user[2] + earn)
    update_user(uid, 'last_work', now.isoformat())
    await update.message.reply_text(f"⚒️ Mehnat rang layi! Aapne {earn} 🪙 kamaye.")

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    try:
        amt = int(context.args[0]) if context.args[0] != "all" else user[2]
        if amt > user[2] or amt <= 0: raise ValueError
        update_user(uid, 'wallet', user[2] - amt); update_user(uid, 'bank', user[3] + amt)
        await update.message.reply_text(f"🏦 {amt} 🪙 bank mein safe ho gaye!")
    except: await update.message.reply_text("Usage: `/dep <amount/all>`")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    try:
        amt = int(context.args[0]) if context.args[0] != "all" else user[3]
        if amt > user[3] or amt <= 0: raise ValueError
        update_user(uid, 'bank', user[3] - amt); update_user(uid, 'wallet', user[2] + amt)
        await update.message.reply_text(f"💰 {amt} 🪙 nikaal liye!")
    except: await update.message.reply_text("Usage: `/with <amount/all>`")

async def slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    try:
        bet = int(context.args[0])
        if bet > user[2] or bet < 100: return await update.message.reply_text("Min bet 100 🪙 hai.")
        items = ["🍒", "💎", "🍋", "7️⃣", "🍀"]
        res = [random.choice(items) for _ in range(3)]
        msg = " | ".join(res)
        if res[0] == res[1] == res[2]:
            win = bet * 10
            update_user(uid, 'wallet', user[2] + win)
            await update.message.reply_text(f"[{msg}]\n\n🔥 **JACKPOT!** Aapne {win} 🪙 jeete!")
        elif res[0] == res[1] or res[1] == res[2]:
            win = bet * 2
            update_user(uid, 'wallet', user[2] + win)
            await update.message.reply_text(f"[{msg}]\n\n✨ **Win!** {win} 🪙 mile.")
        else:
            update_user(uid, 'wallet', user[2] - bet)
            await update.message.reply_text(f"[{msg}]\n\n💀 Haar gaye! -{bet} 🪙")
    except: await update.message.reply_text("Usage: `/slots <amount>`")

async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not update.message.reply_to_message: return await update.message.reply_text("Reply to someone!")
    vic_id = update.message.reply_to_message.from_user.id
    vic, robb = get_user(vic_id), get_user(uid)
    if vic[2] < 500: return await update.message.reply_text("Iske paas kuch nahi hai.")
    if random.choice([True, False, False]):
        stolen = random.randint(100, vic[2] // 2)
        update_user(vic_id, 'wallet', vic[2] - stolen); update_user(uid, 'wallet', robb[2] + stolen)
        await update.message.reply_text(f"🥷 Safal chori! {stolen} 🪙 loot liye.")
    else:
        fine = 400
        update_user(uid, 'wallet', max(0, robb[2] - fine))
        await update.message.reply_text(f"👮 Police! {fine} 🪙 jurmana.")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    cost = 50
    if user[2] < cost: return await update.message.reply_text("Downloader ke liye 50 🪙 chahiye!")
    query = " ".join(context.args)
    if not query: return await update.message.reply_text("Link ya Naam dalo!")
    msg = await update.message.reply_text("🚀 Downloader start ho raha hai...")
    update_user(uid, 'wallet', user[2] - cost)
    ydl_opts = {'format': 'best', 'outtmpl': f'downloads/{uid}_%(id)s.%(ext)s', 'max_filesize': 48000000, 'quiet': True}
    try:
        search = f"ytsearch1:{query}" if "http" not in query else query
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search, download=True)
            if 'entries' in info: info = info['entries'][0]
            f_path = ydl.prepare_filename(info)
        await msg.edit_text("📤 Uploading...")
        with open(f_path, 'rb') as f:
            await context.bot.send_video(chat_id=update.effective_chat.id, video=f, caption=f"✅ {info['title']}")
        os.remove(f_path)
    except Exception as e:
        update_user(uid, 'wallet', user[2]); await update.message.reply_text(f"❌ Error: Ya toh file badi hai ya link galat. Coins wapas kar diye.")

async def add_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target, amt = int(context.args[0]), int(context.args[1])
        u = get_user(target); update_user(target, 'wallet', u[2] + amt)
        await update.message.reply_text(f"✅ User {target} ko {amt} 🪙 diye.")
    except: pass

def main():
    threading.Thread(target=run_web).start() # Flask in background
    req = HTTPXRequest(connect_timeout=30, read_timeout=30)
    app_tg = Application.builder().token(TOKEN).request(req).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(CommandHandler("bal", bal))
    app_tg.add_handler(CommandHandler("work", work))
    app_tg.add_handler(CommandHandler("dep", deposit))
    app_tg.add_handler(CommandHandler("with", withdraw))
    app_tg.add_handler(CommandHandler("slots", slots))
    app_tg.add_handler(CommandHandler("rob", rob))
    app_tg.add_handler(CommandHandler("download", download))
    app_tg.add_handler(CommandHandler("addmoney", add_money))
    print("Mega Bot is Running...")
    app_tg.run_polling()

if __name__ == '__main__':
    if not os.path.exists('downloads'): os.makedirs('downloads')
    main()
