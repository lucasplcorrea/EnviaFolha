"""Criar tabela hr_indicator_snapshots"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.models.hr_indicators import HRIndicatorSnapshot
from app.models.base import Base

def create_hr_indicators_table():
    """Cria tabela de snapshots de indicadores"""
    try:
        engine = create_engine(settings.DATABASE_URL, echo=True)
        
        print("📊 Criando tabela hr_indicator_snapshots...")
        
        # Criar apenas a tabela de indicadores
        HRIndicatorSnapshot.__table__.create(engine, checkfirst=True)
        
        print("✅ Tabela hr_indicator_snapshots criada com sucesso!")
        
        # Verificar se foi criada
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'hr_indicator_snapshots'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            
            print("\n📋 Colunas da tabela hr_indicator_snapshots:")
            for column in columns:
                print(f"  - {column[0]} ({column[1]})")
        
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_hr_indicators_table()
