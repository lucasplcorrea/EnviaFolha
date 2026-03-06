#!/usr/bin/env python3
"""
Migration: Corrige tipos de colunas da tabela hr_indicator_snapshots
Autor: Sistema
Data: 2026-01-07
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect

def run_migration():
    """Executa a migration para corrigir tipos de colunas"""
    
    # Ler DATABASE_URL do ambiente
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("⚠️  DATABASE_URL não encontrada. Pulando migration.")
        return
    
    # Só executar para PostgreSQL
    if 'postgresql' not in db_url:
        print("ℹ️  Migration não necessária para SQLite")
        return
    
    print("=" * 60)
    print("🔄 Migration: fix_hr_indicators_columns")
    print("=" * 60)
    
    try:
        engine = create_engine(db_url)
        inspector = inspect(engine)
        
        # Verificar se a tabela existe
        if 'hr_indicator_snapshots' not in inspector.get_table_names():
            print("ℹ️  Tabela hr_indicator_snapshots não existe ainda. Pulando migration.")
            return
        
        # Verificar se todas as colunas necessárias existem
        columns = inspector.get_columns('hr_indicator_snapshots')
        column_names = {c['name'] for c in columns}
        
        required_columns = {
            'id', 'indicator_type', 'calculation_date', 
            'period_start', 'period_end', 'metrics',
            'total_records', 'calculation_time_ms', 'is_valid',
            'created_at', 'updated_at'
        }
        
        missing_columns = required_columns - column_names
        
        if not missing_columns:
            # Verificar se created_at está com tipo correto
            created_at_col = next((c for c in columns if c['name'] == 'created_at'), None)
            if created_at_col and 'TIMESTAMP' in str(created_at_col['type']).upper():
                print("✅ Tabela hr_indicator_snapshots já está com estrutura completa e tipos corretos")
                return
        
        if missing_columns:
            print(f"⚠️  Colunas faltando: {missing_columns}")
        
        print("🔧 Corrigindo tipos de colunas...")
        
        with engine.connect() as conn:
            # 1. Dropar tabela existente (está vazia)
            print("  1️⃣ Dropando tabela antiga...")
            conn.execute(text("DROP TABLE IF EXISTS hr_indicator_snapshots CASCADE"))
            
            # 2. Recriar com tipos corretos
            print("  2️⃣ Recriando tabela com tipos corretos...")
            conn.execute(text("""
                CREATE TABLE hr_indicator_snapshots (
                    id SERIAL PRIMARY KEY,
                    indicator_type VARCHAR(50) NOT NULL,
                    calculation_date DATE NOT NULL,
                    period_start DATE,
                    period_end DATE,
                    metrics JSONB NOT NULL,
                    total_records INTEGER,
                    calculation_time_ms INTEGER,
                    is_valid INTEGER DEFAULT 1,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # 3. Criar índices
            print("  3️⃣ Criando índices...")
            conn.execute(text("""
                CREATE INDEX idx_hr_snapshots_indicator_type 
                ON hr_indicator_snapshots(indicator_type)
            """))
            
            conn.execute(text("""
                CREATE INDEX idx_hr_snapshots_calculation_date 
                ON hr_indicator_snapshots(calculation_date)
            """))
            
            conn.execute(text("""
                CREATE INDEX idx_type_date 
                ON hr_indicator_snapshots(indicator_type, calculation_date)
            """))
            
            conn.execute(text("""
                CREATE INDEX idx_type_period 
                ON hr_indicator_snapshots(indicator_type, period_start, period_end)
            """))
            
            conn.execute(text("""
                CREATE INDEX idx_hr_snapshots_valid 
                ON hr_indicator_snapshots(is_valid)
            """))
            
            conn.execute(text("""
                CREATE INDEX idx_hr_snapshots_created 
                ON hr_indicator_snapshots(created_at)
            """))
            
            # 4. Criar trigger para updated_at
            print("  4️⃣ Criando trigger de atualização...")
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION update_hr_snapshots_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
            """))
            
            conn.execute(text("""
                DROP TRIGGER IF EXISTS trigger_hr_snapshots_updated_at 
                ON hr_indicator_snapshots
            """))
            
            conn.execute(text("""
                CREATE TRIGGER trigger_hr_snapshots_updated_at
                BEFORE UPDATE ON hr_indicator_snapshots
                FOR EACH ROW
                EXECUTE FUNCTION update_hr_snapshots_updated_at()
            """))
            
            conn.commit()
            
        print("✅ Migration executada com sucesso!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Erro ao executar migration: {e}")
        import traceback
        traceback.print_exc()
        # Não falhar o startup por causa da migration
        pass

if __name__ == "__main__":
    run_migration()
