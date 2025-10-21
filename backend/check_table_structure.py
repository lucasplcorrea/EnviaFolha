"""
Script para verificar a estrutura da tabela employees e comparar com o modelo
"""
import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, text
from app.core.config import Settings

def check_table_structure():
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL)
    
    print("📊 Verificando estrutura da tabela employees...\n")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    column_name, 
                    data_type, 
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns 
                WHERE table_name = 'employees'
                ORDER BY ordinal_position;
            """))
            
            print(f"{'Campo':<25} {'Tipo':<20} {'Tamanho':<10} {'Nullable':<10}")
            print("=" * 75)
            
            for row in result:
                col_name = row[0]
                data_type = row[1]
                max_length = row[2] if row[2] else '-'
                nullable = row[3]
                
                print(f"{col_name:<25} {data_type:<20} {str(max_length):<10} {nullable:<10}")
            
    except Exception as e:
        print(f"❌ Erro ao verificar tabela: {e}")
        return False
    
    print("\n✅ Verificação concluída!")
    return True

if __name__ == "__main__":
    check_table_structure()
