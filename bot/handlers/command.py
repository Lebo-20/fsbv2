import logging
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes
from ..config import VERSION, ADMIN_ID
from ..system import system

logger = logging.getLogger("XiaoBot.Commands")

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    user_id = user.id

    # Register user
    if user_id not in system.users_db['users']:
        system.users_db['users'].append(user_id)
        system.save_all()

    # Deep-linking support: /start [drama_key] or /start [vid_key]
    if args:
        key = args[0]
        if key in system.video_db:
             try:
                 val = system.video_db[key]
                 if isinstance(val, int) or str(val).isdigit():
                     from ..config import STORAGE_CHANNEL_ID
                     await context.bot.copy_message(
                         chat_id=user_id,
                         from_chat_id=STORAGE_CHANNEL_ID or system.settings_db.get("db_channel") or "-1002231917615",
                         message_id=int(val)
                     )
                 else:
                     # Fallback to direct file_id send
                     await context.bot.send_video(chat_id=user_id, video=val)
             except Exception as e:
                 await update.message.reply_text("⚠️ Gagal memuat video. Kemungkinan file ditarik dari server atau file_id kedaluwarsa.")
             return
        elif key in system.drama_db:
             # Drama view logic
             await update.message.reply_text(f"🎬 <b>Memuat Drama: {key}...</b>", parse_mode=constants.ParseMode.HTML)
             return

    welcome_text = (
        f"<b>✨ Xiao Reels Bot v{VERSION} ✨</b>\n\n"
        f"Halo {user.first_name}! Selamat Bergabung di Short Drama Team DL.\n"
        "Silakan pilih menu di bawah ini:"
    )
    
    keyboard = [
        [InlineKeyboardButton("💎 Status VIP", callback_data="nav_vip_status"), InlineKeyboardButton("💰 Beli VIP", callback_data="nav_vip_buy")],
        [InlineKeyboardButton("🎬 Home", callback_data="nav_home"), InlineKeyboardButton("📊 Stats", callback_data="nav_stats")],
        [InlineKeyboardButton("📜 History", callback_data="nav_history"), InlineKeyboardButton("🔍 Cari Video", callback_data="nav_search")]
    ]
    
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="nav_admin")])
        
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)

# --- USER COMMANDS ---

async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    history = system.history_db.get(str(user_id), [])
    
    if not history:
        await update.message.reply_text("📜 Riwayat tontonan Anda masih kosong.")
        return
        
    text = "📜 <b>Riwayat Tontonan Terakhir:</b>\n\n"
    for item in history[-5:]: # Last 5
        text += f"• {item['title']} (Part {item['part']})\n"
        
    await update.message.reply_text(text, parse_mode=constants.ParseMode.HTML)

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).lower().strip()
    # Strip common prefixes from query accidentally copy-pasted by user
    import re
    query = re.sub(r'[^a-zA-Z0-9\s]', '', query) # Remove emojis and punctuation
    query = query.replace("full episode", "").strip()
    
    if not query:
        await update.message.reply_text("💡 Format: `/cari [Judul Drama]`\nContoh: `/cari The Heir`", parse_mode=constants.ParseMode.MARKDOWN)
        return
        
    results = []
    
    # Search in Catalog DB (Single Videos / Formatted Posters)
    for c_key, cat in system.catalog_db.items():
        if c_key == "_pending": continue
        
        c_title = re.sub(r'[^a-zA-Z0-9\s]', '', cat.get('title', '').lower())
        if query in c_key.lower() or query in c_title:
            results.append({
                "type": "catalog",
                "key": c_key,
                "title": f"🎬 {cat.get('title', c_key)}"
            })
            
    # Search in Multi-part Drama DB
    for key, drama in system.drama_db.items():
        d_title = re.sub(r'[^a-zA-Z0-9\s]', '', drama['title'].lower())
        if query in d_title:
            results.append({
                "type": "drama",
                "key": key,
                "title": f"🎬 {drama['title']}"
            })
            
    if not results:
        await update.message.reply_text(f"❌ Tidak ditemukan judul yang mengandung kata: <b>{query}</b>", parse_mode=constants.ParseMode.HTML)
        return
        
    text = f"🔍 <b>Hasil Pencarian ({len(results)} ditemukan):</b>\n\n"
    keyboard = []
    for res in results[:10]: # Max 10 results
        if res["type"] == "catalog":
            keyboard.append([InlineKeyboardButton(res['title'], callback_data=f"show_cat_{res['key']}")])
        else:
            keyboard.append([InlineKeyboardButton(res['title'], callback_data=f"nav_part_{res['key']}_1")])
        
    if len(results) > 10:
        text += "<i>Hanya menampilkan 10 hasil teratas. Silakan gunakan kata kunci yang lebih spesifik.</i>"
        
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)

# --- ADMIN COMMANDS ---

def admin_required(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("⚠️ Anda bukan admin.")
            return
        return await func(update, context)
    return wrapper

@admin_required
async def add_catalog_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Command used as caption to a photo
    if not update.message.photo:
        await update.message.reply_text("❌ Harus dikirim sebagai Basa/Kepsyen dalam FOTO poster drama!")
        return
        
    args = context.args
    if not args:
        await update.message.reply_text("❌ Anda belum memasukkan Link bot target.\nFormat: `/add_catalog [Link Bot] [Enter] [Judul/Deskripsi...]`")
        return
        
    link = args[0]
    photo_id = update.message.photo[-1].file_id
    
    # The caption text excluding the `/add_catalog [link]` part
    caption_text = update.message.caption or ""
    # Split by newline, usually the title is the very first line after the command
    lines = caption_text.split("\n")
    
    # Find title
    title = "Unknown Title"
    for line in lines:
        if line.strip() and not line.startswith("/add_catalog"):
            title = line.strip()
            break
            
    # Clean the text to be saved as the Description (Synopis) body
    clean_caption = caption_text.replace(f"/add_catalog {link}", "").strip()
    if clean_caption.startswith("/add_catalog"):
        clean_caption = clean_caption.replace("/add_catalog", "").strip()
        
    # Generate unique ID for this catalog entry
    import string, random
    c_key = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    
    system.catalog_db[c_key] = {
        "title": title,
        "photo_id": photo_id,
        "caption": clean_caption,
        "link": link
    }
    system.save_all()
    
    await update.message.reply_text(f"✅ <b>Katalog Berhasil Tersimpan!</b>\n\nKini jika user men-/cari kata: `{title}`, Poster dan link ini akan muncul otomatis!", parse_mode=constants.ParseMode.HTML)


@admin_required
async def upload_drama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Simplified logic: /upload_drama [key] [title] [total_parts]
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("💡 Format: <code>/upload_drama [key] [title] [total_parts]</code>", parse_mode=constants.ParseMode.HTML)
        return
    
    key, title, total = args[0], args[1], args[2]
    system.drama_db[key] = {
        "title": title,
        "total_parts": int(total),
        "parts": {}, # msg_id mapping
        "is_free": True
    }
    system.save_all()
    await update.message.reply_text(f"✅ Drama <b>{title}</b> berhasil didaftarkan!", parse_mode=constants.ParseMode.HTML)

@admin_required
async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = system.stats_db['total_views']
    text = f"📊 <b>Statistik Sistem</b>\n\nTotal Views: <code>{total}</code>\nTotal Users: <code>{len(system.users_db['users'])}</code>"
    await update.message.reply_text(text, parse_mode=constants.ParseMode.HTML)

@admin_required
async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("💡 Format: `/broadcast [pesan]`")
        return
    
    count = 0
    for uid in system.users_db['users']:
        try:
            await context.bot.send_message(uid, f"📢 <b>PENGUMUMAN</b>\n\n{text}", parse_mode=constants.ParseMode.HTML)
            count += 1
        except: pass
    
    await update.message.reply_text(f"✅ Berhasil mengirim pesan ke {count} pengguna.")

@admin_required
async def unban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    uid = int(context.args[0])
    if uid in system.users_db.get('banned', []):
        system.users_db['banned'].remove(uid)
        system.save_all()
        await update.message.reply_text(f"✅ User {uid} telah di-unban.")
    else:
        await update.message.reply_text("User tidak ditemukan di daftar ban.")
