import sys
sys.path.insert(0, r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\backend')

from app.core.database import get_db
from sqlalchemy import text

db = next(get_db())
result = db.execute(text("SELECT id, period_name FROM periods WHERE period_name LIKE '%Julho%' OR period_name LIKE '%07%' ORDER BY id DESC"))
for r in result:
    print(f"ID {r[0]}: {r[1]}")
