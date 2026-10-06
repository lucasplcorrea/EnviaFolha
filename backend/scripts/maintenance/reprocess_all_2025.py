import os

import requests
from sqlalchemy import create_engine, text

from common import ensure_backend_on_path, get_analytics_dir, get_api_base_url, get_api_credentials

ensure_backend_on_path()

from app.core.config import settings

# URL da API
API_URL = get_api_base_url()
API_USERNAME, API_PASSWORD = get_api_credentials()

# Meses para re-processar (excluindo 07 e 02 que já foram feitos)
months_to_process = [
    (1, "Janeiro", "01-2025.CSV"),
    (3, "Março", "03-2025.CSV"),
    (4, "Abril", "04-2025.CSV"),
    (5, "Maio", "05-2025.CSV"),
    (6, "Junho", "06-2025.CSV"),
    (8, "Agosto", "08-2025.CSV"),
    (9, "Setembro", "09-2025.CSV"),
    (10, "Outubro", "10-2025.CSV"),
    (11, "Novembro", "11-2025.CSV"),
    (12, "Dezembro", "12-2025.CSV"),
]

base_path = get_analytics_dir()

# Fazer login
print("🔐 Fazendo login...")
login_response = requests.post(f"{API_URL}/api/v1/auth/login", json={
    "username": API_USERNAME,
    "password": API_PASSWORD
})

if login_response.status_code != 200:
    print(f"❌ Erro no login: {login_response.status_code}")
    exit()

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Processar cada mês
for month_num, month_name, filename in months_to_process:
    print(f"\n{'='*60}")
    print(f"📅 Processando {month_name}/2025")
    print(f"{'='*60}")
    
    # Deletar período existente
    periods_response = requests.get(f"{API_URL}/api/v1/payroll/periods", headers=headers)
    if periods_response.status_code == 200:
        response_data = periods_response.json()
        periods = response_data if isinstance(response_data, list) else response_data.get('periods', [])
        for period in periods:
            if isinstance(period, dict) and period.get('month') == month_num and period.get('year') == 2025:
                period_id = period['id']
                print(f"🗑️ Deletando período existente (ID {period_id})...")
                delete_response = requests.delete(
                    f"{API_URL}/api/v1/payroll/periods/{period_id}",
                    headers=headers
                )
                if delete_response.status_code == 200:
                    print("   ✅ Período deletado")
    
    # Verificar se arquivo existe
    csv_path = os.path.join(str(base_path), filename)
    if not os.path.exists(csv_path):
        print(f"⚠️ Arquivo não encontrado: {filename}")
        continue
    
    # Upload do CSV
    print(f"📤 Processando {filename}...")
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
    
    if upload_response.status_code != 200:
        print(f"❌ Erro no upload: {upload_response.status_code}")
        print(upload_response.text)
        continue
    
    result = upload_response.json()
    print(f"✅ Upload concluído - {result.get('total_processed', 0)} registros")
    
    # Verificar valores de férias
    check_query = f"""
    SELECT 
        COUNT(*) as total_records,
        COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3')::numeric), 0) as total_abono,
        COALESCE(SUM((earnings_data->>'FERIAS_GRATIFICACAO')::numeric), 0) as total_gratif,
        COALESCE(SUM((earnings_data->>'FERIAS_GRATIFICACAO_PROPORC')::numeric), 0) as total_gratif_prop,
        COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_EVENTOS')::numeric), 0) as total_med_eventos,
        COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_HORAS_EXTRAS')::numeric), 0) as total_med_he
    FROM payroll_data pd
    INNER JOIN payroll_periods pp ON pp.id = pd.period_id
    WHERE pp.month = {month_num} AND pp.year = 2025
    """
    
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        result_row = conn.execute(text(check_query))
        row = result_row.fetchone()
        
        total_ferias = sum([row[1], row[2], row[3], row[4], row[5]])
        print(f"💰 Férias capturadas: R$ {total_ferias:,.2f}")
        if total_ferias > 0:
            print(f"   └─ Abono 1/3: R$ {row[1]:,.2f}")
            print(f"   └─ Gratificação: R$ {row[2]:,.2f}")
            print(f"   └─ Gratif. Proporc.: R$ {row[3]:,.2f}")

print(f"\n{'='*60}")
print("🎉 Re-processamento completo!")
print(f"{'='*60}")

# Resumo final
print("\n📊 Verificando totais por período...")
summary_query = """
SELECT 
    pp.month,
    pp.year,
    COUNT(*) as total_records,
    COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3')::numeric), 0) +
    COALESCE(SUM((earnings_data->>'FERIAS_GRATIFICACAO')::numeric), 0) +
    COALESCE(SUM((earnings_data->>'FERIAS_GRATIFICACAO_PROPORC')::numeric), 0) +
    COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_EVENTOS')::numeric), 0) +
    COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_HORAS_EXTRAS')::numeric), 0) as total_ferias
FROM payroll_data pd
INNER JOIN payroll_periods pp ON pp.id = pd.period_id
WHERE pp.year = 2025
GROUP BY pp.month, pp.year
ORDER BY pp.month
"""

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    results = conn.execute(text(summary_query))
    
    month_names = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                   "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    
    total_geral = 0
    print("\nPERÍODO          | REGISTROS | FÉRIAS")
    print("-" * 50)
    for row in results:
        month, year, records, ferias = row
        month_name = month_names[month]
        print(f"{month_name:15} | {records:9} | R$ {ferias:>12,.2f}")
        total_geral += ferias
    
    print("-" * 50)
    print(f"{'TOTAL':15} | {'':9} | R$ {total_geral:>12,.2f}")
