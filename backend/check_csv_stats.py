"""
Script para verificar estatísticas dos dados CSV processados
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Conexão com banco
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db')
engine = create_engine(DATABASE_URL)

print("=" * 80)
print("📊 ESTATÍSTICAS DOS DADOS CSV PROCESSADOS")
print("=" * 80)

with engine.connect() as conn:
    # 1. Períodos criados
    print("\n📅 PERÍODOS CRIADOS:")
    result = conn.execute(text("""
        SELECT id, period_name, year, month, is_active, created_at
        FROM payroll_periods
        ORDER BY year DESC, month DESC
    """))
    periods = result.fetchall()
    for p in periods:
        print(f"  - ID {p[0]}: {p[1]} (Ano: {p[2]}, Mês: {p[3]}, Ativo: {p[4]})")
    
    # 2. Total de registros por período
    print("\n📋 REGISTROS POR PERÍODO:")
    result = conn.execute(text("""
        SELECT pp.period_name, COUNT(pd.id) as total
        FROM payroll_periods pp
        LEFT JOIN payroll_data pd ON pd.period_id = pp.id
        GROUP BY pp.id, pp.period_name
        ORDER BY pp.year DESC, pp.month DESC
    """))
    for row in result:
        print(f"  - {row[0]}: {row[1]} registros")
    
    # 3. Estatísticas gerais
    print("\n💰 ESTATÍSTICAS FINANCEIRAS:")
    result = conn.execute(text("""
        SELECT 
            period_id,
            COUNT(*) as total_employees,
            SUM((earnings_data->>'SALARIO_BASE')::numeric) as total_salario_base,
            SUM((deductions_data->>'INSS')::numeric) as total_inss,
            SUM((deductions_data->>'IRRF')::numeric) as total_irrf,
            SUM((deductions_data->>'FGTS')::numeric) as total_fgts
        FROM payroll_data
        WHERE earnings_data IS NOT NULL
        GROUP BY period_id
        ORDER BY period_id DESC
    """))
    stats = result.fetchall()
    
    for stat in stats:
        period_result = conn.execute(text("SELECT period_name FROM payroll_periods WHERE id = :id"), {"id": stat[0]})
        period_name = period_result.fetchone()[0]
        print(f"\n  📊 {period_name}:")
        print(f"     👥 Funcionários: {stat[1]}")
        print(f"     💵 Total Salário Base: R$ {stat[2]:,.2f}" if stat[2] else "     💵 Total Salário Base: N/A")
        print(f"     📉 Total INSS: R$ {stat[3]:,.2f}" if stat[3] else "     📉 Total INSS: N/A")
        print(f"     📉 Total IRRF: R$ {stat[4]:,.2f}" if stat[4] else "     📉 Total IRRF: N/A")
        print(f"     📉 Total FGTS: R$ {stat[5]:,.2f}" if stat[5] else "     📉 Total FGTS: N/A")
    
    # 4. Amostra de dados JSONB
    print("\n🔍 AMOSTRA DE DADOS (primeiro registro):")
    result = conn.execute(text("""
        SELECT 
            e.name,
            e.unique_id,
            pd.earnings_data,
            pd.deductions_data
        FROM payroll_data pd
        JOIN employees e ON e.id = pd.employee_id
        LIMIT 1
    """))
    sample = result.fetchone()
    if sample:
        print(f"\n  👤 Funcionário: {sample[0]} ({sample[1]})")
        print(f"\n  💰 Proventos (earnings_data):")
        if sample[2]:
            for key, value in sample[2].items():
                print(f"     - {key}: {value}")
        print(f"\n  📉 Descontos (deductions_data):")
        if sample[3]:
            for key, value in sample[3].items():
                print(f"     - {key}: {value}")

print("\n" + "=" * 80)
print("✅ Análise concluída!")
print("=" * 80)
