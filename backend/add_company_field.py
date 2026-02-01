"""
Adiciona campo company à tabela payroll_periods
"""
from sqlalchemy import text
from main_legacy import db_engine

def add_company_field():
    """Adiciona campo company se não existir"""
    if not db_engine:
        print("❌ Engine de banco de dados não disponível")
        return
        
    with db_engine.connect() as conn:
        # Verifica se a coluna já existe
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='payroll_periods' AND column_name='company'
        """))
        
        if result.fetchone() is None:
            print("➕ Adicionando coluna 'company' à tabela payroll_periods...")
            conn.execute(text("""
                ALTER TABLE payroll_periods 
                ADD COLUMN company VARCHAR(50) DEFAULT '0060'
            """))
            conn.commit()
            print("✅ Coluna 'company' adicionada com sucesso!")
            
            # Atualizar períodos existentes baseado no padrão de matrículas
            print("🔄 Atualizando períodos existentes...")
            conn.execute(text("""
                UPDATE payroll_periods pp
                SET company = CASE 
                    WHEN EXISTS (
                        SELECT 1 FROM payroll_data pd
                        INNER JOIN employees e ON e.id = pd.employee_id
                        WHERE pd.period_id = pp.id 
                        AND e.unique_id LIKE '0059%'
                        LIMIT 1
                    ) THEN '0059'
                    ELSE '0060'
                END
            """))
            conn.commit()
            print("✅ Períodos atualizados!")
        else:
            print("ℹ️  Coluna 'company' já existe")

if __name__ == "__main__":
    add_company_field()
    print("\n🎉 Migração concluída!")
