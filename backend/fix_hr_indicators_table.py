#!/usr/bin/env python3
"""
Script para corrigir tipos de colunas da tabela hr_indicator_snapshots
Uso: python fix_hr_indicators_table.py
"""
import os
import sys
from sqlalchemy import create_engine, text

def get_database_url():
    """Constrói URL do banco a partir das variáveis de ambiente"""
    # DEBUG: Mostrar o que está no ambiente
    import sys
    print(f"🔍 DEBUG - DATABASE_URL do ambiente: {os.getenv('DATABASE_URL')}", file=sys.stderr)
    print(f"🔍 DEBUG - DATABASE_TYPE do ambiente: {os.getenv('DATABASE_TYPE')}", file=sys.stderr)
    
    # Primeiro: tentar ler DATABASE_URL diretamente do ambiente (Docker)
    # IMPORTANTE: Ler ANTES do load_dotenv() para não sobrescrever
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        print(f"📌 DATABASE_URL detectada do ambiente: {db_url.split('@')[0]}@***")
        return db_url
    
    # Segundo: tentar carregar do .env (desenvolvimento local)
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)  # NÃO sobrescreve variáveis existentes
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            print(f"📌 DATABASE_URL carregada do .env")
            return db_url
    except ImportError:
        pass
    
    # Terceiro: construir manualmente
    db_type = os.getenv('DATABASE_TYPE', 'sqlite')
    print(f"📌 Construindo URL manualmente. DATABASE_TYPE={db_type}")
    
    if db_type == 'sqlite':
        db_path = os.getenv('DATABASE_PATH', './nexo_rh.db')
        return f'sqlite:///{db_path}'
    else:  # postgresql
        user = os.getenv('POSTGRES_USER', 'nexo_rh')
        password = os.getenv('POSTGRES_PASSWORD', '')
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'nexo_rh_db')
        return f'postgresql://{user}:{password}@{host}:{port}/{database}'

def fix_hr_indicators_table():
    """Corrige os tipos de colunas da tabela hr_indicator_snapshots"""
    
    db_url = get_database_url()
    
    # Debug: mostrar o tipo de banco detectado
    if 'postgresql' in db_url:
        print(f"🔧 Conectando ao PostgreSQL: {db_url.split('@')[-1]}")
    else:
        print(f"🔧 Conectando ao banco: {db_url}")
    
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as conn:
            # Verificar se é PostgreSQL
            if 'postgresql' not in db_url:
                print("⚠️  Este script é necessário apenas para PostgreSQL")
                print("✅ SQLite não precisa de correção")
                return
            
            print("\n📋 Executando migração...")
            
            # 1. Dropar tabela existente (está vazia)
            print("  1️⃣  Dropando tabela hr_indicator_snapshots...")
            conn.execute(text("DROP TABLE IF EXISTS hr_indicator_snapshots CASCADE"))
            conn.commit()
            
            # 2. Recriar tabela com tipos corretos
            print("  2️⃣  Recriando tabela com tipos corretos...")
            conn.execute(text("""
                CREATE TABLE hr_indicator_snapshots (
                    id SERIAL PRIMARY KEY,
                    
                    -- Identificação do snapshot
                    indicator_type VARCHAR(50) NOT NULL,
                    calculation_date DATE NOT NULL,
                    period_start DATE,
                    period_end DATE,
                    
                    -- Dados agregados (JSON flexível)
                    metrics JSONB NOT NULL,
                    
                    -- Metadados
                    total_records INTEGER,
                    calculation_time_ms INTEGER,
                    is_valid INTEGER DEFAULT 1,
                    
                    -- Timestamps (CORRETO: TIMESTAMP, não VARCHAR!)
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            
            # 3. Criar índices
            print("  3️⃣  Criando índices...")
            indices = [
                "CREATE INDEX idx_hr_indicator_type ON hr_indicator_snapshots(indicator_type)",
                "CREATE INDEX idx_hr_indicator_date ON hr_indicator_snapshots(calculation_date)",
                "CREATE INDEX idx_hr_indicator_created ON hr_indicator_snapshots(created_at)",
                "CREATE INDEX idx_type_date ON hr_indicator_snapshots(indicator_type, calculation_date)",
                "CREATE INDEX idx_type_period ON hr_indicator_snapshots(indicator_type, period_start, period_end)"
            ]
            
            for idx_sql in indices:
                conn.execute(text(idx_sql))
            conn.commit()
            
            # 4. Criar trigger para updated_at
            print("  4️⃣  Criando trigger para updated_at...")
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """))
            conn.commit()
            
            conn.execute(text("""
                CREATE TRIGGER update_hr_indicator_snapshots_updated_at 
                    BEFORE UPDATE ON hr_indicator_snapshots 
                    FOR EACH ROW 
                    EXECUTE FUNCTION update_updated_at_column()
            """))
            conn.commit()
            
            print("\n✅ Migração concluída com sucesso!")
            print("\n📊 Estrutura da tabela corrigida:")
            print("   - created_at: TIMESTAMP (antes: VARCHAR)")
            print("   - updated_at: TIMESTAMP (antes: VARCHAR)")
            print("   - Todos os índices recriados")
            print("   - Trigger de updated_at configurado")
            
    except Exception as e:
        print(f"\n❌ Erro durante migração: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        engine.dispose()

if __name__ == '__main__':
    print("=" * 60)
    print("🔧 Correção de Tipos - hr_indicator_snapshots")
    print("=" * 60)
    
    fix_hr_indicators_table()
    
    print("\n" + "=" * 60)
    print("✅ Processo finalizado!")
    print("=" * 60)
