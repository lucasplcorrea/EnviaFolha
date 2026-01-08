"""
Script de migração para corrigir o tamanho do campo cpf na tabela employees
"""
import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, text
from app.core.config import Settings

def migrate_cpf_field():
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL)
    
    print("🔄 Iniciando migração do campo cpf...")
    
    try:
        with engine.connect() as conn:
            # Altera o tamanho do campo cpf de VARCHAR(11) para VARCHAR(14)
            # para suportar formato com máscara: 000.000.000-00
            conn.execute(text("ALTER TABLE employees ALTER COLUMN cpf TYPE VARCHAR(14);"))
            conn.commit()
            print("✅ Campo cpf alterado de VARCHAR(11) para VARCHAR(14)")
            
            # Verifica a alteração
            result = conn.execute(text("""
                SELECT column_name, data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'employees' AND column_name = 'cpf';
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
    migrate_cpf_field()
