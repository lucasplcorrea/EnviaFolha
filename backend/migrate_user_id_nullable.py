#!/usr/bin/env python3
"""
Migração: Alterar user_id para nullable em communication_sends
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

print("🔧 Aplicando migração: user_id nullable em communication_sends")

try:
    with engine.connect() as conn:
        # Alterar coluna user_id para nullable
        conn.execute(text("""
            ALTER TABLE communication_sends 
            ALTER COLUMN user_id DROP NOT NULL;
        """))
        conn.commit()
        
        print("✅ Migração aplicada com sucesso!")
        print("   • communication_sends.user_id agora permite NULL")
        
except Exception as e:
    print(f"❌ Erro ao aplicar migração: {e}")
    import traceback
    traceback.print_exc()
