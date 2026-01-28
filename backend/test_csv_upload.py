"""
Script de teste para processar CSV de folha de pagamento
Testa o novo endpoint /api/v1/payroll/upload-csv
"""
import requests
import json
import os
from pathlib import Path

# Configurações
BASE_URL = "http://localhost:8002"  # Porta padrão do main_legacy.py
API_ENDPOINT = f"{BASE_URL}/api/v1/payroll/upload-csv"

# Credenciais de teste (ajustar conforme necessário)
USERNAME = "admin"
PASSWORD = "admin123"  # Senha padrão do sistema

def get_auth_token():
    """Faz login e obtém token JWT"""
    login_url = f"{BASE_URL}/api/v1/auth/login"
    response = requests.post(login_url, json={
        "username": USERNAME,
        "password": PASSWORD
    })
    
    if response.status_code == 200:
        data = response.json()
        return data.get('access_token')
    else:
        print(f"❌ Erro no login: {response.status_code}")
        print(response.text)
        return None

def test_csv_upload(csv_filename, division_code='0060', auto_create=False):
    """
    Testa upload de CSV
    
    Args:
        csv_filename: Nome do arquivo CSV (ex: '01-2024.CSV')
        division_code: '0060' (Empreendimentos) ou '0059' (Infraestrutura)
        auto_create: Se True, cria funcionários não encontrados
    """
    # Obter token
    token = get_auth_token()
    if not token:
        print("❌ Não foi possível obter token de autenticação")
        return
    
    # Caminho do arquivo
    project_root = Path(__file__).parent.parent
    if division_code == '0060':
        csv_path = project_root / 'Analiticos' / 'Empreendimentos' / csv_filename
    else:
        csv_path = project_root / 'Analiticos' / 'Infraestrutura' / csv_filename
    
    if not csv_path.exists():
        print(f"❌ Arquivo não encontrado: {csv_path}")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 TESTE DE UPLOAD DE CSV")
    print(f"{'='*60}")
    print(f"📁 Arquivo: {csv_filename}")
    print(f"🏢 Divisão: {division_code} ({'Empreendimentos' if division_code == '0060' else 'Infraestrutura'})")
    print(f"👤 Auto-criar: {auto_create}")
    print(f"📍 Caminho: {csv_path}")
    print(f"{'='*60}\n")
    
    # Preparar request
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "file_path": str(csv_path),
        "division_code": division_code,
        "auto_create_employees": auto_create
    }
    
    print("🚀 Enviando requisição...\n")
    
    # Enviar request
    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=payload, timeout=300)
        
        print(f"📡 Status Code: {response.status_code}")
        print(f"\n📄 Resposta:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"\n✅ CSV PROCESSADO COM SUCESSO!")
                print(f"\n📊 ESTATÍSTICAS:")
                stats = result.get('stats', {})
                for key, value in stats.items():
                    print(f"   • {key}: {value}")
                
                if result.get('errors'):
                    print(f"\n⚠️ ERROS ENCONTRADOS ({len(result['errors'])}):")
                    for error in result['errors'][:5]:  # Mostrar apenas 5 primeiros
                        print(f"   • Linha {error.get('row')}: {error.get('error')}")
                
                if result.get('warnings'):
                    print(f"\n⚠️ AVISOS ({len(result['warnings'])}):")
                    for warning in result['warnings'][:5]:
                        print(f"   • {warning}")
            else:
                print(f"\n❌ FALHA NO PROCESSAMENTO")
                print(f"Erro: {result.get('error')}")
        else:
            print(f"\n❌ ERRO NA REQUISIÇÃO")
            
    except requests.exceptions.Timeout:
        print("❌ Timeout: Requisição demorou mais de 5 minutos")
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

if __name__ == '__main__':
    print("="*60)
    print("🧪 TESTE DE PROCESSAMENTO DE CSV - FASE 1")
    print("="*60)
    
    # TESTE 1: CSV Mensal (Janeiro 2024) - Empreendimentos
    test_csv_upload(
        csv_filename='01-2024.CSV',
        division_code='0060',
        auto_create=True  # Criar funcionários automaticamente para teste
    )
    
    # Para testar outros arquivos, descomentar:
    # 
    # # TESTE 2: 13º Salário Adiantamento
    # test_csv_upload(
    #     csv_filename='AdiantamentoDecimoTerceiro-11-2024.CSV',
    #     division_code='0060',
    #     auto_create=False
    # )
    # 
    # # TESTE 3: Infraestrutura
    # test_csv_upload(
    #     csv_filename='01-2024.CSV',
    #     division_code='0059',
    #     auto_create=True
    # )
