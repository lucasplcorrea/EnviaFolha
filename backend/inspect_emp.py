import sys
import json
sys.path.append('.')
from app.database import SessionLocal
from app.models.employee import Employee
from sqlalchemy import inspect

db = SessionLocal()
mapper = inspect(Employee)

print("=== COLS ===")
for c in mapper.columns:
    print(f"{c.name}: {c.type}")

print("\n=== FIRST EMP ===")
emp = db.query(Employee).first()
if emp:
    d = {k: v for k, v in emp.__dict__.items() if not k.startswith('_')}
    for k, v in d.items():
        print(f"{k}: {v}")
else:
    print("No employees found.")
