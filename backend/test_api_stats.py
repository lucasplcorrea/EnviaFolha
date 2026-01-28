import requests

API_URL = "http://localhost:8002"

# Login
login_response = requests.post(f"{API_URL}/api/v1/auth/login", json={
    "username": "admin",
    "password": "admin123"
})

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Buscar estatísticas gerais
stats_response = requests.get(
    f"{API_URL}/api/v1/payroll/statistics",
    headers=headers
)

if stats_response.status_code == 200:
    stats = stats_response.json()
    print("📊 Estatísticas retornadas pela API:")
    print(f"   Total Gratificações: R$ {stats.get('total_gratificacoes', 0):,.2f}")
    print(f"   Total HE 50% Diurnas: R$ {stats.get('total_he_50_diurnas', 0):,.2f}")
    print(f"   Total HE 50% Noturnas: R$ {stats.get('total_he_50_noturnas', 0):,.2f}")
    print(f"   Total HE 60%: R$ {stats.get('total_he_60', 0):,.2f}")
    print(f"   Total HE 100% Diurnas: R$ {stats.get('total_he_100_diurnas', 0):,.2f}")
    print(f"   Total HE 100% Noturnas: R$ {stats.get('total_he_100_noturnas', 0):,.2f}")
    print(f"   Total Adicional Noturno: R$ {stats.get('total_adicional_noturno', 0):,.2f}")
    print(f"   Total Periculosidade: R$ {stats.get('total_periculosidade', 0):,.2f}")
    print(f"   Total Insalubridade: R$ {stats.get('total_insalubridade', 0):,.2f}")
    print(f"   Total Vale Transporte: R$ {stats.get('total_vale_transporte', 0):,.2f}")
    print(f"   Total Horas Noturnas: {stats.get('total_horas_noturnas', 0)}")
else:
    print(f"❌ Erro: {stats_response.status_code}")
    print(stats_response.text)
