"""Verificar valores de Status nos CSVs"""
import pandas as pd
import os

# Verificar valores de Status em vários CSVs
csv_dir = '../Analiticos/Infraestrutura'
all_status = {}

for f in os.listdir(csv_dir):
    if f.endswith('.CSV'):
        csv_path = os.path.join(csv_dir, f)
        try:
            df = pd.read_csv(csv_path, encoding='latin1', sep=';')
            if 'Status' in df.columns:
                for s in df['Status'].dropna().unique():
                    if s not in all_status:
                        all_status[s] = 0
                    all_status[s] += len(df[df['Status'] == s])
        except Exception as e:
            print(f"Erro em {f}: {e}")

print('=== VALORES ÚNICOS DE STATUS NOS CSVs ===')
for s, count in sorted(all_status.items(), key=lambda x: -x[1]):
    print(f'  "{s}": {count} registros')
