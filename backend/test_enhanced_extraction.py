"""
Test script to verify enhanced data extraction from CSV files
"""
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

# Database connection
DATABASE_URL = "sqlite:///./enviafolha.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def check_payroll_data():
    """Check what data is currently in payroll_data table"""
    session = Session()
    try:
        # Get a sample record
        result = session.execute(text("""
            SELECT 
                pd.id,
                pp.period_name,
                e.name as employee_name,
                pd.earnings_data,
                pd.deductions_data,
                pd.benefits_data,
                pd.additional_data
            FROM payroll_data pd
            JOIN payroll_periods pp ON pd.period_id = pp.id
            JOIN employees e ON pd.employee_id = e.id
            LIMIT 1
        """))
        
        row = result.fetchone()
        if row:
            print("\n=== SAMPLE PAYROLL RECORD ===")
            print(f"Period: {row[1]}")
            print(f"Employee: {row[2]}")
            print(f"\nEarnings Data:")
            print(json.dumps(json.loads(row[3]) if row[3] else {}, indent=2, ensure_ascii=False))
            print(f"\nDeductions Data:")
            print(json.dumps(json.loads(row[4]) if row[4] else {}, indent=2, ensure_ascii=False))
            print(f"\nBenefits Data:")
            print(json.dumps(json.loads(row[5]) if row[5] else {}, indent=2, ensure_ascii=False))
            print(f"\nAdditional Data:")
            print(json.dumps(json.loads(row[6]) if row[6] else {}, indent=2, ensure_ascii=False))
        else:
            print("No payroll data found")
            
        # Count records by field population
        result = session.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN earnings_data != '{}' AND earnings_data IS NOT NULL THEN 1 END) as with_earnings,
                COUNT(CASE WHEN benefits_data != '{}' AND benefits_data IS NOT NULL THEN 1 END) as with_benefits,
                COUNT(CASE WHEN additional_data != '{}' AND additional_data IS NOT NULL THEN 1 END) as with_additional
            FROM payroll_data
        """))
        
        row = result.fetchone()
        print("\n=== DATA POPULATION STATISTICS ===")
        print(f"Total records: {row[0]}")
        print(f"Records with earnings data: {row[1]} ({row[1]/row[0]*100:.1f}%)")
        print(f"Records with benefits data: {row[2]} ({row[2]/row[0]*100:.1f}%)")
        print(f"Records with additional data: {row[3]} ({row[3]/row[0]*100:.1f}%)")
        
    finally:
        session.close()

if __name__ == "__main__":
    check_payroll_data()
