import os

import requests
from sqlalchemy import create_engine, text

from common import ensure_backend_on_path, get_analytics_dir, get_api_base_url, get_api_credentials

ensure_backend_on_path()

from app.core.config import settings

API_URL = get_api_base_url()
API_USERNAME, API_PASSWORD = get_api_credentials()

# Login
print("🔐 Fazendo login...")
login_response = requests.post(f"{API_URL}/api/v1/auth/login", json={
    "username": API_USERNAME,
    "password": API_PASSWORD
})

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

base_path = get_analytics_dir()

for month_num, month_name, filename in [(11, "Novembro", "11-2025.CSV"), (12, "Dezembro", "12-2025.CSV")]:
    print(f"\n{'='*60}")
    print(f"📅 Re-processando {month_name}/2025")
    print(f"{'='*60}")
    
    # Deletar período existente
    periods_response = requests.get(f"{API_URL}/api/v1/payroll/periods", headers=headers)
    response_data = periods_response.json()
    periods = response_data if isinstance(response_data, list) else response_data.get('periods', [])
    
    for period in periods:
        if isinstance(period, dict) and period.get('month') == month_num and period.get('year') == 2025:
            period_id = period['id']
            print(f"🗑️ Deletando período ID {period_id}...")
            requests.delete(f"{API_URL}/api/v1/payroll/periods/{period_id}", headers=headers)
    
    # Upload
    csv_path = os.path.join(str(base_path), filename)
    print(f"📤 Processando {filename}...")
    
    upload_response = requests.post(
        f"{API_URL}/api/v1/payroll/upload-csv",
        headers=headers,
        json={'file_path': csv_path, 'division_code': '0060', 'auto_create_employees': False}
    )
    
    if upload_response.status_code == 200:
        print("✅ Upload concluído")

# Verificar valores capturados
print(f"\n{'='*60}")
print("📊 Verificando valores de 13º capturados...")
print(f"{'='*60}\n")

query = """
SELECT 
    pp.month,
    COALESCE(SUM((earnings_data->>'13_SALARIO_ADIANTAMENTO')::numeric), 0) as sal_adiant,
    COALESCE(SUM((earnings_data->>'13_SALARIO_INTEGRAL')::numeric), 0) as sal_integral,
    COALESCE(SUM((earnings_data->>'13_MEDIA_EVENTOS_VARIAVEIS')::numeric), 0) as med_evt,
    COALESCE(SUM((earnings_data->>'13_MEDIA_HORAS_EXTRAS_DIURNO')::numeric), 0) as med_he,
    COALESCE(SUM((earnings_data->>'13_GRATIFICACAO_FUNCAO_ADIANTAMENTO')::numeric), 0) as gratif_ad,
    COALESCE(SUM((earnings_data->>'13_GRATIFICACAO_FUNCAO_INTEGRAL')::numeric), 0) as gratif_int
FROM payroll_data pd
INNER JOIN payroll_periods pp ON pp.id = pd.period_id
WHERE pp.year = 2025 AND pp.month IN (11, 12)
GROUP BY pp.month
ORDER BY pp.month
"""

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    results = conn.execute(text(query))
    
    print(f"{'MÊS':12} | {'SAL. ADIANT':>13} | {'SAL. COMPL':>13} | {'TOTAL 13º':>13}")
    print("-" * 60)
    
    total_geral = 0
    for row in results:
        month, sal_ad, sal_int, med_evt, med_he, gratif_ad, gratif_int = row
        total = sal_ad + sal_int + med_evt + med_he + gratif_ad + gratif_int
        total_geral += total
        month_name = "Novembro" if month == 11 else "Dezembro"
        print(f"{month_name:12} | R$ {sal_ad:>10,.2f} | R$ {sal_int:>10,.2f} | R$ {total:>10,.2f}")
    
    print("-" * 60)
    print(f"{'TOTAL':12} | {'':>13} | {'':>13} | R$ {total_geral:>10,.2f}")
    
    if total_geral > 0:
        print(f"\n✅ Sucesso! 13º salário capturado corretamente")
    else:
        print(f"\n❌ ERRO: Valores de 13º ainda zerados")
