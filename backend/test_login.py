#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste rápido do endpoint de login
"""

import urllib.request
import urllib.parse
import json

def test_login():
    """Testa o endpoint de login"""
    url = "http://localhost:8002/api/v1/auth/login"
    
    data = {
        "username": "admin",
        "password": "admin123"
    }
    
    # Preparar requisição
    data_encoded = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data_encoded,
        headers={
            'Content-Type': 'application/json',
            'Content-Length': len(data_encoded)
        },
        method='POST'
    )
    
    try:
        print("🧪 Testando login...")
        print(f"📡 URL: {url}")
        print(f"📝 Dados: {data}")
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("✅ Login bem-sucedido!")
            print(f"📋 Resposta: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return True
            
    except urllib.error.HTTPError as e:
        print(f"❌ Erro HTTP {e.code}: {e.reason}")
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            print(f"📋 Erro: {error_data}")
        except:
            print("Não foi possível ler a resposta de erro")
        return False
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    test_login()