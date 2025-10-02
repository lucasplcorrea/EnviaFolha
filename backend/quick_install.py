import subprocess
import sys

def quick_install():
    """Instalação rápida das dependências essenciais"""
    
    print("🚀 Instalação rápida para Python 3.13...")
    
    # Pacotes que funcionam bem no Python 3.13
    packages = [
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0", 
        "sqlalchemy==2.0.23",
        "pydantic==2.5.0",
        "pydantic-settings==2.1.0",
        "python-multipart==0.0.6",
        "python-dotenv==1.0.0",
        "requests==2.31.0",
        "python-dateutil==2.8.2",
        "email-validator==2.1.0",
    ]
    
    # Pacotes que podem precisar de tratamento especial
    optional_packages = [
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "PyPDF2==3.0.1",
        "openpyxl==3.1.2",
        "phonenumbers==8.13.26",
        "aiofiles==23.2.1",
        "alembic==1.13.1",
    ]
    
    print("📦 Instalando pacotes essenciais...")
    for package in packages:
        try:
            print(f"  Instalando {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"  ✅ {package} instalado")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Falha ao instalar {package}: {e}")
    
    print("\n📦 Instalando pacotes opcionais...")
    for package in optional_packages:
        try:
            print(f"  Instalando {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"  ✅ {package} instalado")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️ Falha ao instalar {package} (não crítico): {e}")
    
    print("\n✅ Instalação concluída!")
    print("\n🔍 Testando importações...")
    
    # Testar importações
    test_imports = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "uvicorn"),
        ("sqlalchemy", "SQLAlchemy"),
        ("pydantic", "pydantic"),
        ("requests", "requests"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
    ]
    
    for module, name in test_imports:
        try:
            __import__(module)
            print(f"  ✅ {name} importado com sucesso")
        except ImportError:
            print(f"  ❌ {name} não disponível")

if __name__ == "__main__":
    quick_install()
