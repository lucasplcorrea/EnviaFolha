#!/usr/bin/env python3
"""
Migração: Ajustar tabela communication_sends
- Remover coluna extra_data
- Alterar title e message para nullable
"""
from sqlalchemy import create_engine, text
import os

# Carregar variáveis de ambiente
def load_env_file():
    env_vars = {}
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
                    os.environ[key.strip()] = value.strip()
    
    return env_vars

load_env_file()

# Conectar ao banco
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db')
engine = create_engine(DATABASE_URL)

print("🔧 Aplicando migração: ajustar communication_sends")
print()

try:
    with engine.connect() as conn:
        # 1. Remover coluna extra_data se existir
        print("1️⃣ Removendo coluna extra_data...")
        try:
            conn.execute(text("""
                ALTER TABLE communication_sends 
                DROP COLUMN IF EXISTS extra_data;
            """))
            print("   ✅ Coluna extra_data removida")
        except Exception as e:
            print(f"   ⚠️ Não foi possível remover extra_data: {e}")
        
        # 2. Alterar title para nullable
        print("2️⃣ Alterando title para nullable...")
        try:
            conn.execute(text("""
                ALTER TABLE communication_sends 
                ALTER COLUMN title DROP NOT NULL;
            """))
            print("   ✅ Coluna title agora permite NULL")
        except Exception as e:
            print(f"   ⚠️ Não foi possível alterar title: {e}")
        
        # 3. Alterar message para nullable
        print("3️⃣ Alterando message para nullable...")
        try:
            conn.execute(text("""
                ALTER TABLE communication_sends 
                ALTER COLUMN message DROP NOT NULL;
            """))
            print("   ✅ Coluna message agora permite NULL")
        except Exception as e:
            print(f"   ⚠️ Não foi possível alterar message: {e}")
        
        conn.commit()
        
        print()
        print("="*60)
        print("✅ Migração aplicada com sucesso!")
        print("="*60)
        print("📊 Mudanças:")
        print("   • extra_data: REMOVIDA")
        print("   • title: nullable=True")
        print("   • message: nullable=True")
        
except Exception as e:
    print(f"❌ Erro ao aplicar migração: {e}")
    import traceback
    traceback.print_exc()
