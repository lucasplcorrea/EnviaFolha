"""
Debug script to check actual payroll data in PostgreSQL
"""
import os
import sys
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment variables
def load_env_file():
    env_vars = {}
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars

env_vars = load_env_file()
for key, value in env_vars.items():
    os.environ[key] = value

# Database connection
database_url = os.getenv('DATABASE_URL')
if not database_url:
    db_user = os.getenv('DB_USER', 'enviafolha_user')
    db_password = os.getenv('DB_PASSWORD', 'secure_password')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'enviafolha_db')
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

engine = create_engine(database_url)
Session = sessionmaker(bind=engine)

def analyze_payroll_data():
    """Analyze payroll data in detail"""
    session = Session()
    try:
        # Get Julho 2024 data
        result = session.execute(text("""
            SELECT 
                pd.id,
                e.name as employee_name,
                e.unique_id,
                pd.earnings_data::text,
                pd.deductions_data::text,
                pd.benefits_data::text,
                pd.additional_data::text
            FROM payroll_data pd
            JOIN payroll_periods pp ON pd.period_id = pp.id
            JOIN employees e ON pd.employee_id = e.id
            WHERE pp.period_name = 'Julho 2024'
            LIMIT 3
        """))
        
        rows = result.fetchall()
        print("\n" + "="*80)
        print("🔍 ANÁLISE DETALHADA - JULHO 2024 (3 primeiros registros)")
        print("="*80)
        
        for idx, row in enumerate(rows, 1):
            print(f"\n{'─'*80}")
            print(f"📋 REGISTRO {idx}: {row[1]} (ID: {row[2]})")
            print(f"{'─'*80}")
            
            print("\n💰 EARNINGS DATA:")
            earnings = json.loads(row[3]) if row[3] else {}
            if earnings:
                print(json.dumps(earnings, indent=2, ensure_ascii=False))
            else:
                print("  ⚠️  VAZIO")
            
            print("\n📉 DEDUCTIONS DATA:")
            deductions = json.loads(row[4]) if row[4] else {}
            if deductions:
                print(json.dumps(deductions, indent=2, ensure_ascii=False))
            else:
                print("  ⚠️  VAZIO")
            
            print("\n🏥 BENEFITS DATA:")
            benefits = json.loads(row[5]) if row[5] else {}
            if benefits:
                print(json.dumps(benefits, indent=2, ensure_ascii=False))
            else:
                print("  ⚠️  VAZIO")
            
            print("\n📊 ADDITIONAL DATA:")
            additional = json.loads(row[6]) if row[6] else {}
            if additional:
                print(json.dumps(additional, indent=2, ensure_ascii=False))
            else:
                print("  ⚠️  VAZIO")
        
        # Statistics summary
        result = session.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN earnings_data::text != '{}' THEN 1 END) as with_earnings,
                COUNT(CASE WHEN deductions_data::text != '{}' THEN 1 END) as with_deductions,
                COUNT(CASE WHEN benefits_data::text != '{}' THEN 1 END) as with_benefits,
                COUNT(CASE WHEN additional_data::text != '{}' THEN 1 END) as with_additional
            FROM payroll_data pd
            JOIN payroll_periods pp ON pd.period_id = pp.id
            WHERE pp.period_name = 'Julho 2024'
        """))
        
        row = result.fetchone()
        print(f"\n{'='*80}")
        print("📊 ESTATÍSTICAS DE POPULAÇÃO - JULHO 2024")
        print(f"{'='*80}")
        print(f"Total de registros: {row[0]}")
        print(f"Com earnings_data:   {row[1]:3d} ({row[1]/row[0]*100:5.1f}%)")
        print(f"Com deductions_data: {row[2]:3d} ({row[2]/row[0]*100:5.1f}%)")
        print(f"Com benefits_data:   {row[3]:3d} ({row[3]/row[0]*100:5.1f}%)")
        print(f"Com additional_data: {row[4]:3d} ({row[4]/row[0]*100:5.1f}%)")
        print("="*80)
        
        # Test aggregation query
        print("\n🔢 TESTE DE AGREGAÇÃO:")
        print("="*80)
        result = session.execute(text("""
            SELECT 
                COUNT(DISTINCT pd.employee_id) as num_employees,
                COALESCE(SUM((pd.additional_data->>'TOTAL_PROVENTOS')::numeric), 0) as total_proventos,
                COALESCE(SUM((pd.additional_data->>'TOTAL_DESCONTOS')::numeric), 0) as total_descontos,
                COALESCE(SUM((pd.additional_data->>'LIQUIDO_CALCULO')::numeric), 0) as total_liquido,
                COALESCE(SUM((pd.deductions_data->>'INSS')::numeric), 0) as total_inss,
                COALESCE(SUM((pd.deductions_data->>'IRRF')::numeric), 0) as total_irrf,
                COALESCE(SUM((pd.deductions_data->>'FGTS')::numeric), 0) as total_fgts
            FROM payroll_data pd
            JOIN payroll_periods pp ON pd.period_id = pp.id
            WHERE pp.period_name = 'Julho 2024'
        """))
        
        row = result.fetchone()
        print(f"Funcionários: {row[0]}")
        print(f"Total Proventos: R$ {row[1]:,.2f}")
        print(f"Total Descontos: R$ {row[2]:,.2f}")
        print(f"Total Líquido:   R$ {row[3]:,.2f}")
        print(f"Total INSS:      R$ {row[4]:,.2f}")
        print(f"Total IRRF:      R$ {row[5]:,.2f}")
        print(f"Total FGTS:      R$ {row[6]:,.2f}")
        print("="*80)
        
    finally:
        session.close()

if __name__ == "__main__":
    analyze_payroll_data()
