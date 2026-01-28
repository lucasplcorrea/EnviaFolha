import requests
import os

# URL da API
API_URL = "http://localhost:8002"

# Fazer login para obter token
login_response = requests.post(f"{API_URL}/api/v1/auth/login", json={
    "username": "admin",
    "password": "admin123"  # Ajuste conforme sua senha
})

if login_response.status_code != 200:
    print(f"❌ Erro no login: {login_response.status_code}")
    print(login_response.text)
    exit()

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Upload do CSV
csv_path = r"C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Empreendimentos\07-2025.CSV"

if not os.path.exists(csv_path):
    print(f"❌ Arquivo não encontrado: {csv_path}")
    exit()

print(f"📤 Processando {os.path.basename(csv_path)}...")

# Enviar caminho do arquivo (não o arquivo em si)
data = {
    'file_path': csv_path,
    'division_code': '0060',  # Empreendimentos
    'auto_create_employees': False
}

upload_response = requests.post(
    f"{API_URL}/api/v1/payroll/upload-csv",
    headers=headers,
    json=data
)

if upload_response.status_code == 200:
    result = upload_response.json()
    print(f"✅ Upload concluído!")
    print(f"   Período: {result.get('period_name', 'N/A')}")
    print(f"   Registros processados: {result.get('total_processed', 0)}")
else:
    print(f"❌ Erro no upload: {upload_response.status_code}")
    print(upload_response.text)
