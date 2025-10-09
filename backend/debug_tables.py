#!/usr/bin/env python3
"""
Debug PostgreSQL - verificar estrutura das tabelas
"""
import psycopg2
from psycopg2.extras import RealDictCursor

def debug_tables():
    """Debug das tabelas PostgreSQL"""
    try:
        # Configurações de conexão
        db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'enviafolha_db',
            'user': 'enviafolha_user',
            'password': 'secure_password'
        }
        
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔍 Verificando estrutura das tabelas...")
        
        # Listar todas as tabelas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print(f"📋 Tabelas encontradas: {[t['table_name'] for t in tables]}")
        
        # Verificar estrutura da tabela users
        print("\n👤 Estrutura da tabela 'users':")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        
        # Verificar estrutura da tabela employees
        print("\n👥 Estrutura da tabela 'employees':")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'employees'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        
        # Testar inserção simples
        print("\n🧪 Testando inserção de usuário...")
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, is_admin, is_active)
                VALUES ('test_user', 'test@test.com', 'hashed_password', 'Usuário Teste', false, true)
                RETURNING id, username
            """)
            result = cursor.fetchone()
            print(f"✅ Usuário criado: ID {result['id']}, username: {result['username']}")
            
            # Limpar teste
            cursor.execute("DELETE FROM users WHERE username = 'test_user'")
            print("🧹 Usuário de teste removido")
            
        except Exception as e:
            print(f"❌ Erro na inserção: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no debug: {e}")
        return False

if __name__ == "__main__":
    debug_tables()