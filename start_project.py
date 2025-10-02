import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

def check_requirements():
    """Verifica se Python e Node.js estão instalados"""
    print("🔍 Verificando pré-requisitos...")
    
    # Verificar Python
    try:
        python_version = subprocess.check_output([sys.executable, "--version"], text=True).strip()
        print(f"✅ {python_version}")
    except:
        print("❌ Python não encontrado!")
        return False
    
    # Verificar Node.js
    try:
        node_version = subprocess.check_output(["node", "--version"], text=True).strip()
        print(f"✅ Node.js {node_version}")
    except:
        print("❌ Node.js não encontrado!")
        print("💡 Instale Node.js em: https://nodejs.org/")
        return False
    
    # Verificar npm
    try:
        npm_version = subprocess.check_output(["npm", "--version"], text=True).strip()
        print(f"✅ npm {npm_version}")
    except:
        print("❌ npm não encontrado!")
        return False
    
    return True

def start_backend():
    """Inicia o servidor backend"""
    print("\n🔧 Iniciando Backend...")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ Pasta backend não encontrada!")
        return None
    
    os.chdir(backend_dir)
    
    # Instalar dependências Python se necessário
    if not Path(".venv").exists():
        print("📦 Instalando dependências Python...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Iniciar servidor
    print("🚀 Iniciando servidor API...")
    backend_process = subprocess.Popen([
        sys.executable, "run_server.py"
    ])
    
    os.chdir("..")
    return backend_process

def start_frontend():
    """Inicia o servidor frontend"""
    print("\n🎨 Iniciando Frontend...")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Pasta frontend não encontrada!")
        return None
    
    os.chdir(frontend_dir)
    
    # Instalar dependências Node.js se necessário
    if not Path("node_modules").exists():
        print("📦 Instalando dependências Node.js...")
        subprocess.run(["npm", "install"])
    
    # Iniciar servidor
    print("🚀 Iniciando interface web...")
    frontend_process = subprocess.Popen([
        "npm", "start"
    ])
    
    os.chdir("..")
    return frontend_process

def main():
    print("🚀 Sistema de Envio RH v2.0")
    print("=" * 40)
    
    if not check_requirements():
        print("\n❌ Pré-requisitos não atendidos!")
        return
    
    try:
        # Iniciar backend
        backend_process = start_backend()
        if not backend_process:
            print("❌ Falha ao iniciar backend!")
            return
        
        print("⏳ Aguardando backend inicializar...")
        time.sleep(5)
        
        # Iniciar frontend  
        frontend_process = start_frontend()
        if not frontend_process:
            print("❌ Falha ao iniciar frontend!")
            backend_process.terminate()
            return
        
        print("⏳ Aguardando frontend inicializar...")
        time.sleep(10)
        
        # Abrir navegador
        print("\n✅ Sistema iniciado com sucesso!")
        print("🌐 Backend: http://localhost:8000")
        print("🌐 Frontend: http://localhost:3000")
        print("📚 Docs: http://localhost:8000/docs")
        print("\n🔑 Credenciais: admin / admin123")
        print("\n🛑 Para parar: Ctrl+C")
        
        webbrowser.open("http://localhost:3000")
        
        # Aguardar interrupção
        try:
            backend_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Parando serviços...")
            backend_process.terminate()
            frontend_process.terminate()
            print("✅ Serviços parados!")
    
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()
