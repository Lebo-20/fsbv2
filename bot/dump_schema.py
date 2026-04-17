import sqlite3

conn = sqlite3.connect('D:\\fshub v2\\bot_database.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("TABLES:")
for table in tables:
    name = table[0]
    cursor.execute(f"PRAGMA table_info({name});")
    cols = cursor.fetchall()
    print(f"[{name}] Columns:")
    for col in cols:
        print("  -", col[1], col[2])
