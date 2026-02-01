from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

# Verificar TODOS os campos de 13º e Férias no banco
query = """
SELECT 
    pp.month,
    pp.year,
    COUNT(*) as registros,
    -- 13º Salário
    COALESCE(SUM((earnings_data->>'13_SALARIO_ADIANTAMENTO')::numeric), 0) as sal_13_adiant,
    COALESCE(SUM((earnings_data->>'13_SALARIO_INTEGRAL')::numeric), 0) as sal_13_integral,
    -- Férias
    COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3')::numeric), 0) as ferias_abono,
    COALESCE(SUM((earnings_data->>'FERIAS_GRATIFICACAO')::numeric), 0) as ferias_gratif,
    COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_HORAS_EXTRAS')::numeric), 0) as ferias_med_he,
    -- Descontos
    COALESCE(SUM((deductions_data->>'DESCONTO_13_ADIANTAMENTO')::numeric), 0) as desc_13,
    COALESCE(SUM((deductions_data->>'DESCONTO_FERIAS_ADIANTAMENTO')::numeric), 0) as desc_ferias
FROM payroll_data pd
INNER JOIN payroll_periods pp ON pp.id = pd.period_id
WHERE pp.year = 2025 AND pp.month IN (11, 12)
GROUP BY pp.month, pp.year
ORDER BY pp.month
"""

with engine.connect() as conn:
    results = conn.execute(text(query))
    print('='*100)
    print('VALORES NO BANCO - NOV/DEZ 2025')
    print('='*100)
    print(f"{'MÊS':6} | {'REG':>4} | {'13 ADIANT':>11} | {'13 INTEG':>10} | {'FER ABONO':>10} | {'FER GRATIF':>11} | {'FER MED HE':>11} | {'DESC 13':>10} | {'DESC FER':>10}")
    print('-' * 100)
    for row in results:
        month = 'Nov' if row[0] == 11 else 'Dez'
        print(f"{month:6} | {row[2]:>4} | R$ {row[3]:>8,.2f} | R$ {row[4]:>7,.2f} | R$ {row[5]:>7,.2f} | R$ {row[6]:>8,.2f} | R$ {row[7]:>8,.2f} | R$ {row[8]:>7,.2f} | R$ {row[9]:>7,.2f}")

# Agora verificar os valores nos CSVs originais para comparar
print("\n" + "="*100)
print("VERIFICANDO VALORES ORIGINAIS NOS CSVs")
print("="*100)

import pandas as pd
import re

def parse_br_number(value):
    if pd.isna(value) or value == '' or value is None:
        return 0.0
    try:
        value_str = str(value).strip().replace('.', '').replace(',', '.')
        value_str = re.sub(r'[^\d.-]', '', value_str)
        return float(value_str) if value_str and value_str != '-' else 0.0
    except:
        return 0.0

# Novembro
nov_df = pd.read_csv(
    r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Empreendimentos\11-2025.CSV',
    delimiter=';', encoding='latin-1', dtype=str
)

print(f"\nNOVEMBRO 2025 (CSV):")
print(f"  - Registros: {len(nov_df)}")

# Verificar coluna de 13º
for col in ['13o Salário Proporcional', '13o Salário Adiantamento', '13o Salário Indenizado']:
    if col in nov_df.columns:
        total = sum(parse_br_number(v) for v in nov_df[col].dropna())
        if total > 0:
            print(f"  - {col}: R$ {total:,.2f}")

# Verificar coluna de férias
for col in ['1/3 Sobre Férias', 'Gratificacao Função Férias', 'Med.Hrs.Ext.S/Férias Diurnas']:
    if col in nov_df.columns:
        total = sum(parse_br_number(v) for v in nov_df[col].dropna())
        if total > 0:
            print(f"  - {col}: R$ {total:,.2f}")

# Dezembro
dez_df = pd.read_csv(
    r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Empreendimentos\12-2025.CSV',
    delimiter=';', encoding='latin-1', dtype=str
)

print(f"\nDEZEMBRO 2025 (CSV):")
print(f"  - Registros: {len(dez_df)}")

# Verificar coluna de 13º
for col in ['13o Salário Complementar', '13o Salário Proporcional', '13o Salário Indenizado']:
    if col in dez_df.columns:
        total = sum(parse_br_number(v) for v in dez_df[col].dropna())
        if total > 0:
            print(f"  - {col}: R$ {total:,.2f}")

# Verificar coluna de férias
for col in ['1/3 Sobre Férias', 'Gratificacao Função Férias', 'Med.Hrs.Ext.S/Férias Diurnas']:
    if col in dez_df.columns:
        total = sum(parse_br_number(v) for v in dez_df[col].dropna())
        if total > 0:
            print(f"  - {col}: R$ {total:,.2f}")

# Verificar desconto de férias
for col in ['Desconto Férias Adiantamento', 'Desc. Férias Adiantamento', 'Desconto Ferias Adiantamento']:
    if col in dez_df.columns:
        total = sum(parse_br_number(v) for v in dez_df[col].dropna())
        if total > 0:
            print(f"  - {col}: R$ {total:,.2f}")

# Listar todas as colunas com 'Férias' ou 'Ferias'
print("\n" + "="*100)
print("COLUNAS COM 'FÉRIAS' OU 'FERIAS' NOS CSVs:")
print("="*100)
print("\nNovembro:")
for col in nov_df.columns:
    if 'rias' in col.lower():
        total = sum(parse_br_number(v) for v in nov_df[col].dropna())
        print(f"  '{col}': R$ {total:,.2f}")

print("\nDezembro:")
for col in dez_df.columns:
    if 'rias' in col.lower():
        total = sum(parse_br_number(v) for v in dez_df[col].dropna())
        print(f"  '{col}': R$ {total:,.2f}")
