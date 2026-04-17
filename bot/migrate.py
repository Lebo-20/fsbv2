import sqlite3
import json
import os

db_path = 'D:\\fshub v2\\bot_database.db'

# 1. Connect ke Database
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 2. Migrasi Users
cur.execute("SELECT user_id FROM users")
users = [row[0] for row in cur.fetchall()]

with open('D:\\fshub v2\\all_users.json', 'w') as f:
    json.dump({"users": users, "banned": []}, f, indent=4)

# 3. Migrasi Videos
cur.execute("SELECT code, backup_message_id, file_id FROM videos")
videos = cur.fetchall()

video_db = {}
for code, msg_id, file_id in videos:
    if msg_id:
        video_db[code] = msg_id
    else:
        video_db[code] = file_id # Pakai string (file_id) sebagai fallback

with open('D:\\fshub v2\\video_db.json', 'w') as f:
    json.dump(video_db, f, indent=4)

print(f"MANTAP! ✅ Berhasil migrasi {len(users)} User dan {len(videos)} Video ke format JSON baru.")
