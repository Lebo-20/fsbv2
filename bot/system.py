import json
import os
import time
import asyncio
import logging
from typing import Dict, Any, List
from .config import DRAMA_DB, HISTORY_DB, STATS_DB, USERS_DB, SETTINGS_DB, VIDEO_DB, VIP_DB, TX_DB, CATALOG_DB, DEFAULT_COOLDOWN, SPAM_WAIT_TIME

logger = logging.getLogger("XiaoBot.System")

class XiaoSystem:
    def __init__(self):
        self.user_locks: Dict[int, asyncio.Lock] = {}
        self.nav_locks: Dict[str, float] = {}  # key: f"{user_id}_{drama_key}_{part}"
        self.anti_spam: Dict[int, float] = {}
        self.admin_states: Dict[int, str] = {} # Tracks state for admin inputs
        
        # Initialize databases
        self.drama_db = self._load_json(DRAMA_DB, {})
        self.history_db = self._load_json(HISTORY_DB, {})
        self.stats_db = self._load_json(STATS_DB, {"total_views": 0, "drama_views": {}})
        self.users_db = self._load_json(USERS_DB, {"users": [], "banned": []})
        self.settings_db = self._load_json(SETTINGS_DB, {
            "fsub_channels": [],
            "saweria_link": "",
            "start_message": "Selamat datang di Xiao Reels Bot!",
            "premium_price": "50.000",
            "mission_active": False
        })
        self.video_db = self._load_json(VIDEO_DB, {})
        self.vip_db = self._load_json(VIP_DB, {})
        self.tx_db = self._load_json(TX_DB, {"pending": {}, "processed": []})
        self.catalog_db = self._load_json(CATALOG_DB, {})

    def _load_json(self, path: str, default: Any) -> Any:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading {path}: {e}")
        return default

    def save_all(self):
        self._save_json(DRAMA_DB, self.drama_db)
        self._save_json(HISTORY_DB, self.history_db)
        self._save_json(STATS_DB, self.stats_db)
        self._save_json(USERS_DB, self.users_db)

        self._save_json(SETTINGS_DB, self.settings_db)
        self._save_json(VIDEO_DB, self.video_db)
        self._save_json(VIP_DB, self.vip_db)
        self._save_json(TX_DB, self.tx_db)
        self._save_json(CATALOG_DB, self.catalog_db)
    def _save_json(self, path: str, data: Any):
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving {path}: {e}")

    def get_lock(self, user_id: int) -> asyncio.Lock:
        if user_id not in self.user_locks:
            self.user_locks[user_id] = asyncio.Lock()
        return self.user_locks[user_id]

    def check_spam(self, user_id: int) -> tuple[bool, int]:
        """Returns (Allowed, WaitTime)"""
        now = time.time()
        last_time = self.anti_spam.get(user_id, 0)
        diff = now - last_time
        
        if diff < DEFAULT_COOLDOWN:
            return False, int(SPAM_WAIT_TIME - diff)
        
        self.anti_spam[user_id] = now
        return True, 0

    def is_nav_locked(self, user_id: int, drama_key: str, part: int) -> bool:
        lock_key = f"{user_id}_{drama_key}_{part}"
        now = time.time()
        if lock_key in self.nav_locks:
            if now - self.nav_locks[lock_key] < 15: # NAV_LOCK_TIME
                return True
        self.nav_locks[lock_key] = now
        return False

system = XiaoSystem()
