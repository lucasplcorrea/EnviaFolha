"""Script para verificar dados de férias nos payroll_data"""
import os
import json
from dotenv import load_dotenv
load_dotenv('../.env')
from sqlalchemy import create_engine, text

engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    # Verificar estrutura do earnings_data
    print('=== VERIFICANDO earnings_data (amostra) ===')
    result = conn.execute(text("""
        SELECT pd.id, e.name, pd.earnings_data, pd.additional_data
        FROM payroll_data pd
        JOIN employees e ON pd.employee_id = e.id
        LIMIT 3
    """))
    for r in result:
        print(f'\n--- Registro {r[0]} - {r[1]} ---')
        if r[2]:
            data = r[2] if isinstance(r[2], dict) else json.loads(r[2]) if r[2] else {}
            print(f'  earnings_data keys: {list(data.keys())[:10]}...')
        if r[3]:
            data = r[3] if isinstance(r[3], dict) else json.loads(r[3]) if r[3] else {}
            print(f'  additional_data keys: {list(data.keys())[:10]}...')
    
    # Procurar por campos que contenham "ferias" ou "13" no earnings_data
    print('\n=== PROCURANDO CAMPOS DE FÉRIAS/13º ===')
    result = conn.execute(text("""
        SELECT DISTINCT jsonb_object_keys(earnings_data::jsonb) as key
        FROM payroll_data
        WHERE earnings_data IS NOT NULL
        ORDER BY key
    """))
    keys = [r[0] for r in result]
    print(f'Total de chaves em earnings_data: {len(keys)}')
    
    # Filtrar chaves relacionadas a férias/13º
    ferias_keys = [k for k in keys if 'ferias' in k.lower() or '13' in k.lower() or 'decimo' in k.lower()]
    print(f'\nChaves relacionadas a férias/13º:')
    for k in ferias_keys:
        print(f'  - {k}')
    
    # Verificar valores de férias para alguns funcionários
    print('\n=== AMOSTRA DE VALORES DE FÉRIAS ===')
    result = conn.execute(text("""
        SELECT e.name, 
               pd.earnings_data->>'ferias_gozo' as ferias_gozo,
               pd.earnings_data->>'ferias_pecuniaria' as ferias_pecuniaria,
               pd.earnings_data->>'ferias_1_3_constitucional' as ferias_1_3,
               pd.earnings_data->>'13_salario_1_parcela' as decimo_1,
               pd.earnings_data->>'13_salario_2_parcela' as decimo_2
        FROM payroll_data pd
        JOIN employees e ON pd.employee_id = e.id
        WHERE (pd.earnings_data->>'ferias_gozo' IS NOT NULL 
               AND pd.earnings_data->>'ferias_gozo' != '0' 
               AND pd.earnings_data->>'ferias_gozo' != '0.0')
           OR (pd.earnings_data->>'ferias_pecuniaria' IS NOT NULL 
               AND pd.earnings_data->>'ferias_pecuniaria' != '0'
               AND pd.earnings_data->>'ferias_pecuniaria' != '0.0')
        LIMIT 10
    """))
    rows = list(result)
    if rows:
        for r in rows:
            print(f'  {r[0]}: gozo={r[1]}, pecuniaria={r[2]}, 1/3={r[3]}, 13-1a={r[4]}, 13-2a={r[5]}')
    else:
        print('  Nenhum registro com férias encontrado')
    
    # Contar quantos funcionários têm férias registradas
    print('\n=== CONTAGEM DE FÉRIAS POR PERÍODO ===')
    result = conn.execute(text("""
        SELECT pp.year, pp.month, COUNT(*) as total_com_ferias
        FROM payroll_data pd
        JOIN payroll_periods pp ON pd.period_id = pp.id
        WHERE (pd.earnings_data->>'ferias_gozo' IS NOT NULL 
               AND pd.earnings_data->>'ferias_gozo' != '0' 
               AND pd.earnings_data->>'ferias_gozo' != '0.0')
        GROUP BY pp.year, pp.month
        ORDER BY pp.year, pp.month
    """))
    rows = list(result)
    if rows:
        for r in rows:
            print(f'  {r[0]}/{r[1]:02d}: {r[2]} funcionários com férias')
    else:
        print('  Nenhum período com férias encontrado')
