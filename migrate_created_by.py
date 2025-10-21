"""
Script para permitir NULL no campo created_by da tabela employees.
Isso permite importações sem necessidade de usuário autenticado.
"""
from sqlalchemy import create_engine, text

# Conectar ao banco
engine = create_engine('postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db')

with engine.connect() as conn:
    try:
        print("🔧 Alterando coluna created_by para permitir NULL...")
        
        # Alterar coluna para permitir NULL
        conn.execute(text("""
            ALTER TABLE employees 
            ALTER COLUMN created_by DROP NOT NULL;
        """))
        
        conn.commit()
        print("✅ Coluna created_by agora permite NULL!")
        print("📝 Colaboradores podem ser criados sem created_by.")
        
    except Exception as e:
        print(f"❌ Erro ao alterar tabela: {e}")
        conn.rollback()
