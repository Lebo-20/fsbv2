import asyncio
import io
import json
import logging
import time
from typing import Optional, Tuple
import cloudscraper
import qrcode
from bs4 import BeautifulSoup
from bot.system import system

logger = logging.getLogger("SaweriaAPI")

class SaweriaScraper:
    BACKEND = "https://backend.saweria.co"
    FRONTEND = "https://saweria.co"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://saweria.co/",
    }

    def __init__(self):
        self.scraper = cloudscraper.create_scraper()

    async def get_user_id(self, username: str) -> Optional[str]:
        if not username or not isinstance(username, str):
            raise ValueError("Username harus berupa string dan tidak boleh kosong.")

        def _sync_get_backend():
            url = f"{self.BACKEND}/users/{username}"
            try:
                res = self.scraper.get(url, headers=self.HEADERS, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("data", {}).get("id")
            except Exception as e:
                logger.error(f"Error fetching user_id for {username}: {e}")
            return None

        return await asyncio.to_thread(_sync_get_backend)

    async def create_payment(
        self,
        user_id: str,
        amount: int,
        name: str,
        email: str,
        message: str,
    ) -> Tuple[str, str, io.BytesIO, int]:
        if amount < 1000:
            raise ValueError("Jumlah minimum donasi adalah 1000")

        payload = {
            "agree": True,
            "notUnderage": True,
            "message": message,
            "amount": amount,
            "payment_type": "qris",
            "vote": "",
            "currency": "IDR",
            "customer_info": {"first_name": name, "email": email, "phone": ""},
        }

        def _sync_post():
            res = self.scraper.post(
                f"{self.BACKEND}/donations/{user_id}",
                json=payload,
                headers=self.HEADERS,
            )
            if not res.ok:
                raise Exception(f"Gagal membuat pembayaran: {res.text}")
            return res.json()["data"]

        data = await asyncio.to_thread(_sync_post)
        qr_string = data["qr_string"]
        transaction_id = data["id"]
        amount_raw = data["amount_raw"]

        # Generate standard QR Code image via python qrcode
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        qr_image_stream = io.BytesIO()
        img.save(qr_image_stream, format="PNG")
        qr_image_stream.name = f"{transaction_id}.png"
        qr_image_stream.seek(0)

        return qr_string, transaction_id, qr_image_stream, amount_raw

    async def check_paid_status(self, transaction_id: str) -> bool:
        def _sync_get():
            res = self.scraper.get(f"{self.BACKEND}/donations/qris/{transaction_id}", headers=self.HEADERS)
            if not res.ok:
                raise Exception("Transaction ID not found")
            js = res.json()["data"]
            # Saweria clears qr_string or sets status to something if paid
            return js.get("qr_string", "") == ""

        return await asyncio.to_thread(_sync_get)

saweria_client = SaweriaScraper()
