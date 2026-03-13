"""
Script para reprocessar TODOS os meses de 2024 e 2025.
Isso irá capturar todas as novas colunas de 13º Salário e Férias.
"""

import os
import time

import requests

from common import get_analytics_dir, get_api_base_url, get_api_credentials

# URL da API
API_URL = get_api_base_url()
API_USERNAME, API_PASSWORD = get_api_credentials()

# Todos os meses a processar (2024 e 2025)
months_to_process = [
    # 2024
    (1, 2024, "Janeiro", "01-2024.CSV"),
    (2, 2024, "Fevereiro", "02-2024.CSV"),
    (3, 2024, "Março", "03-2024.CSV"),
    (4, 2024, "Abril", "04-2024.CSV"),
    (5, 2024, "Maio", "05-2024.CSV"),
    (6, 2024, "Junho", "06-2024.CSV"),
    (7, 2024, "Julho", "07-2024.CSV"),
    (8, 2024, "Agosto", "08-2024.CSV"),
    (9, 2024, "Setembro", "09-2024.CSV"),
    (10, 2024, "Outubro", "10-2024.CSV"),
    (11, 2024, "Novembro", "11-2024.CSV"),
    (12, 2024, "Dezembro", "12-2024.CSV"),
    # 2025
    (1, 2025, "Janeiro", "01-2025.CSV"),
    (2, 2025, "Fevereiro", "02-2025.CSV"),
    (3, 2025, "Março", "03-2025.CSV"),
    (4, 2025, "Abril", "04-2025.CSV"),
    (5, 2025, "Maio", "05-2025.CSV"),
    (6, 2025, "Junho", "06-2025.CSV"),
    (7, 2025, "Julho", "07-2025.CSV"),
    (8, 2025, "Agosto", "08-2025.CSV"),
    (9, 2025, "Setembro", "09-2025.CSV"),
    (10, 2025, "Outubro", "10-2025.CSV"),
    (11, 2025, "Novembro", "11-2025.CSV"),
    (12, 2025, "Dezembro", "12-2025.CSV"),
]

base_path = get_analytics_dir()

# Fazer login
print("🔐 Fazendo login...")
login_response = requests.post(f"{API_URL}/api/v1/auth/login", json={
    "username": API_USERNAME,
    "password": API_PASSWORD
})

if login_response.status_code != 200:
    print(f"❌ Erro no login: {login_response.status_code} - {login_response.text}")
    exit()

token = login_response.json()["access_token"]
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

success_count = 0
error_count = 0

# Processar cada mês
for month_num, year, month_name, filename in months_to_process:
    print(f"\n{'='*60}")
    print(f"📅 Processando {month_name}/{year}")
    print(f"{'='*60}")
    
    # Deletar período existente
    periods_response = requests.get(f"{API_URL}/api/v1/payroll/periods", headers=headers)
    if periods_response.status_code == 200:
        response_data = periods_response.json()
        periods = response_data if isinstance(response_data, list) else response_data.get('periods', [])
        for period in periods:
            if isinstance(period, dict) and period.get('month') == month_num and period.get('year') == year:
                period_id = period['id']
                print(f"🗑️ Deletando período existente (ID {period_id})...")
                delete_response = requests.delete(
                    f"{API_URL}/api/v1/payroll/periods/{period_id}",
                    headers=headers
                )
                if delete_response.status_code == 200:
                    print("   ✅ Período deletado")
                else:
                    print(f"   ⚠️ Erro ao deletar: {delete_response.status_code}")
    
    # Processar CSV via JSON (endpoint correto)
    file_path = os.path.join(str(base_path), filename)
    if os.path.exists(file_path):
        print(f"📄 Processando CSV: {filename}")
        
        # Usar endpoint /api/v1/payroll/upload-csv com JSON
        response = requests.post(
            f"{API_URL}/api/v1/payroll/upload-csv",
            json={
                "file_path": file_path,
                "division_code": "0060",  # Empreendimentos
                "auto_create_employees": True
            },
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            stats = result.get('stats', {})
            print(f"   ✅ Sucesso!")
            print(f"      - Funcionários: {stats.get('employees_processed', 0)}")
            print(f"      - Registros: {stats.get('records_created', 0)}")
            print(f"      - Período: {stats.get('period_id', 'N/A')}")
            success_count += 1
        else:
            print(f"   ❌ Erro: {response.status_code} - {response.text[:200]}")
            error_count += 1
    else:
        print(f"   ⚠️ Arquivo não encontrado: {file_path}")
        error_count += 1
    
    # Pequena pausa entre processamentos
    time.sleep(0.5)

print(f"\n{'='*60}")
print(f"📊 RESUMO DO PROCESSAMENTO")
print(f"{'='*60}")
print(f"✅ Sucesso: {success_count} meses")
print(f"❌ Erros: {error_count} meses")
print(f"📁 Total: {len(months_to_process)} meses")
print(f"{'='*60}")
