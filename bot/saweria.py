import asyncio
import logging
import time
from telegram.ext import ContextTypes
from bot.system import system
from bot.saweria_api import saweria_client

logger = logging.getLogger("SaweriaChecker")

async def check_saweria_payments(context: ContextTypes.DEFAULT_TYPE):
    pending_tx = system.tx_db.get("pending", {})
    if not pending_tx:
        return

    processed_tx = system.tx_db.setdefault("processed", [])
    keys_to_process = []
    
    # Check all pending transactions
    for tx_id, tx_data in list(pending_tx.items()):
        try:
            is_paid = await saweria_client.check_paid_status(tx_id)
            if is_paid:
                keys_to_process.append((tx_id, tx_data))
        except Exception as e:
            logger.debug(f"Error checking tx {tx_id}: {e}")

    for tx_id, tx in keys_to_process:
        user_id = tx["user_id"]
        days = tx["days"]
        vtype = tx.get("vtype", "R")
        amount = tx.get("amount", "?")
        
        # Activate VIP
        now = time.time()
        user_vip = system.vip_db.get(str(user_id), {})
        current_until = user_vip.get('until', 0)
        if current_until < now:
            current_until = now
            
        new_until = current_until + (days * 86400)
        
        if vtype == "L":
            views = 2 if days == 1 else 6
            # Jika user sebelumnya sudah VIP Limited, tambahkan kuotanya
            current_views = user_vip.get('views_left', 0) if user_vip.get('type') == 'LIMITED' else 0
            system.vip_db[str(user_id)] = {'until': new_until, 'type': 'LIMITED', 'views_left': current_views + views}
            vtype_name = "Limited"
        else:
            system.vip_db[str(user_id)] = {'until': new_until, 'type': 'REGULAR'}
            vtype_name = "Regular"
        
        # Mark processed
        processed_tx.append(tx_id)
        if tx_id in pending_tx:
            del pending_tx[tx_id]
        
        system.save_all()
        
        # Send Notification (Delete QR Message completely)
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        msg_text = f"✅ <b>PEMBAYARAN DITERIMA!</b>\n\nNominal: Rp {amount}\nTerima kasih atas orderan Anda 🙌\n\nVIP {vtype_name} selama {days} Hari telah AKTIF!"
        keyboard = [[InlineKeyboardButton("🔍 Cek Status VIP", callback_data="nav_vip_status")]]
        
        try:
            msg_id = tx.get("message_id")
            if msg_id:
                try:
                    await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
                except Exception as del_err:
                    logger.debug(f"Could not delete QR message: {del_err}")
                
            await context.bot.send_message(
                chat_id=user_id, 
                text=msg_text, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send VIP notification to {user_id}: {e}")
