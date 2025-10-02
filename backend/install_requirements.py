import subprocess
import sys
import os

def install_requirements():
    """Script para instalar dependências compatíveis com Python 3.13"""
    
    print(f"Python version: {sys.version}")
    
    # Lista de pacotes com versões específicas para Python 3.13
    packages = [
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0",
        "sqlalchemy==2.0.23",
        "alembic==1.13.1",
        "pydantic==2.5.0",
        "pydantic-settings==2.1.0",
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "python-multipart==0.0.6",
        "python-dotenv==1.0.0",
        "requests==2.31.0",
        "PyPDF2==3.0.1",
        "openpyxl==3.1.2",
        "phonenumbers==8.13.26",
        "aiofiles==23.2.1",
        "python-dateutil==2.8.2",
        "email-validator==2.1.0",
    ]
    
    # Pacotes que podem precisar de versões específicas para Python 3.13
    python_313_packages = [
        # Usar versão de desenvolvimento do pandas se necessário
        "pandas>=2.2.0",
        # Alternativa: instalar do conda-forge se disponível
        # "pandas==2.2.0rc0",
    ]
    
    # Instalar pacotes básicos primeiro
    for package in packages:
        print(f"Instalando {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} instalado com sucesso")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao instalar {package}: {e}")
    
    # Tentar instalar pandas
    for package in python_313_packages:
        print(f"Instalando {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} instalado com sucesso")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao instalar {package}: {e}")
            if "pandas" in package:
                print("⚠️  Tentando instalação alternativa do pandas...")
                # Tentar instalar versão de desenvolvimento
                try:
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", 
                        "--pre", "--extra-index-url", 
                        "https://pypi.anaconda.org/scientific-python-nightly-wheels/simple",
                        "pandas"
                    ])
                    print("✅ Pandas instalado da versão de desenvolvimento")
                except subprocess.CalledProcessError:
                    print("❌ Falha na instalação alternativa do pandas")
                    print("💡 Considere usar Python 3.11 ou criar ambiente conda")
    
    # Verificar se psycopg2 é necessário (apenas se usar PostgreSQL)
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary==2.9.9"])
        print("✅ psycopg2-binary instalado")
    except subprocess.CalledProcessError:
        print("⚠️  psycopg2-binary falhou, mas não é crítico se usar SQLite")

if __name__ == "__main__":
    install_requirements()
