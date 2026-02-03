"""Verificar todos os valores de Situação/Descrição nos CSVs"""
import pandas as pd
import os

csv_dir = '../Analiticos/Infraestrutura'
all_situations = {}

for f in os.listdir(csv_dir):
    if f.endswith('.CSV'):
        csv_path = os.path.join(csv_dir, f)
        try:
            df = pd.read_csv(csv_path, encoding='latin1', sep=';')
            if 'Situação' in df.columns and 'Descrição' in df.columns:
                for _, row in df[['Situação', 'Descrição']].drop_duplicates().iterrows():
                    key = (row['Situação'], row['Descrição'])
                    if key not in all_situations:
                        all_situations[key] = 0
                    all_situations[key] += 1
        except Exception as e:
            print(f"Erro em {f}: {e}")

print('=== TODOS OS TIPOS DE SITUAÇÃO NOS CSVs ===')
for (sit, desc), count in sorted(all_situations.items(), key=lambda x: x[0][0]):
    print(f'  Código {sit}: "{desc}" ({count} arquivos)')
