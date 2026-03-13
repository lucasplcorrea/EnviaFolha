import os

import requests

from common import ensure_backend_on_path, get_analytics_dir, get_api_base_url, get_api_credentials

ensure_backend_on_path()

# URL da API
API_URL = get_api_base_url()
API_USERNAME, API_PASSWORD = get_api_credentials()

# Fazer login para obter token
print("🔐 Fazendo login...")
login_response = requests.post(f"{API_URL}/api/v1/auth/login", json={
    "username": API_USERNAME,
    "password": API_PASSWORD
})

if login_response.status_code != 200:
    print(f"❌ Erro no login: {login_response.status_code}")
    print(login_response.text)
    exit()

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Primeiro, deletar o período existente de fevereiro/2025
print("🗑️ Deletando período Fevereiro/2025 existente...")
periods_response = requests.get(f"{API_URL}/api/v1/payroll/periods", headers=headers)
if periods_response.status_code == 200:
    response_data = periods_response.json()
    periods = response_data if isinstance(response_data, list) else response_data.get('periods', [])
    for period in periods:
        if isinstance(period, dict) and period.get('month') == 2 and period.get('year') == 2025:
            period_id = period['id']
            print(f"   Encontrado período ID {period_id}, deletando...")
            delete_response = requests.delete(
                f"{API_URL}/api/v1/payroll/periods/{period_id}",
                headers=headers
            )
            if delete_response.status_code == 200:
                print("   ✅ Período deletado")
            else:
                print(f"   ⚠️ Erro ao deletar: {delete_response.status_code}")

# Upload do CSV
csv_path = os.path.join(str(get_analytics_dir()), "02-2025.CSV")

if not os.path.exists(csv_path):
    print(f"❌ Arquivo não encontrado: {csv_path}")
    exit()

print(f"\n📤 Re-processando {os.path.basename(csv_path)}...")

# Enviar caminho do arquivo
data = {
    'file_path': csv_path,
    'division_code': '0060',
    'auto_create_employees': False
}

upload_response = requests.post(
    f"{API_URL}/api/v1/payroll/upload-csv",
    headers=headers,
    json=data
)

if upload_response.status_code == 200:
    result = upload_response.json()
    print(f"\n✅ Re-processamento concluído!")
    print(f"   Período: {result.get('period_name', 'N/A')}")
    print(f"   Registros processados: {result.get('total_processed', 0)}")
    print(f"   Colaboradores únicos: {result.get('unique_employees', 0)}")
else:
    print(f"\n❌ Erro no upload: {upload_response.status_code}")
    print(upload_response.text)

# Verificar os novos valores de férias
print("\n🔍 Verificando valores de férias capturados...")
check_query = """
SELECT 
    COUNT(*) as total_records,
    COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3')::numeric), 0) as total_abono,
    COALESCE(SUM((earnings_data->>'FERIAS_GRATIFICACAO')::numeric), 0) as total_gratif,
    COALESCE(SUM((earnings_data->>'FERIAS_GRATIFICACAO_PROPORC')::numeric), 0) as total_gratif_prop,
    COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_EVENTOS')::numeric), 0) as total_med_eventos,
    COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_HORAS_EXTRAS')::numeric), 0) as total_med_he
FROM payroll_data pd
INNER JOIN payroll_periods pp ON pp.id = pd.period_id
WHERE pp.month = 2 AND pp.year = 2025
"""

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text(check_query))
    row = result.fetchone()
    
    print(f"\n📊 Resultados Fevereiro/2025:")
    print(f"   Total de registros: {row[0]}")
    print(f"   Férias Abono 1/3: R$ {row[1]:,.2f}")
    print(f"   Férias Gratificação: R$ {row[2]:,.2f}")
    print(f"   Férias Gratif. Proporc.: R$ {row[3]:,.2f}")
    print(f"   Férias Média Eventos: R$ {row[4]:,.2f}")
    print(f"   Férias Média HE: R$ {row[5]:,.2f}")
    print(f"   \n   💰 TOTAL FÉRIAS: R$ {sum([row[1], row[2], row[3], row[4], row[5]]):,.2f}")
