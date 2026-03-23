import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.employee import Employee
from datetime import date

DATABASE_URL = "postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def main():
    db = SessionLocal()
    
    # Check what type admission_date and termination_date are 
    emp = db.query(Employee).filter(Employee.termination_date.isnot(None)).first()
    if emp:
        print(f"Sample Employee {emp.id}:")
        print(f"admission: {emp.admission_date} (Type: {type(emp.admission_date)})")
        print(f"termination: {emp.termination_date} (Type: {type(emp.termination_date)})")
    else:
        print("No terminated employees found.")
        
    print("-" * 50)
    
    # Run a test query for 2025-12
    period_start = date(2025, 12, 1)
    period_end = date(2026, 1, 1)
    
    terminations_query = db.query(Employee.admission_date, Employee.termination_date).filter(
        Employee.termination_date >= period_start,
        Employee.termination_date < period_end
    )
    results = terminations_query.all()
    print(f"Terminations in Dec 2025: {len(results)}")
    
    total_days = 0
    valid_count = 0
    for adm, term in results:
        print(f"  adm: {adm}, term: {term}")
        if adm and term:
            try:
                days = (term - adm).days
                print(f"    days: {days}")
                total_days += days
                valid_count += 1
            except Exception as e:
                print(f"    Error calculating days: {e}")
                
    if valid_count > 0:
        print(f"Avg tenure months: {(total_days / valid_count) / 30.416}")
    else:
        print("Valid count is 0")

    db.close()

if __name__ == "__main__":
    main()
