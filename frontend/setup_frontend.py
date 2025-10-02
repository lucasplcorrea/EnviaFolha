import subprocess
import sys
import os
from pathlib import Path

def setup_frontend():
    """Configura o frontend React"""
    print("🎨 Configurando Frontend React...")
    
    # Verificar se estamos na pasta frontend
    if not Path("package.json").exists():
        print("❌ Execute este script na pasta frontend/")
        return False
    
    # Verificar Node.js
    try:
        node_version = subprocess.check_output(["node", "--version"], text=True).strip()
        print(f"✅ Node.js {node_version}")
    except:
        print("❌ Node.js não encontrado!")
        print("💡 Instale em: https://nodejs.org/")
        return False
    
    # Verificar npm
    try:
        npm_version = subprocess.check_output(["npm", "--version"], text=True).strip()
        print(f"✅ npm {npm_version}")
    except:
        print("❌ npm não encontrado!")
        return False
    
    # Instalar dependências
    print("\n📦 Instalando dependências...")
    try:
        subprocess.run(["npm", "install"], check=True)
        print("✅ Dependências instaladas!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        return False
    
    # Configurar Tailwind CSS
    print("\n🎨 Configurando Tailwind CSS...")
    try:
        subprocess.run(["npx", "tailwindcss", "init", "-p"], check=True)
        print("✅ Tailwind configurado!")
    except subprocess.CalledProcessError:
        print("⚠️ Tailwind já configurado ou erro na configuração")
    
    print("\n✅ Frontend configurado com sucesso!")
    print("🚀 Execute: npm start")
    return True

if __name__ == "__main__":
    setup_frontend()
