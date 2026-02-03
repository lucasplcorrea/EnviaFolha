"""Script para verificar estrutura de tabelas de afastamentos e férias"""
import os
from dotenv import load_dotenv
load_dotenv('../.env')
from sqlalchemy import create_engine, text

engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    # Listar tabelas
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
    tables = [r[0] for r in result]
    print('=== TABELAS DO BANCO ===')
    for t in sorted(tables):
        print(f'  - {t}')
    
    # Verificar estrutura de leave_records
    print('\n=== ESTRUTURA leave_records ===')
    result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='leave_records' ORDER BY ordinal_position"))
    for r in result:
        print(f'  {r[0]}: {r[1]}')
    
    # Verificar dados em leave_records
    print('\n=== DADOS EM leave_records ===')
    result = conn.execute(text("SELECT * FROM leave_records LIMIT 5"))
    rows = list(result)
    if rows:
        for r in rows:
            print(f'  {r}')
    else:
        print('  Nenhum registro')
    
    # Verificar campos de férias/afastamento no Employee
    print('\n=== CAMPOS DE FERIAS/AFASTAMENTO EM employees ===')
    result = conn.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name='employees' 
        AND (column_name LIKE '%leave%' OR column_name LIKE '%vacation%' OR column_name LIKE '%ferias%' OR column_name LIKE '%afasta%')
        ORDER BY column_name
    """))
    rows = list(result)
    if rows:
        for r in rows:
            print(f'  {r[0]}: {r[1]}')
    else:
        print('  Nenhum campo relacionado encontrado')
    
    # Verificar colunas da tabela payroll_data
    print('\n=== COLUNAS payroll_data (amostra) ===')
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='payroll_data' ORDER BY ordinal_position LIMIT 30"))
    for r in result:
        print(f'  - {r[0]}')
    
    # Verificar se há dados de férias nos payroll_data
    print('\n=== VERIFICANDO COLUNAS COM FERIAS EM payroll_data ===')
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='payroll_data' 
        AND (column_name LIKE '%ferias%' OR column_name LIKE '%vacation%')
        ORDER BY column_name
    """))
    rows = list(result)
    if rows:
        for r in rows:
            print(f'  - {r[0]}')
    else:
        print('  Nenhuma coluna de férias encontrada')
