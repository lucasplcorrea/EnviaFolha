from sqlalchemy import create_engine, text
import json

engine = create_engine('postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db')
conn = engine.connect()

# Investigar o caso específico da KEITY em Novembro
print('\n' + '='*150)
print('INVESTIGAÇÃO: KEITY TAIHANNE ALVES SANTOS - Novembro 2025')
print('='*150)

result = conn.execute(text("""
    SELECT 
        e.name,
        e.unique_id,
        pp.period_name,
        pd.additional_data,
        pd.earnings_data,
        pd.deductions_data
    FROM payroll_data pd
    JOIN employees e ON e.id = pd.employee_id
    JOIN payroll_periods pp ON pd.period_id = pp.id
    WHERE 
        e.name LIKE '%KEITY%'
        AND pp.month = 11
        AND pp.year = 2025
    LIMIT 1
"""))

for row in result:
    print(f"\nNome: {row[0]}")
    print(f"Matrícula: {row[1]}")
    print(f"Período: {row[2]}")
    
    print("\n--- ADDITIONAL DATA ---")
    additional = row[3] or {}
    print(f"Valor Salário: R$ {additional.get('Valor Salário', 0)}")
    print(f"Salário Mensal: R$ {additional.get('Salário Mensal', 0)}")
    print(f"Total de Proventos: R$ {additional.get('Total de Proventos', 0)}")
    print(f"Total de Descontos: R$ {additional.get('Total de Descontos', 0)}")
    print(f"Líquido de Cálculo: R$ {additional.get('Líquido de Cálculo', 0)}")
    print(f"Status: {additional.get('Status', 'N/A')}")
    print(f"Horas Normais Diurnas: {additional.get('Horas Normais Diurnas', 0)}")
    print(f"Horas Faltas Diurnas: {additional.get('Horas Faltas Diurnas', 0)}")
    
    print("\n--- EARNINGS DATA (Proventos) ---")
    earnings = row[4] or {}
    for key in sorted(earnings.keys()):
        value = earnings[key]
        if value and float(value) > 0:
            print(f"  {key}: R$ {float(value):,.2f}")
    
    print("\n--- DEDUCTIONS DATA (Descontos) ---")
    deductions = row[5] or {}
    for key in sorted(deductions.keys()):
        value = deductions[key]
        if value and float(value) > 0:
            print(f"  {key}: R$ {float(value):,.2f}")

# Agora verificar as colunas de férias no CSV de julho
print('\n' + '='*150)
print('VERIFICAÇÃO: Colunas de Férias no CSV de Julho 2025')
print('='*150)

result2 = conn.execute(text("""
    SELECT 
        e.name,
        pp.period_name,
        pd.additional_data->>'1/3 Sobre Férias' as abono_1_3,
        pd.additional_data->>'Horas Férias Diurnas' as horas_ferias,
        pd.earnings_data->>'FERIAS_VALOR_BASE' as ferias_valor_base_earnings,
        pd.earnings_data->>'FERIAS_ABONO_1_3' as ferias_abono_earnings
    FROM payroll_data pd
    JOIN employees e ON e.id = pd.employee_id
    JOIN payroll_periods pp ON pd.period_id = pp.id
    WHERE 
        pp.month = 7
        AND pp.year = 2025
        AND (
            (pd.additional_data->>'1/3 Sobre Férias')::numeric > 0
            OR (pd.additional_data->>'Horas Férias Diurnas')::numeric > 0
        )
    LIMIT 5
"""))

print(f"\n{'Nome':40} | {'Período':20} | {'1/3 Abono (add)':>15} | {'Horas Férias':>15} | {'Férias Base (earn)':>20} | {'Abono (earn)':>20}")
print('-'*150)

count = 0
for row in result2:
    nome = row[0][:38] if row[0] else 'N/A'
    periodo = row[1][:18] if row[1] else 'N/A'
    abono_add = float(row[2]) if row[2] else 0
    horas = float(row[3]) if row[3] else 0
    ferias_base_earn = row[4] if row[4] else 'NULL'
    abono_earn = row[5] if row[5] else 'NULL'
    
    print(f"{nome:40} | {periodo:20} | R$ {abono_add:>11,.2f} | {horas:>15.2f} | {ferias_base_earn:>20} | {abono_earn:>20}")
    count += 1

if count == 0:
    print("Nenhum registro encontrado com valores de férias em additional_data")

print('='*150)

conn.close()
