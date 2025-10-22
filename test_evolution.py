#!/usr/bin/env python3
"""Script para testar a Evolution API"""

import requests
import json

def test_evolution_api():
    url = "http://localhost:8002/api/v1/evolution/test-message"
    
    payload = {
        "phone_number": "5547988588869",
        "message": "🚀 Teste do Sistema EnviaFolha - Evolution API funcionando perfeitamente!"
    }
    
    print("📤 Enviando mensagem de teste...")
    print(f"URL: {url}")
    print(f"Telefone: {payload['phone_number']}")
    print(f"Mensagem: {payload['message']}")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("\n✅ Mensagem enviada com sucesso!")
            else:
                print(f"\n❌ Erro: {result.get('error')}")
        else:
            print(f"\n❌ Erro HTTP {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar ao backend")
        print("Certifique-se de que o backend está rodando em http://localhost:8002")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    test_evolution_api()
