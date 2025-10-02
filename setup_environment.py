import subprocess
import sys
import os
import platform

def check_python_version():
    """Verifica a versão do Python"""
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor == 13:
        print("⚠️  Python 3.13 detectado - algumas bibliotecas podem ter incompatibilidades")
        return "3.13"
    elif version.major == 3 and version.minor >= 11:
        print("✅ Versão do Python compatível")
        return "compatible"
    else:
        print("❌ Python 3.11+ é necessário")
        return "incompatible"

def setup_for_python_313():
    """Configuração específica para Python 3.13"""
    print("\n🔧 Configurando ambiente para Python 3.13...")
    
    # Opções para Python 3.13
    print("\nOpções disponíveis:")
    print("1. Instalar com pip (pode ter incompatibilidades)")
    print("2. Usar pyenv para instalar Python 3.11")
    print("3. Usar conda para gerenciar dependências")
    print("4. Usar Docker (recomendado)")
    
    choice = input("\nEscolha uma opção (1-4): ").strip()
    
    if choice == "1":
        print("\n📦 Instalando dependências com pip...")
        os.system(f"{sys.executable} backend/install_requirements.py")
    
    elif choice == "2":
        print("\n🐍 Instruções para pyenv:")
        print("1. Instale pyenv: https://github.com/pyenv/pyenv")
        print("2. Execute: pyenv install 3.11.7")
        print("3. Execute: pyenv local 3.11.7")
        print("4. Execute: pip install -r backend/requirements.txt")
    
    elif choice == "3":
        print("\n🐍 Instruções para conda:")
        print("1. Instale Miniconda/Anaconda")
        print("2. Execute: conda env create -f backend/conda-requirements.yml")
        print("3. Execute: conda activate sistema-rh")
    
    elif choice == "4":
        print("\n🐳 Usando Docker (recomendado):")
        print("1. Execute: docker-compose up -d")
        print("2. Acesse: http://localhost:3000")
    
    else:
        print("Opção inválida")

def setup_for_compatible_python():
    """Configuração para Python compatível"""
    print("\n📦 Instalando dependências...")
    
    try:
        # Atualizar pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        
        # Instalar dependências do backend
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"])
        
        print("✅ Dependências do backend instaladas com sucesso!")
        
        # Verificar se Node.js está disponível para o frontend
        try:
            subprocess.check_call(["node", "--version"], stdout=subprocess.DEVNULL)
            subprocess.check_call(["npm", "--version"], stdout=subprocess.DEVNULL)
            
            print("\n📦 Instalando dependências do frontend...")
            os.chdir("frontend")
            subprocess.check_call(["npm", "install"])
            os.chdir("..")
            
            print("✅ Dependências do frontend instaladas com sucesso!")
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  Node.js não encontrado. Instale Node.js 18+ para o frontend")
            print("💡 Ou use Docker: docker-compose up -d")
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro na instalação: {e}")
        print("💡 Considere usar Docker ou conda")

def main():
    print("🚀 Configuração do Sistema de Envio RH v2.0")
    print("=" * 50)
    
    python_status = check_python_version()
    
    if python_status == "incompatible":
        print("\n❌ Por favor, instale Python 3.11 ou superior")
        return
    
    elif python_status == "3.13":
        setup_for_python_313()
    
    else:
        setup_for_compatible_python()
    
    print("\n" + "=" * 50)
    print("✅ Configuração concluída!")
    print("\n📚 Próximos passos:")
    print("1. Configure o arquivo .env com suas credenciais")
    print("2. Execute o backend: cd backend && uvicorn main:app --reload")
    print("3. Execute o frontend: cd frontend && npm start")
    print("4. Ou use Docker: docker-compose up -d")

if __name__ == "__main__":
    main()
