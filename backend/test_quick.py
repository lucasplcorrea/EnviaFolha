import requests
import json

# Login
print("=== TESTE DE CSV UPLOAD ===\n")
print("1. Fazendo login...")
login_resp = requests.post('http://localhost:8002/api/v1/auth/login', json={
    'username': 'admin',
    'password': 'admin123'
})

if login_resp.status_code != 200:
    print(f"❌ Erro no login: {login_resp.status_code}")
    print(login_resp.text)
    exit(1)

token = login_resp.json()['access_token']
print("✅ Login realizado com sucesso!\n")

# Upload CSV
print("2. Enviando CSV...")
csv_path = r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Empreendimentos\01-2024.CSV'
resp = requests.post(
    'http://localhost:8002/api/v1/payroll/upload-csv',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    json={
        'file_path': csv_path,
        'division_code': '0060',
        'auto_create_employees': True
    },
    timeout=300
)

print(f"Status: {resp.status_code}\n")
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
