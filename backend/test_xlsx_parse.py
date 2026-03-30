"""Testa a leitura do xlsx do usuário com header=1"""
import sys
sys.path.insert(0, '.')

import io, os

try:
    import pandas as pd
except ImportError:
    print("❌ pandas não instalado"); sys.exit(1)

test_dir = r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\tests\novaimportacao'
files = [f for f in os.listdir(test_dir) if f.endswith(('.xlsx', '.xls'))]
if not files:
    print("❌ Nenhum arquivo xlsx encontrado em", test_dir); sys.exit(1)

path = os.path.join(test_dir, files[0])
print(f"📂 Lendo: {files[0]}")

with open(path, 'rb') as f:
    data = f.read()

# Simula o comportamento correto (header=1)
df = pd.read_excel(io.BytesIO(data), header=1, keep_default_na=False)
df = df.fillna('')
df = df[df.apply(lambda r: any(str(v).strip() for v in r.values), axis=1)]

print(f"\n✅ Colunas detectadas: {list(df.columns)}")
print(f"✅ Total de linhas: {len(df)}")
print(f"\n📋 Primeiras 3 linhas:")
for i, row in df.head(3).iterrows():
    d = row.to_dict()
    print(f"  [{i}] nome={d.get('nome','?')} | cpf={d.get('cpf','?')} | matricula={d.get('matricula','?')} | company_code={d.get('company_code','?')}")
