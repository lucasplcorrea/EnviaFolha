"""
Migração: Tornar processed_by nullable em payroll_processing_logs
Data: 2026-01-19
"""

from common import ensure_backend_on_path, get_database_url

ensure_backend_on_path()

from sqlalchemy import create_engine, text

def migrate():
    """Executa a migração"""
    engine = create_engine(get_database_url())
    
    print("🔄 Iniciando migração: payroll_processing_logs.processed_by nullable")
    
    with engine.connect() as conn:
        try:
            # Tornar processed_by nullable
            print("1️⃣ Tornando coluna processed_by nullable...")
            conn.execute(text("""
                ALTER TABLE payroll_processing_logs 
                ALTER COLUMN processed_by DROP NOT NULL;
            """))
            conn.commit()
            print("✅ Coluna processed_by agora é nullable")
            
            # Atualizar registros existentes com processed_by=1 para NULL se user não existe
            print("2️⃣ Verificando registros com processed_by inválido...")
            result = conn.execute(text("""
                UPDATE payroll_processing_logs 
                SET processed_by = NULL 
                WHERE processed_by NOT IN (SELECT id FROM users);
            """))
            conn.commit()
            rows_updated = result.rowcount
            if rows_updated > 0:
                print(f"✅ {rows_updated} registro(s) atualizado(s) para processed_by=NULL")
            else:
                print("✅ Nenhum registro necessita atualização")
            
            print("✅ Migração concluída com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro na migração: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    migrate()
