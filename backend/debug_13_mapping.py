import pandas as pd
import re

def parse_br_number(value):
    """Parse Brazilian number format"""
    if pd.isna(value) or value == '' or value is None:
        return 0.0
    
    try:
        # Remove espaços
        value_str = str(value).strip()
        
        # Remove pontos (separador de milhares)
        value_str = value_str.replace('.', '')
        
        # Substitui vírgula por ponto (separador decimal)
        value_str = value_str.replace(',', '.')
        
        # Remove qualquer caractere não numérico exceto ponto e sinal negativo
        value_str = re.sub(r'[^\d.-]', '', value_str)
        
        return float(value_str) if value_str and value_str != '-' else 0.0
    except Exception as e:
        return 0.0

# Ler CSV
df = pd.read_csv(
    r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Empreendimentos\11-2025.CSV',
    delimiter=';',
    encoding='latin-1',
    dtype=str
)

print("="*70)
print("TESTE DE MAPEAMENTO DE 13º SALÁRIO - NOVEMBRO")
print("="*70)

# Verificar colunas
decimo_fields = {
    '13_SALARIO_ADIANTAMENTO': '13o Salário Proporcional',
    '13_GRATIFICACAO_FUNCAO_ADIANTAMENTO': 'Gratificacao Função 13o Sal.Prop.',
    '13_MEDIA_EVENTOS_VARIAVEIS': 'Med.Eve.Var.13o Sal.Prop.',
    '13_MEDIA_HORAS_EXTRAS_DIURNO': 'Med.Hrs.Ext.Diurnas 13o Sal.Prop.',
}

for json_field, csv_field in decimo_fields.items():
    print(f"\n{json_field}:")
    print(f"  Coluna CSV: '{csv_field}'")
    print(f"  Existe: {csv_field in df.columns}")
    
    if csv_field in df.columns:
        # Filtrar valores não-nulos
        non_null = df[csv_field].dropna()
        non_empty = non_null[non_null != '']
        
        print(f"  Total registros: {len(df)}")
        print(f"  Não-nulos: {len(non_null)}")
        print(f"  Não-vazios: {len(non_empty)}")
        
        if len(non_empty) > 0:
            # Parsear valores
            values = [parse_br_number(v) for v in non_empty]
            positive_values = [v for v in values if v > 0]
            
            print(f"  Com valor > 0: {len(positive_values)}")
            print(f"  Total: R$ {sum(positive_values):,.2f}")
            print(f"  Exemplo de valores:")
            for i, val in enumerate(non_empty.head()):
                parsed = parse_br_number(val)
                print(f"    '{val}' → {parsed}")

print("\n" + "="*70)
print("RESUMO")
print("="*70)

total_13 = 0
for json_field, csv_field in decimo_fields.items():
    if csv_field in df.columns:
        non_empty = df[csv_field].dropna()
        non_empty = non_empty[non_empty != '']
        values = [parse_br_number(v) for v in non_empty]
        positive_values = sum([v for v in values if v > 0])
        total_13 += positive_values
        if positive_values > 0:
            print(f"{json_field:40}: R$ {positive_values:>12,.2f}")

print("-"*70)
print(f"{'TOTAL 13º NOVEMBRO':40}: R$ {total_13:>12,.2f}")
