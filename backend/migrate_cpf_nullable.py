"""
Migração para tornar o campo CPF nullable na tabela employees.
Necessário para permitir import de CSVs sem informação de CPF.
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_cpf_nullable():
    """Remove a constraint NOT NULL do campo CPF"""
    
    print("🔄 Iniciando migração: tornar CPF e Phone nullable...")
    
    # Construir connection string do .env
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        # Tentar construir manualmente
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'enviafolha')
        db_user = os.getenv('DB_USER', 'postgres')
        db_pass = os.getenv('DB_PASSWORD', '')
        
        db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Verificar status atual
        cursor.execute("""
            SELECT column_name, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'employees' AND column_name IN ('cpf', 'phone')
        """)
        
        for row in cursor.fetchall():
            print(f"   Campo {row[0]}: is_nullable = {row[1]}")
        
        # Aplicar alterações
        print("\n   Removendo constraint NOT NULL de CPF...")
        cursor.execute("ALTER TABLE employees ALTER COLUMN cpf DROP NOT NULL")
        
        print("   Removendo constraint NOT NULL de Phone...")
        cursor.execute("ALTER TABLE employees ALTER COLUMN phone DROP NOT NULL")
        
        conn.commit()
        print("\n✅ Migração concluída! CPF e Phone agora são nullable!")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro durante migração: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = migrate_cpf_nullable()
    sys.exit(0 if success else 1)
