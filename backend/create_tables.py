#!/usr/bin/env python3
"""Script para criar tabelas faltantes"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.models.base import Base

def create_missing_tables():
    try:
        engine = create_engine(settings.DATABASE_URL, echo=True)
        
        # Criar todas as tabelas definidas nos modelos
        Base.metadata.create_all(engine)
        
        print("✅ Todas as tabelas foram criadas/verificadas")
        
        # Verificar se as tabelas existem agora
        with engine.connect() as conn:
            tables = ["users", "roles", "permissions", "role_permissions", "user_permissions"]
            for table in tables:
                result = conn.execute(text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}');"))
                exists = result.fetchone()[0]
                status = "✅" if exists else "❌"
                print(f"{status} Tabela '{table}': {'Existe' if exists else 'Não existe'}")
                
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    create_missing_tables()