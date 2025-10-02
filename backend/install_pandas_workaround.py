import subprocess
import sys
import os

def install_pandas_workaround():
    """Instala pandas com workaround para Python 3.13"""
    
    print("🔧 Instalando pandas com workaround para Python 3.13...")
    
    # Primeiro, instalar numpy pré-compilado
    try:
        print("1. Instalando numpy pré-compilado...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "--only-binary=all", "--upgrade", "numpy"
        ])
        print("✅ numpy instalado")
    except subprocess.CalledProcessError:
        print("⚠️ Falha ao instalar numpy, tentando versão específica...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "numpy==1.26.4"
            ])
            print("✅ numpy 1.26.4 instalado")
        except subprocess.CalledProcessError as e:
            print(f"❌ Falha ao instalar numpy: {e}")
    
    # Instalar pandas pré-compilado
    try:
        print("2. Instalando pandas pré-compilado...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "--only-binary=all", "pandas"
        ])
        print("✅ pandas instalado")
    except subprocess.CalledProcessError:
        print("⚠️ Falha ao instalar pandas, tentando versão específica...")
        try:
            # Tentar versão mais recente disponível para Python 3.13
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "--pre", "pandas"
            ])
            print("✅ pandas (versão preview) instalado")
        except subprocess.CalledProcessError as e:
            print(f"❌ Falha ao instalar pandas: {e}")
            print("💡 Considere usar Python 3.11 ou Docker")
            return False
    
    # Opcional: instalar psycopg2 se necessário
    try:
        print("3. Instalando psycopg2-binary (opcional)...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "psycopg2-binary==2.9.9"
        ])
        print("✅ psycopg2-binary instalado")
    except subprocess.CalledProcessError:
        print("⚠️ psycopg2-binary falhou (não é crítico para SQLite)")
    
    return True

if __name__ == "__main__":
    install_pandas_workaround()
