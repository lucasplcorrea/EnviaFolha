#!/usr/bin/env python3
"""
Teste de conexão PostgreSQL
"""
import os
import sys

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(__file__))

def test_postgresql_connection():
    """Testa conexão com PostgreSQL"""
    print("🔌 Testando conexão com PostgreSQL...")
    
    try:
        # Tentar import do psycopg2
        import psycopg2
        print("✅ psycopg2 disponível")
    except ImportError:
        print("❌ psycopg2 não instalado. Instalando...")
        os.system("python -m pip install psycopg2-binary")
        try:
            import psycopg2
            print("✅ psycopg2 instalado com sucesso")
        except ImportError:
            print("❌ Falha ao instalar psycopg2")
            return False
    
    try:
        # Configurações de conexão
        db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'enviafolha_db',
            'user': 'enviafolha_user',
            'password': 'secure_password'
        }
        
        print(f"📡 Tentando conectar em: {db_config['host']}:{db_config['port']}")
        
        # Testar conexão
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Testar query simples
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Conectado ao PostgreSQL: {version}")
        
        # Verificar se banco existe
        cursor.execute("SELECT current_database();")
        database = cursor.fetchone()[0]
        print(f"✅ Banco atual: {database}")
        
        # Listar tabelas existentes
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"📋 Tabelas existentes: {[table[0] for table in tables]}")
        else:
            print("📋 Nenhuma tabela encontrada (banco vazio)")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Erro de conexão: {e}")
        print("💡 Verifique se:")
        print("   - PostgreSQL está rodando")
        print("   - Banco 'enviafolha_db' existe")
        print("   - Usuário 'enviafolha_user' tem permissões")
        print("   - Senha está correta")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

if __name__ == "__main__":
    success = test_postgresql_connection()
    if success:
        print("\n🎉 Conexão PostgreSQL funcionando!")
        print("✅ Pronto para executar migrações")
    else:
        print("\n❌ Falha na conexão PostgreSQL")
        print("🔧 Configure o banco antes de continuar")
    
    sys.exit(0 if success else 1)