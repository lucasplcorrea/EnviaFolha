import psycopg2
import os
import json
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/enviafolha')
conn = psycopg2.connect(db_url)
cursor = conn.cursor()

# Verificar total de registros
cursor.execute('SELECT COUNT(*) FROM payroll_data WHERE period_id = 1')
total = cursor.fetchone()[0]
print(f'📊 Total de registros em payroll_data (Janeiro 2024): {total}')

# Ver estrutura da tabela
print('\n📋 Estrutura da tabela payroll_data:')
cursor.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'payroll_data'
    ORDER BY ordinal_position
""")
for row in cursor.fetchall():
    print(f'  - {row[0]}: {row[1]}')

# Ver alguns registros
print('\n💰 Primeiros 3 registros de folha:')
cursor.execute("""
    SELECT pd.id, e.name, pd.gross_salary, pd.net_salary, 
           pd.earnings_data, pd.deductions_data
    FROM payroll_data pd
    JOIN employees e ON e.id = pd.employee_id
    WHERE pd.period_id = 1
    LIMIT 3
""")

for row in cursor.fetchall():
    print(f'\n  ID: {row[0]}')
    print(f'  Funcionário: {row[1]}')
    print(f'  Salário Bruto: R$ {row[2]:,.2f}' if row[2] else '  Salário Bruto: N/A')
    print(f'  Salário Líquido: R$ {row[3]:,.2f}' if row[3] else '  Salário Líquido: N/A')
    
    if row[4]:  # earnings_data
        print(f'  Proventos (primeiros 3):')
        earnings = row[4] if isinstance(row[4], dict) else {}
        for key, value in list(earnings.items())[:3]:
            print(f'    - {key}: R$ {value:,.2f}')
    
    if row[5]:  # deductions_data
        print(f'  Descontos (primeiros 3):')
        deductions = row[5] if isinstance(row[5], dict) else {}
        for key, value in list(deductions.items())[:3]:
            print(f'    - {key}: R$ {value:,.2f}')

# Ver período criado
print('\n📅 Período criado:')
cursor.execute('SELECT * FROM payroll_periods WHERE id = 1')
period = cursor.fetchone()
print(f'  ID: {period[0]}')
print(f'  Ano: {period[1]}')
print(f'  Mês: {period[2]}')
print(f'  Nome: {period[3]}')
print(f'  Ativo: {period[5]}')

cursor.close()
conn.close()
