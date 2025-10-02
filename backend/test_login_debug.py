#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste para verificar se o problema é hasheamento de senha
"""

import urllib.request
import urllib.parse
import json

def test_login_with_different_passwords():
    """Testa login com diferentes formatos de senha"""
    url = "http://localhost:8002/api/v1/auth/login"
    
    # Senhas para testar
    passwords_to_test = [
        "admin123",  # Senha original
        "$2b$12$...",  # Formato bcrypt (exemplo)
        "21232f297a57a5a743894a0e4a801fc3",  # MD5 de "admin"
    ]
    
    for password in passwords_to_test:
        data = {
            "username": "admin",
            "password": password
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
            print(f"🧪 Testando senha: '{password[:10]}...'")
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                print(f"✅ SUCESSO com senha: {password}")
                print(f"📋 Token: {result.get('access_token', 'N/A')}")
                return password
                
        except urllib.error.HTTPError as e:
            print(f"❌ Falhou com senha: {password} (HTTP {e.code})")
            
        except Exception as e:
            print(f"❌ Erro com senha: {password} - {e}")
    
    print("🚫 Nenhuma senha funcionou!")
    return None

def check_database_users():
    """Verifica usuários no banco de dados"""
    try:
        with open('simple_db.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            users = data.get('users', [])
            
            print("👥 Usuários no banco:")
            for user in users:
                print(f"  - Username: {user.get('username')}")
                print(f"    Password: {user.get('password', 'N/A')}")
                print(f"    Email: {user.get('email', 'N/A')}")
                print()
            
            return users
    except Exception as e:
        print(f"❌ Erro ao ler banco: {e}")
        return []

if __name__ == "__main__":
    print("🔍 DIAGNÓSTICO DE LOGIN")
    print("=" * 50)
    
    print("\n1. Verificando usuários no banco...")
    users = check_database_users()
    
    print("\n2. Testando diferentes senhas...")
    working_password = test_login_with_different_passwords()
    
    if working_password:
        print(f"\n🎉 Login funcionou com: {working_password}")
    else:
        print("\n🚫 Nenhuma senha funcionou - pode ser problema de conexão")