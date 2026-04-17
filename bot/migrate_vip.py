import sqlite3
import json
import time
from datetime import datetime

with sqlite3.connect('D:\\fshub v2\\bot_database.db') as conn:
    cur = conn.cursor()
    cur.execute("SELECT user_id, vip_until, vip_limited_until, is_admin FROM users")
    
    vip_db = {}
    for user_id, req, lim, is_admin in cur.fetchall():
        v_until = 0
        v_type = 'REGULAR'
        if req:
            try:
                dt = datetime.fromisoformat(req).timestamp()
                if dt > time.time():
                    v_until = dt
            except: pass
            
        if lim and not v_until:
             try:
                dt = datetime.fromisoformat(lim).timestamp()
                if dt > time.time():
                    v_until = dt
                    v_type = 'LIMITED'
             except: pass
             
        if v_until:
            vip_db[str(user_id)] = {'until': v_until, 'type': v_type}
            
with open('D:\\fshub v2\\vip_db.json', 'w') as f:
    json.dump(vip_db, f, indent=4)
print(f"Migrated {len(vip_db)} active VIP users")
