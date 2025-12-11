import sys
import os
sys.path.append(os.getcwd())
from backend.database import db

if not db.conn:
    db.connect()

cursor = db.conn.cursor()
cursor.execute("SELECT symbol, timeframe, COUNT(*) FROM candles GROUP BY symbol, timeframe")
rows = cursor.fetchall()
for r in rows:
    print(r)
