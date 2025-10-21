#!/usr/bin/env python3
"""Script para verificar estrutura do banco de dados"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_users_table():
    try:
        engine = create_engine(settings.DATABASE_URL, echo=False)
        
        with engine.connect() as conn:
            # Verificar colunas da tabela users
            result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position;"))
            columns = result.fetchall()
            
            print("📋 Colunas da tabela 'users':")
            for column in columns:
                print(f"  - {column[0]} ({column[1]})")
                
            # Verificar se existe a tabela roles
            result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'roles');"))
            roles_exists = result.fetchone()[0]
            print(f"\n📊 Tabela 'roles' existe: {'✅ Sim' if roles_exists else '❌ Não'}")
            
            if roles_exists:
                result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'roles' ORDER BY ordinal_position;"))
                columns = result.fetchall()
                print("📋 Colunas da tabela 'roles':")
                for column in columns:
                    print(f"  - {column[0]} ({column[1]})")
                    
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    check_users_table()