#!/usr/bin/env python3
"""
Script para criar as tabelas de Cartão Ponto no banco de dados
"""
import sys
import os

# Adicionar o diretório backend ao path
sys.path.insert(0, os.path.dirname(__file__))

from app.models.base import Base, engine
from app.models.timecard import TimecardPeriod, TimecardData, TimecardProcessingLog

def create_timecard_tables():
    """Cria as tabelas de cartão ponto no banco de dados"""
    print("=" * 60)
    print("🔧 Criando tabelas de Cartão Ponto")
    print("=" * 60)
    
    try:
        # Importar os modelos para garantir que estejam registrados
        print(f"📋 Modelos registrados:")
        print(f"   - TimecardPeriod ({TimecardPeriod.__tablename__})")
        print(f"   - TimecardData ({TimecardData.__tablename__})")
        print(f"   - TimecardProcessingLog ({TimecardProcessingLog.__tablename__})")
        print()
        
        # Criar apenas as tabelas de timecard
        print("🔨 Criando tabelas no banco de dados...")
        TimecardPeriod.__table__.create(engine, checkfirst=True)
        TimecardData.__table__.create(engine, checkfirst=True)
        TimecardProcessingLog.__table__.create(engine, checkfirst=True)
        
        print("✅ Tabelas criadas com sucesso!")
        print()
        print("📊 Estrutura das tabelas:")
        print()
        
        # Mostrar estrutura de cada tabela
        for table_name, table in [
            ('timecard_periods', TimecardPeriod.__table__),
            ('timecard_data', TimecardData.__table__),
            ('timecard_processing_logs', TimecardProcessingLog.__table__)
        ]:
            print(f"   {table_name}:")
            for column in table.columns:
                nullable = "NULL" if column.nullable else "NOT NULL"
                pk = " PRIMARY KEY" if column.primary_key else ""
                print(f"      - {column.name}: {column.type} {nullable}{pk}")
            print()
        
        print("=" * 60)
        print("✅ Processo concluído!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_timecard_tables()
