import asyncio
import logging
import random
import string
from telegram import Update, constants
from telegram.ext import ContextTypes
from ..system import system
from ..decorators import retry_backoff
from ..config import STORAGE_CHANNEL_ID

logger = logging.getLogger("XiaoBot.Messages")

def generate_key(length=12):
    return ''.join(random.choices(string.ascii_uppercase, k=length))

# Simulasi Fungsi Download
@retry_backoff()
async def fetch_reels_data(url: str):
    # Logika download asli diletakkan di sini
    await asyncio.sleep(2) 
    return {"url": url, "status": "success"}

async def reels_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = update.effective_chat
    message = update.message
    
    if not message: return
    
    logger.info(f"Received msg in chat: {chat.type} {chat.id}, thread: {getattr(message, 'message_thread_id', None)}, photo: {bool(message.photo)}, video: {bool(message.video)}")
    
    # 1. Handle Auto-Topic to Link & Catalog
    auto_topic = system.settings_db.get("auto_topic", {})
    if chat.type in ['group', 'supergroup'] and chat.id == auto_topic.get("chat_id"):
        if getattr(message, 'message_thread_id', None) == auto_topic.get("thread_id") or auto_topic.get("thread_id") is None:
            # 1a. Handle Poster Upload
            if message.photo and message.caption:
                photo_id = message.photo[-1].file_id
                caption = message.caption
                lines = caption.split('\n')
                
                title = "Unknown"
                for line in lines:
                    if line.strip():
                        title = line.strip()
                        break
                        
                # Tambahkan ke antrean _pending di catalog_db
                import time
                if "_pending" not in system.catalog_db:
                    system.catalog_db["_pending"] = []
                
                # Cleanup expired pending items (7 hours = 25200 seconds)
                now = time.time()
                system.catalog_db["_pending"] = [p for p in system.catalog_db["_pending"] if now - p['ts'] < 25200]
                
                
                import re
                link_match = re.search(r't\.me/\S+\?start=([A-Za-z0-9]+)', caption)
                if link_match:
                    video_key = link_match.group(1)
                    bot_username = (await context.bot.get_me()).username
                    final_link = f"https://t.me/{bot_username}?start={video_key}"
                    
                    import string, random
                    c_key = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
                    system.catalog_db[c_key] = {
                        "user_id": user_id,
                        "title": title,
                        "photo_id": photo_id,
                        "caption": caption,
                        "link": final_link
                    }
                    system.save_all()
                    
                    if STORAGE_CHANNEL_ID:
                        await context.bot.send_message(chat_id=STORAGE_CHANNEL_ID, text=f"✅ <b>Poster Ter-Publis (Instan)!</b>\n\nPoster <b>{title}</b> berhasil mendeteksi Link di caption dan langsung ter-publis ke Katalog!\n\n🔗 Link Video: <code>{final_link}</code>", parse_mode=constants.ParseMode.HTML)
                    return
                
                system.catalog_db["_pending"].append({
                    "user_id": user_id,
                    "title": title,
                    "photo_id": photo_id,
                    "caption": caption,
                    "ts": now
                })
                system.save_all()
                
                if STORAGE_CHANNEL_ID:
                    await context.bot.send_message(chat_id=STORAGE_CHANNEL_ID, text=f"⏳ <b>Poster Ditangkap: {title}</b>\n\nPoster masuk daftar antrean! Bot akan menunggu Video diunggah.", parse_mode=constants.ParseMode.HTML)
                return
                
            # 1b. Handle Video Upload
            elif message.video or message.document:
                try:
                    if not STORAGE_CHANNEL_ID:
                        await message.reply_text("⚠️ Error: STORAGE_CHANNEL_ID belum dikonfigurasi di .env")
                        return
                    
                    forwarded = await context.bot.copy_message(
                        chat_id=STORAGE_CHANNEL_ID,
                        from_chat_id=chat.id,
                        message_id=message.message_id
                    )
                    
                    vid_key = generate_key()
                    system.video_db[vid_key] = forwarded.message_id
                    
                    bot_username = (await context.bot.get_me()).username
                    link = f"https://t.me/{bot_username}?start={vid_key}"
                    
                    # Cek apakah ada poster di antrean
                    import time
                    now = time.time()
                    pending_queue = system.catalog_db.get("_pending", [])
                    # Buang yang kadaluarsa (> 7 jam)
                    pending_queue = [p for p in pending_queue if now - p['ts'] < 25200]
                    system.catalog_db["_pending"] = pending_queue
                    
                    if pending_queue:
                        # Cari poster di antrean yang diupload oleh user yang SAMA
                        user_posters = [p for p in pending_queue if p.get('user_id') == user_id]
                        
                        if user_posters:
                            paired_poster = user_posters[0]
                            pending_queue.remove(paired_poster) # Hapus dari antrean utama
                            
                            import string, random
                            c_key = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
                            system.catalog_db[c_key] = {
                                "title": paired_poster["title"],
                                "photo_id": paired_poster["photo_id"],
                                "caption": paired_poster["caption"],
                                "link": link
                            }
                            if STORAGE_CHANNEL_ID:
                                await context.bot.send_message(
                                    chat_id=STORAGE_CHANNEL_ID,
                                    text=f"✅ <b>Katalog Ter-Publis!</b>\n\nPoster <b>{paired_poster['title']}</b> telah disambungkan dengan Video ini dan resmi masuk ke database Pencarian!\n\n🔗 Link Video: <code>{link}</code>",
                                    parse_mode=constants.ParseMode.HTML
                                )
                        else:
                            # Jika tidak ada poster dari user ini, hanya jadikan Link biasa
                            if STORAGE_CHANNEL_ID:
                                await context.bot.send_message(
                                    chat_id=STORAGE_CHANNEL_ID,
                                    text=f"✅ <b>File Otomatis Dikonversi!</b>\n(Tidak ada poster antrean untuk Anda)\n\nLink Akses:\n<code>{link}</code>",
                                    parse_mode=constants.ParseMode.HTML
                                )
                    else:
                        # Jika tidak ada poster sama sekali di antrean
                        if STORAGE_CHANNEL_ID:
                            await context.bot.send_message(
                                chat_id=STORAGE_CHANNEL_ID,
                                text=f"✅ <b>File Otomatis Dikonversi!</b>\n(Tidak ada poster di antrean)\n\nLink Akses:\n<code>{link}</code>",
                                parse_mode=constants.ParseMode.HTML
                            )
                        
                    system.save_all()
                except Exception as e:
                    await message.reply_text(f"❌ Gagal memproses file/video:\n<code>{e}</code>", parse_mode=constants.ParseMode.HTML)
            return # Block regular logic in this topic

    
    # Handle Video input for 'adm_video_to_link' directly
    if user_id in system.admin_states and system.admin_states[user_id] == "adm_video_to_link":
        if not update.message.video and not update.message.document:
            await update.message.reply_text("⚠️ Gagal: Mohon kirimkan file Video!")
            del system.admin_states[user_id]
            return
            
        try:
            # Forward to storage channel
            if not STORAGE_CHANNEL_ID:
                await update.message.reply_text("⚠️ Error: STORAGE_CHANNEL_ID belum dikonfigurasi di .env")
                del system.admin_states[user_id]
                return
                
            forwarded = await context.bot.copy_message(
                chat_id=STORAGE_CHANNEL_ID,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
            
            # Save to Database
            vid_key = generate_key()
            system.video_db[vid_key] = forwarded.message_id
            system.save_all()
            
            bot_username = (await context.bot.get_me()).username
            link = f"https://t.me/{bot_username}?start={vid_key}"
            
            await update.message.reply_text(
                f"✅ <b>Video Berhasil Diproses!</b>\n\nLink Akses:\n<code>{link}</code>\n\nSilakan bagikan link ini.",
                parse_mode=constants.ParseMode.HTML
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Terjadi kesalahan saat memproses video:\n<code>{e}</code>", parse_mode=constants.ParseMode.HTML)
            
        del system.admin_states[user_id]
        return

    # Handle text or photo inputs
    text = update.message.text or update.message.caption or ""
    photo = update.message.photo
    if not text and not photo:
        return
        
    # --- ADMIN TEXT INPUT INTERCEPTOR ---
    if user_id in system.admin_states:
        state = system.admin_states.pop(user_id) # Get and clear state
        response = ""
        
        if state == "adm_add_fsub":
            channels = system.settings_db.get("fsub_channels", [])
            if text not in channels:
                channels.append(text)
                system.settings_db["fsub_channels"] = channels
            response = f"✅ Channel Fsub <b>{text}</b> berhasil ditambahkan!"
        elif state == "adm_del_fsub":
            channels = system.settings_db.get("fsub_channels", [])
            if text in channels:
                channels.remove(text)
                system.settings_db["fsub_channels"] = channels
                response = f"✅ Channel Fsub <b>{text}</b> berhasil dihapus!"
            else:
                response = f"⚠️ Channel Fsub <b>{text}</b> tidak ditemukan."
        elif state == "adm_set_saweria":
            system.settings_db["saweria_link"] = text
            response = f"✅ Link Saweria berhasil diubah menjadi:\n{text}"
        elif state == "adm_set_qris":
            if update.message.photo:
                file_id = update.message.photo[-1].file_id
                system.settings_db["qris_file_id"] = file_id
                system.save_all()
                await update.message.reply_text("✅ Foto QRIS berhasil diunggah dan disimpan!")
                return
            else:
                await update.message.reply_text("⚠️ Anda harus mengirim FOTO (Bukan dokumen/teks). Silakan ulangi.")
                return
        elif state == "adm_set_saweria_overlay":
            system.settings_db["saweria_overlay"] = text
            system.save_all()
            await update.message.reply_text("✅ Link Overlay Saweria berhasil disimpan.\nSistem Auto-Approve telah aktif!")
            return
        elif state == "adm_set_start":
            system.settings_db["start_message"] = text
            response = "✅ Start Message berhasil diperbarui!"
        elif state == "adm_set_premium":
            system.settings_db["premium_price"] = text
            response = f"✅ Harga Premium berhasil diubah menjadi:\n<b>{text}</b>"
        elif state == "adm_db_channel":
            system.settings_db["db_channel"] = text
            response = f"✅ DB Channel diubah ke:\n<code>{text}</code>"
        elif state == "adm_set_topic":
            # https://t.me/c/3857149032/1795 -> chat_id: -1003857149032, thread_id: 1795
            try:
                parts = text.strip('/').split('/')
                thread_id = int(parts[-1])
                chat_raw = parts[-2]
                chat_id = int(f"-100{chat_raw}")
                system.settings_db["auto_topic"] = {"chat_id": chat_id, "thread_id": thread_id}
                response = f"✅ Auto-Link Topic berhasil diset ke:\nChat ID: <code>{chat_id}</code>\nThread ID: <code>{thread_id}</code>\n\nSetiap video yang dikirim khusus ke dalam topik tersebut akan otomatis di-Link."
            except Exception as e:
                response = f"❌ URL Tidak Valid:\n<code>{e}</code>\n\nPastikan formatnya seperti https://t.me/c/123/456"
        elif state == "adm_broadcast":
            await update.message.reply_text("⏳ <i>Mengirim broadcast ke semua user...</i>", parse_mode=constants.ParseMode.HTML)
            count = 0
            for uid in system.users_db.get('users', []):
                try:
                    await context.bot.send_message(uid, f"📢 <b>PENGUMUMAN</b>\n\n{text}", parse_mode=constants.ParseMode.HTML)
                    count += 1
                except: pass
            response = f"✅ Broadcast berhasil terkirim ke <b>{count}</b> user."
        else:
            response = f"✅ Konfigurasi untuk <code>{state}</code> disimpan:\n{text}"

        system.save_all()
        await update.message.reply_text(response, parse_mode=constants.ParseMode.HTML)
        return
    # --- END ADMIN INTERCEPTOR ---

    if "instagram.com" not in text.lower():
        return

    if not system.check_spam(user_id):
        return

    lock = system.get_lock(user_id)
    if lock.locked():
        await update.message.reply_text("⏳ Masih ada proses yang berjalan...")
        return

    async with lock:
        msg = await update.message.reply_text("⚡ <b>Memproses...</b>", parse_mode=constants.ParseMode.HTML)
        try:
            data = await fetch_reels_data(text)
            
            # Save stats
            system.dataCache['stats']['total_processed'] += 1
            system.save_data()
            
            await msg.edit_text(f"✅ <b>Selesai!</b>\n\nLink: {data['url']}", parse_mode=constants.ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error processing reels: {e}")
            await msg.edit_text(f"❌ <b>Error:</b> {str(e)}", parse_mode=constants.ParseMode.HTML)
