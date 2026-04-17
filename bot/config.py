import os
from dotenv import load_dotenv

load_dotenv()

# Bot Info
VERSION = "2.2.0"
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", 0))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN tidak ditemukan di file .env!")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAMA_DB = os.path.join(BASE_DIR, "drama_db.json")
HISTORY_DB = os.path.join(BASE_DIR, "history.json")
STATS_DB = os.path.join(BASE_DIR, "drama_stats.json")
USERS_DB = os.path.join(BASE_DIR, "all_users.json")
SETTINGS_DB = os.path.join(BASE_DIR, "settings.json")
VIDEO_DB = os.path.join(BASE_DIR, "video_db.json")
VIP_DB = os.path.join(BASE_DIR, "vip_db.json")
TX_DB = os.path.join(BASE_DIR, "transactions.json")
CATALOG_DB = os.path.join(BASE_DIR, "catalog_db.json")
LOG_FILE = os.path.join(BASE_DIR, "bot.log")

# Constraints
DEFAULT_COOLDOWN = 3  # seconds
NAV_LOCK_TIME = 15    # seconds (lock on double click)
SPAM_WAIT_TIME = 30   # seconds
MAX_RETRIES = 3
BACKOFF_FACTOR = 2
