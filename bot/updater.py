"""
updater.py - Sistem /update untuk Xiao Reels Bot
Melakukan git pull origin main dan restart bot secara otomatis.
"""
import logging
import asyncio
import subprocess
import sys
import os
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger("XiaoBot.Updater")


async def update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command /update:
    - Jalankan git pull origin main
    - Tampilkan hasil output ke chat
    - Restart bot otomatis jika ada perubahan
    """
    from .config import ADMIN_ID
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Hanya admin yang bisa menjalankan /update.")
        return

    msg = await update.message.reply_text("🔄 <b>Mengecek pembaruan dari GitHub...</b>", parse_mode="HTML")

    try:
        # Tentukan direktori root proyek (2 level di atas bot/updater.py)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Jalankan git pull
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        output = stdout or stderr or "(tidak ada output)"

        if result.returncode != 0:
            await msg.edit_text(
                f"❌ <b>Git Pull Gagal!</b>\n\n<pre>{output}</pre>",
                parse_mode="HTML"
            )
            return

        # Cek apakah ada perubahan
        if "Already up to date" in stdout or "Already up-to-date" in stdout:
            await msg.edit_text(
                f"✅ <b>Bot sudah versi terbaru!</b>\n\n<pre>{output}</pre>",
                parse_mode="HTML"
            )
            return

        # Ada perubahan - beritahu lalu restart
        await msg.edit_text(
            f"✅ <b>Pembaruan Berhasil!</b>\n\n<pre>{output}</pre>\n\n"
            f"♻️ <b>Bot akan restart dalam 3 detik...</b>",
            parse_mode="HTML"
        )

        await asyncio.sleep(3)

        logger.info("=== RESTART DIPANGGIL OLEH /update ===")

        # Restart dengan menjalankan ulang proses Python
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except subprocess.TimeoutExpired:
        await msg.edit_text("⏱ <b>Timeout!</b> Git pull memakan waktu terlalu lama.", parse_mode="HTML")
    except FileNotFoundError:
        await msg.edit_text(
            "❌ <b>Git tidak ditemukan!</b>\n\n"
            "Pastikan git sudah terinstall di server dan ada di PATH.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Update error: {e}")
        await msg.edit_text(f"❌ <b>Error:</b> <code>{e}</code>", parse_mode="HTML")
