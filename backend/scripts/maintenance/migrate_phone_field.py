"""
Script de migração para corrigir o tamanho do campo phone na tabela employees
"""
from common import ensure_backend_on_path, get_database_url

ensure_backend_on_path()

from sqlalchemy import create_engine, text

def migrate_phone_field():
    engine = create_engine(get_database_url())
    
    print("🔄 Iniciando migração do campo phone...")
    
    try:
        with engine.connect() as conn:
            # Altera o tamanho do campo phone de VARCHAR(11) para VARCHAR(20)
            conn.execute(text("ALTER TABLE employees ALTER COLUMN phone TYPE VARCHAR(20);"))
            conn.commit()
            print("✅ Campo phone alterado de VARCHAR(11) para VARCHAR(20)")
            
            # Verifica a alteração
            result = conn.execute(text("""
                SELECT column_name, data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'employees' AND column_name = 'phone';
            """))
            row = result.fetchone()
            if row:
                print(f"📊 Verificação: {row[0]} | {row[1]}({row[2]})")
            
    except Exception as e:
        print(f"❌ Erro ao migrar: {e}")
        return False
    
    print("✅ Migração concluída com sucesso!")
    return True

if __name__ == "__main__":
    migrate_phone_field()
