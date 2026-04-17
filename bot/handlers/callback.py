import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes
from ..system import system
from ..config import VERSION, ADMIN_ID

async def mp_nav_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    # 1. Instant Answer for General Responsiveness
    # Ini akan langsung menghilangkan ikon loading di HP user
    if not data.startswith("nav_part_"):
        await query.answer()

    # 2. Anti-Spam Check
    allowed, wait = system.check_spam(user_id)
    if not allowed:
        # Jika spam, kita beri peringatan (ini akan otomatis me-reset tombol loading)
        await query.answer(f"⚠️ Tunggu {wait} detik.", show_alert=True)
        return

    # 3. Part Navigation logic
    if data.startswith("nav_part_"):
        _, _, key, part = data.split("_")
        part = int(part)
        
        # Beri feedback khusus memuat untuk navigasi part
        await query.answer("⏳ Memuat Part...", show_alert=False)

        if system.is_nav_locked(user_id, key, part):
            return

        drama = system.drama_db.get(key)
        if not drama:
            await query.edit_message_text("⚠️ Drama tidak ditemukan.")
            return

        # VIP Check
        if not drama.get("is_free", True) and user_id != ADMIN_ID:
            vip_data = system.vip_db.get(str(user_id))
            now = time.time()
            is_active = vip_data and vip_data.get('until', 0) > now
            has_quota = True

            if is_active and vip_data.get('type') == 'LIMITED':
                if vip_data.get('views_left', 0) > 0:
                    vip_data['views_left'] -= 1
                    system.save_all()
                else:
                    has_quota = False
            
            if not is_active or not has_quota:
                reason = "Masa aktif VIP Anda telah habis" if not is_active else "Kuota (x lihat) VIP Limited Anda telah habis"
                await query.edit_message_text(f"⚠️ {reason}. Silakan perpanjang/beli VIP untuk menonton konten Premium eksklusif ini.", 
                                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Beli/Perpanjang VIP", callback_data="nav_vip_buy")]]))
                return

        # SUCCESS LOADING PART
        msg_id = drama['parts'].get(str(part))
        if not msg_id:
            await query.edit_message_text(f"⚠️ Gagal memuat Part {part}. File tidak tersedia.",
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Coba Lagi", callback_data=f"nav_part_{key}_{part}")]]))
            return

        # Navigation Buttons
        keyboard = []
        nav_row = []
        if part > 1:
            nav_row.append(InlineKeyboardButton(f"◀️ Part {part-1}", callback_data=f"nav_part_{key}_{part-1}"))
        if part < drama['total_parts']:
            nav_row.append(InlineKeyboardButton(f"▶️ Part {part+1}", callback_data=f"nav_part_{key}_{part+1}"))
        
        if nav_row: keyboard.append(nav_row)
        keyboard.append([InlineKeyboardButton("📑 Daftar Part", callback_data=f"list_parts_{key}")])
        keyboard.append([InlineKeyboardButton("↩️ Kembali ke History", callback_data="nav_history")])

        await query.edit_message_text(
            f"🎬 <b>{drama['title']}</b>\nPart: <code>{part}/{drama['total_parts']}</code>\n\nSelamat menonton!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=constants.ParseMode.HTML
        )
        
        # Update Stats & History
        system.stats_db['total_views'] += 1
        history = system.history_db.get(str(user_id), [])
        history.append({"title": drama['title'], "key": key, "part": part, "time": time.time()})
        system.history_db[str(user_id)] = history[-10:] # Keep last 10
        system.save_all()
        return

    # 3. Base Navigation
    await query.answer()
    
    if data == "nav_history":
        history = system.history_db.get(str(user_id), [])
        if not history:
            text = "📜 Riwayat Anda kosong."
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="nav_start")]]
        else:
            text = "📜 <b>Riwayat Terakhir:</b>\n"
            keyboard = []
            for item in history[::-1]:
                keyboard.append([InlineKeyboardButton(f"• {item['title']} (P{item['part']})", callback_data=f"nav_part_{item['key']}_{item['part']}")])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="nav_start")])
    elif data == "nav_admin":
        if user_id != ADMIN_ID:
            await query.answer("❌ Akses Ditolak!", show_alert=True)
            return
            
        mission_icon = "✅" if system.settings_db.get("mission_active", False) else "❌"
        text = "<b>🛠 ADMIN PANEL - XIAO REELS</b>\n\nSilakan pilih menu manajemen di bawah ini untuk mengelola bot."
        keyboard = [
            [InlineKeyboardButton("➕ Tambah Channel Fsub", callback_data="adm_add_fsub"), InlineKeyboardButton("➖ Hapus Channel Fsub", callback_data="adm_del_fsub")],
            [InlineKeyboardButton("📊 Lihat Channel Fsub", callback_data="adm_view_fsub"), InlineKeyboardButton("👑 Kelola Admin", callback_data="adm_manage_admin")],
            [InlineKeyboardButton("👥 Daftar Member", callback_data="adm_list_members"), InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
            [InlineKeyboardButton("📂 Ubah DB Channel", callback_data="adm_db_channel")],
            [InlineKeyboardButton("🔗 Link Publik Saweria", callback_data="adm_set_saweria"), InlineKeyboardButton("🖼 Set Foto QRIS", callback_data="adm_set_qris")],
            [InlineKeyboardButton("⚙️ Set Overlay URL (Auto-Pay)", callback_data="adm_set_saweria_overlay")],
            [InlineKeyboardButton("💬 Atur Start Message", callback_data="adm_set_start"), InlineKeyboardButton("📝 Atur Auto Post", callback_data="adm_set_auto")],
            [InlineKeyboardButton("💵 Harga Premium", callback_data="adm_set_premium"), InlineKeyboardButton("🎬 Buat Multi-Part", callback_data="adm_make_multipart")],
            [InlineKeyboardButton("✏️ Edit Link", callback_data="adm_edit_link"), InlineKeyboardButton("🛡 Proteksi Konten", callback_data="adm_protect")],
            [InlineKeyboardButton("🔗 Video to Link", callback_data="adm_video_to_link"), InlineKeyboardButton(f"🎯 Misi: {mission_icon}", callback_data="adm_mission_toggle")],
            [InlineKeyboardButton("💬 Auto-Topic to Link", callback_data="adm_set_topic")],
            [InlineKeyboardButton("« Kembali", callback_data="nav_start")]
        ]
    elif data == "adm_mission_toggle":
        current = system.settings_db.get("mission_active", False)
        system.settings_db["mission_active"] = not current
        system.save_all()
        await query.answer(f"Misi diubah ke: {'AKTIF' if not current else 'NON-AKTIF'}")
        
        mission_icon = "✅" if not current else "❌"
        text = "<b>🛠 ADMIN PANEL - XIAO REELS</b>\n\nSilakan pilih menu manajemen di bawah ini untuk mengelola bot."
        keyboard = [
            [InlineKeyboardButton("➕ Tambah Channel Fsub", callback_data="adm_add_fsub"), InlineKeyboardButton("➖ Hapus Channel Fsub", callback_data="adm_del_fsub")],
            [InlineKeyboardButton("📊 Lihat Channel Fsub", callback_data="adm_view_fsub"), InlineKeyboardButton("👑 Kelola Admin", callback_data="adm_manage_admin")],
            [InlineKeyboardButton("👥 Daftar Member", callback_data="adm_list_members"), InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
            [InlineKeyboardButton("📂 Ubah DB Channel", callback_data="adm_db_channel")],
            [InlineKeyboardButton("🔗 Link Publik Saweria", callback_data="adm_set_saweria"), InlineKeyboardButton("🖼 Set Foto QRIS", callback_data="adm_set_qris")],
            [InlineKeyboardButton("⚙️ Set Overlay URL (Auto-Pay)", callback_data="adm_set_saweria_overlay")],
            [InlineKeyboardButton("💬 Atur Start Message", callback_data="adm_set_start"), InlineKeyboardButton("📝 Atur Auto Post", callback_data="adm_set_auto")],
            [InlineKeyboardButton("💵 Harga Premium", callback_data="adm_set_premium"), InlineKeyboardButton("🎬 Buat Multi-Part", callback_data="adm_make_multipart")],
            [InlineKeyboardButton("✏️ Edit Link", callback_data="adm_edit_link"), InlineKeyboardButton("🛡 Proteksi Konten", callback_data="adm_protect")],
            [InlineKeyboardButton("🔗 Video to Link", callback_data="adm_video_to_link"), InlineKeyboardButton(f"🎯 Misi: {mission_icon}", callback_data="adm_mission_toggle")],
            [InlineKeyboardButton("« Kembali", callback_data="nav_start")]
        ]
    elif data.startswith("adm_"):
        if user_id != ADMIN_ID:
            await query.answer("❌ Akses Ditolak!", show_alert=True)
            return

        # Handle Immediate Actions
        if data == "adm_view_fsub":
            channels = system.settings_db.get("fsub_channels", [])
            if not channels:
                text = "📊 <b>Daftar Channel Fsub:</b>\n<i>Belum ada channel terdaftar.</i>"
            else:
                text = "📊 <b>Daftar Channel Fsub:</b>\n" + "\n".join([f"• <code>{ch}</code>" for ch in channels])
            keyboard = [[InlineKeyboardButton("« Kembali", callback_data="nav_admin")]]
        elif data == "adm_list_members":
            total = len(system.users_db.get('users', []))
            text = f"👥 <b>Total Member:</b> <code>{total}</code> user."
            keyboard = [[InlineKeyboardButton("« Kembali", callback_data="nav_admin")]]
        else:
            # Handle Actions that require text input from Admin
            prompts = {
                "adm_add_fsub": "➕ Kirimkan ID atau Username Channel Fsub untuk ditambahkan:",
                "adm_del_fsub": "➖ Kirimkan ID atau Username Channel Fsub untuk dihapus:",
                "adm_broadcast": "📢 Kirimkan pesan yang ingin di-broadcast:",
                "adm_db_channel": "📂 Kirimkan ID Database Channel baru:",
                "adm_set_saweria": "🔗 Kirimkan **Username** akun Saweria Anda (contoh: TeamDl):",
                "adm_set_qris": "🖼 Kirimkan langsung berupa FOTO (image), kode Barcode QRIS Saweria Anda ke bot ini:",
                "adm_set_saweria_overlay": "⚙️ <b>Sistem Auto-Approve</b>\nKirimkan Link Overlay/Widget OBS Anda dari Dashboard Saweria:",
                "adm_set_start": "💬 Kirimkan pesan Start Message baru:",
                "adm_set_auto": "📝 Kirimkan konfigurasi Auto Post:",
                "adm_set_premium": "💵 Kirimkan nominal harga Premium baru:",
                "adm_set_topic": "💬 Kirimkan link Topik Channel (contoh: https://t.me/c/3857149032/1795):",
                "adm_make_multipart": "🎬 Kirimkan ID/URL Video Multi-Part:",
                "adm_video_to_link": "🔗 <b>Video to Link Mode Aktif!</b>\n\nSilakan forward atau kirimkan file video MP4 ke bot ini untuk mendapatkan Link permanen.",
                "adm_edit_link": "✏️ Kirimkan Link lama dan Link baru:",
                "adm_protect": "🛡 Kirimkan status proteksi (On/Off):",
                "adm_manage_admin": "👑 Kirimkan User ID untuk dijadikan admin sekunder:"
            }
            if data in prompts:
                system.admin_states[user_id] = data
                text = prompts[data]
                keyboard = [[InlineKeyboardButton("« Batal", callback_data="nav_admin")]]
            else:
                text = "⚙️ Fitur ini masih di tahap pengembangan."
                keyboard = [[InlineKeyboardButton("« Kembali", callback_data="nav_admin")]]

    elif data.startswith("show_cat_"):
        c_key = data.split("_")[2]
        cat = system.catalog_db.get(c_key)
        if not cat:
            await query.answer("❌ Data katalog tidak ditemukan!", show_alert=True)
            return
            
        link = cat['link']
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🎬 Tonton Sekarang", url=link)]])
        
        await query.message.delete()
        await context.bot.send_photo(
            chat_id=user_id,
            photo=cat['photo_id'],
            caption=cat['caption'],
            reply_markup=markup,
            parse_mode=constants.ParseMode.HTML
        )
        return
        
    elif data == "nav_start":
        text = f"<b>✨ Xiao Reels Bot v{VERSION} ✨</b>\n\nHalo! Selamat Bergabung di Short Drama Team DL.\nSilakan pilih menu:"
        keyboard = [
            [InlineKeyboardButton("💎 Status VIP", callback_data="nav_vip_status"), InlineKeyboardButton("💰 Beli VIP", callback_data="nav_vip_buy")],
            [InlineKeyboardButton("🎬 Home", callback_data="nav_home"), InlineKeyboardButton("📊 Stats", callback_data="nav_stats")],
            [InlineKeyboardButton("📜 History", callback_data="nav_history"), InlineKeyboardButton("🔍 Cari Video", callback_data="nav_search")]
        ]
        if user_id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="nav_admin")])
    elif data == "nav_vip_status":
        from datetime import datetime
        import time
        vip_data = system.vip_db.get(str(user_id))
        now = time.time()
        
        if vip_data and vip_data.get('until', 0) > now:
            remaining = int((vip_data['until'] - now) / 86400)
            vtype = vip_data.get('type', 'REGULAR')
            
            if vtype == 'LIMITED':
                akses_text = f"🎯 Kuota Video Tersisa: <b>{vip_data.get('views_left', 0)}x lihat</b>\n\n<i>Anda bisa meng-upgrade ke VIP Regular jika kuota ini habis.</i>"
            else:
                akses_text = "Anda memiliki akses FULL UNLIMITED ke semua video VIP!"
                
            text = (f"👤 <b>STATUS MEMBERSHIP ANDA</b>\n\n"
                    f"🆔 User ID: <code>{user_id}</code>\n"
                    f"💎 Status VIP: <b>AKTIF</b> ✅\n"
                    f"📅 Tipe: <b>{vtype}</b>\n"
                    f"⏳ Sisa waktu: <b>~{remaining} hari</b>\n\n"
                    f"{akses_text}")
        else:
            text = (f"👤 <b>STATUS MEMBERSHIP ANDA</b>\n\n"
                    f"🆔 User ID: <code>{user_id}</code>\n"
                    f"❌ Status VIP: TIDAK AKTIF\n"
                    f"💎 Tipe: Free User\n\n"
                    f"💡 Ingin jadi VIP? Klik tombol di bawah untuk membeli akses VIP.")
            
        keyboard = [[InlineKeyboardButton("💰 Beli VIP / Topup Kuota", callback_data="nav_vip_buy")], [InlineKeyboardButton("« Kembali", callback_data="nav_start")]]
    elif data == "nav_search":
        text = "💡 <b>CARA PENCARIAN VIDEO</b>\n\nUntuk mencari Drama/Film, silakan gunakan perintah <code>/cari</code> diikuti dengan Judul yang ingin Anda cari.\n\nContoh:\n<code>/cari The Heir</code>\n<code>/cari Pengantin</code>"
        keyboard = [[InlineKeyboardButton("« Kembali", callback_data="nav_start")]]
    elif data == "nav_vip_buy":
        text = (f"💎 <b>PILIH JENIS VIP</b>\n\n"
                f"🔰 <b>VIP Limited</b> - <i>Untuk mencoba</i>\n"
                f"• Akses VIP dibatasi jumlah video (x lihat)\n"
                f"• 1 Hari: Rp 1.000 (2x lihat)\n"
                f"• 3 Hari: Rp 3.000 (6x lihat)\n\n"
                f"💎 <b>VIP Regular</b> - <i>Full Akses</i>\n"
                f"• Harga: Rp 1.000/hari\n"
                f"• Durasi: 7-30 hari (bisa diperpanjang)\n"
                f"• Akses tanpa batas")
        
        keyboard = [
            [InlineKeyboardButton("🔰 1 Hari Limited (Rp 1.000)", callback_data="buy_req_L_1_1000")],
            [InlineKeyboardButton("🔰 3 Hari Limited (Rp 3.000)", callback_data="buy_req_L_3_3000")],
            [InlineKeyboardButton("💎 7 Hari Regular (Rp 7.000)", callback_data="buy_req_R_7_7000")],
            [InlineKeyboardButton("💎 14 Hari Regular (Rp 14.000)", callback_data="buy_req_R_14_14000")],
            [InlineKeyboardButton("💎 30 Hari Regular (Rp 30.000)", callback_data="buy_req_R_30_30000")],
            [InlineKeyboardButton("« Kembali", callback_data="nav_start")]
        ]
    elif data.startswith("buy_req_"):
        # Process Saweria Payment Creation via API
        _, _, vtype, days, base_price = data.split("_")
        
        from bot.saweria_api import saweria_client
        import time

        try:
            await query.message.delete()
        except: pass
        
        msg = await context.bot.send_message(chat_id=user_id, text="⏳ <i>Memproses Server Pembayaran...</i>", parse_mode="HTML")
        try:
            username = system.settings_db.get("saweria_link", "TeamDL")
            if "saweria.co" in username:
                # Extract username from URL (e.g. https://saweria.co/TeamDL -> TeamDL)
                parts = username.strip("/").split("/")
                username = parts[-1] 
                
            saweria_user_id = await saweria_client.get_user_id(username)
            if not saweria_user_id:
                raise Exception(f"Username {username} tidak ditemukan.")
                
            vtype_name = "Limited" if vtype == "L" else "Regular"
                
            qr_string, tx_id, qr_image_stream, amount_raw = await saweria_client.create_payment(
                user_id=saweria_user_id,
                amount=int(base_price),
                name=f"USER {user_id}",
                email="buyer@xiaoreels.com",
                message=f"Beli VIP {vtype_name} {days} Hari",
            )
            
            # Track pending
            system.tx_db["pending"][tx_id] = {
                "user_id": user_id,
                "days": int(days),
                "vtype": vtype,
                "amount": amount_raw,
                "timestamp": time.time(),
                "status": "waiting"
            }
            system.save_all()
            
            await msg.delete()
            
            ksaweria = f"https://saweria.co/{username}"
            text = (f"💰 <b>MENUNGGU PEMBAYARAN</b>\n\n"
                    f"Paket: <b>VIP {vtype_name} {days} Hari</b>\n"
                    f"Nominal: <code>{amount_raw}</code>\n"
                    f"Trans_ID: <code>{tx_id}</code>\n\n"
                    f"⚠️ <b>PENTING:</b> Scan Barcode QRIS di atas dan Pastikan pembayaran Anda TEPAT sesuai angka tersebut.\n\n"
                    f"<i>Sistem secara otomatis mengecek status live... Anda akan menerima notifikasi VIP instan setelah membayar.</i>")
                    
            keyboard = [
                [InlineKeyboardButton("💳 Buka Saweria Public", url=ksaweria)],
                [InlineKeyboardButton("🔄 Pengecekan Berjalan", callback_data="no_action")],
                [InlineKeyboardButton("« Batalkan", callback_data="nav_vip_buy")]
            ]
            
            photo_msg = await context.bot.send_photo(chat_id=user_id, photo=qr_image_stream, caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            
            # Save message ID so we can edit the message on success
            system.tx_db["pending"][tx_id]["message_id"] = photo_msg.message_id
            system.save_all()
            
        except Exception as e:
            await msg.edit_text(f"❌ <b>Gagal Menyambung ke Server Pembayaran</b>\n\n{e}\n\nMohon laporkan masalah ini ke Admin.", parse_mode="HTML")
        
        return
    else:
        text = "⚙️ Menu sedang dikembangkan..."
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="nav_start")]]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)
