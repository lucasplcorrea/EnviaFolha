"""
Script alternativo para executar o servidor
"""
import sys
import os

def main():
    print("🚀 Iniciando Sistema RH...")
    print(f"🐍 Python {sys.version}")
    
    # Verificar se estamos no diretório correto
    if not os.path.exists("simple_main.py"):
        print("❌ Arquivo simple_main.py não encontrado!")
        print("💡 Execute este script na pasta backend/")
        return
    
    # Tentar importar uvicorn
    try:
        import uvicorn
        print("✅ uvicorn encontrado")
    except ImportError:
        print("❌ uvicorn não encontrado!")
        print("💡 Execute: pip install uvicorn[standard]")
        return
    
    # Tentar importar fastapi
    try:
        import fastapi
        print("✅ FastAPI encontrado")
    except ImportError:
        print("❌ FastAPI não encontrado!")
        print("💡 Execute: pip install fastapi")
        return
    
    print("\n🔥 Iniciando servidor na porta 8000...")
    print("📡 Acesse: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("🛑 Para parar: Ctrl+C\n")
    
    try:
        # Executar servidor
        uvicorn.run(
            "simple_main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Servidor parado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")

if __name__ == "__main__":
    main()
