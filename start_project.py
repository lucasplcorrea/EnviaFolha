#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Envio RH - Inicializador do Projeto (PostgreSQL)
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def run_command(command, cwd=None, background=False):
    """Executa comando no terminal"""
    try:
        if background:
            if sys.platform == "win32":
                subprocess.Popen(command, shell=True, cwd=cwd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen(command, shell=True, cwd=cwd)
        else:
            result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
            return result.returncode == 0
    except Exception as e:
        print(f"Erro ao executar comando: {e}")
        return False

def main():
    print("🚀 Sistema de Envio RH v2.0 - PostgreSQL Edition")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    backend_path = project_root / "backend"
    frontend_path = project_root / "frontend"
    
    # Verificar se os diretórios existem
    if not backend_path.exists():
        print("❌ Diretório backend não encontrado!")
        return
    
    if not frontend_path.exists():
        print("❌ Diretório frontend não encontrado!")
        return
    
    print("📁 Diretórios encontrados:")
    print(f"   Backend: {backend_path}")
    print(f"   Frontend: {frontend_path}")
    print()
    
    # Verificar dependências Python
    print("🐍 Verificando ambiente Python...")
    if not run_command("python --version"):
        print("❌ Python não encontrado! Instale Python 3.11+")
        return
    
    # Verificar Node.js
    print("📦 Verificando Node.js...")
    if not run_command("node --version"):
        print("❌ Node.js não encontrado! Instale Node.js 16+")
        return
    
    print("✅ Dependências básicas verificadas!")
    print()
    
    # Iniciar backend
    print("🔧 Iniciando backend PostgreSQL...")
    backend_command = "python main.py"
    run_command(backend_command, cwd=backend_path, background=True)
    
    # Aguardar backend inicializar
    print("⏳ Aguardando backend inicializar...")
    time.sleep(3)
    
    # Iniciar frontend
    print("🎨 Iniciando frontend React...")
    frontend_command = "npm start"
    run_command(frontend_command, cwd=frontend_path, background=True)
    
    print()
    print("✅ Projeto iniciado com sucesso!")
    print("=" * 60)
    print("🌐 Frontend: http://localhost:3000")
    print("🔧 Backend: http://localhost:8002")
    print("📊 API Docs: http://localhost:8002/docs")
    print("=" * 60)
    print("💡 Pressione Ctrl+C nos terminais para parar os serviços")

if __name__ == "__main__":
    main()