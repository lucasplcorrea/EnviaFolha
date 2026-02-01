"""
Script para verificar e corrigir a tabela payroll_processing_logs
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal, engine
from app.models.payroll import PayrollProcessingLog
from sqlalchemy import text, inspect

def check_and_fix_table():
    """Verifica e cria a tabela se necessário"""
    
    print("=" * 80)
    print("🔍 VERIFICANDO TABELA payroll_processing_logs")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        # Verificar se a tabela existe
        inspector = inspect(engine)
        table_exists = 'payroll_processing_logs' in inspector.get_table_names()
        
        if not table_exists:
            print("\n❌ Tabela payroll_processing_logs não existe!")
            print("📝 Criando tabela...")
            
            from app.models import Base
            Base.metadata.create_all(bind=engine)
            
            print("✅ Tabela criada com sucesso!")
        else:
            print("\n✅ Tabela payroll_processing_logs existe")
        
        # Verificar quantidade de registros
        result = db.execute(text("""
            SELECT COUNT(*) FROM payroll_processing_logs
        """)).fetchone()
        
        count = result[0] if result else 0
        print(f"\n📊 Total de registros: {count}")
        
        if count > 0:
            # Mostrar últimos 5 registros
            result = db.execute(text("""
                SELECT 
                    filename, 
                    status, 
                    processed_rows, 
                    error_rows,
                    created_at
                FROM payroll_processing_logs
                ORDER BY created_at DESC
                LIMIT 5
            """))
            
            print("\n📋 Últimos 5 registros:")
            for row in result:
                print(f"   • {row[0]} - {row[1]} - {row[2]} processados - {row[3]} erros - {row[4]}")
        else:
            print("\n⚠️ Nenhum registro encontrado na tabela")
            print("   Isso é normal se você ainda não processou nenhum CSV com o novo sistema")
        
        # Verificar colunas
        columns = [col['name'] for col in inspector.get_columns('payroll_processing_logs')]
        print(f"\n📝 Colunas da tabela: {', '.join(columns)}")
        
        print("\n" + "=" * 80)
        print("✅ Verificação concluída!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Erro durante verificação: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_and_fix_table()
