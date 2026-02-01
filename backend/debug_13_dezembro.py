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

# Ler CSV de dezembro
df = pd.read_csv(
    r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Empreendimentos\12-2025.CSV',
    delimiter=';',
    encoding='latin-1',
    dtype=str
)

print("="*70)
print("TESTE DE MAPEAMENTO DE 13º SALÁRIO - DEZEMBRO")
print("="*70)

decimo_fields = {
    '13_SALARIO_INTEGRAL': '13o Salário Complementar',
    '13_SALARIO_INDENIZADO': '13o Salário Indenizado',
    '13_SALARIO_MATERNIDADE_GPS': '13o Salário Lic.Mater.Rescisão (GPS)',
    '13_MEDIA_EVENTOS_VARIAVEIS_IND': 'Med.Eve.Var. 13o Sal.Ind.',
    '13_MEDIA_HORAS_EXTRAS_IND': 'Med.Hrs.Ext.Diurnas 13o Sal.Ind.',
}

total_13 = 0
for json_field, csv_field in decimo_fields.items():
    print(f"\n{json_field}:")
    print(f"  Coluna CSV: '{csv_field}'")
    print(f"  Existe: {csv_field in df.columns}")
    
    if csv_field in df.columns:
        non_empty = df[csv_field].dropna()
        non_empty = non_empty[non_empty != '']
        
        if len(non_empty) > 0:
            values = [parse_br_number(v) for v in non_empty]
            positive_values = sum([v for v in values if v > 0])
            total_13 += positive_values
            
            if positive_values > 0:
                print(f"  Total: R$ {positive_values:,.2f}")
                print(f"  Registros com valor > 0: {len([v for v in values if v > 0])}")

print("\n" + "="*70)
print(f"TOTAL 13º DEZEMBRO: R$ {total_13:,.2f}")
