"""
Script de migração para simplificar o sistema de permissões
Remove tabelas complexas de permissões e mantém apenas roles com páginas
"""

import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.role_simple import Role, DEFAULT_ROLES
from app.models.base import Base
import json

def migrate_to_simple_permissions():
    """Migra o banco para o sistema simplificado de permissões"""
    
    # Configurar conexão
    database_url = settings.DATABASE_URL
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🔄 Iniciando migração para sistema simplificado...")
        
        # 1. Remover tabelas antigas de permissões (se existirem)
        print("🗑️  Removendo tabelas antigas de permissões...")
        
        # Remover constraints e tabelas relacionadas
        session.execute(text("DROP TABLE IF EXISTS user_permissions CASCADE;"))
        session.execute(text("DROP TABLE IF EXISTS role_permissions CASCADE;"))
        session.execute(text("DROP TABLE IF EXISTS permissions CASCADE;"))
        
        # 2. Recriar tabela roles com nova estrutura
        print("🔄 Recriando tabela roles...")
        session.execute(text("DROP TABLE IF EXISTS roles CASCADE;"))
        session.commit()
        
        # Criar tabela roles com SQL direto
        create_roles_sql = """
        CREATE TABLE roles (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description VARCHAR(255),
            is_active BOOLEAN DEFAULT true,
            allowed_pages TEXT NOT NULL DEFAULT '[]',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE
        );
        """
        session.execute(text(create_roles_sql))
        session.commit()
        
        # 3. Criar todas as outras tabelas
        Base.metadata.create_all(engine)
        session.commit()
        
        # 4. Inserir roles padrão usando SQL direto
        print("➕ Inserindo roles padrão...")
        for role_data in DEFAULT_ROLES:
            insert_sql = """
            INSERT INTO roles (name, description, allowed_pages) 
            VALUES (:name, :description, :allowed_pages)
            """
            session.execute(text(insert_sql), {
                'name': role_data['name'],
                'description': role_data['description'],
                'allowed_pages': json.dumps(role_data['allowed_pages'])
            })
        session.commit()
        
        # 5. Atualizar usuários existentes para ter role padrão
        print("👥 Atualizando usuários existentes...")
        
        # Buscar IDs dos roles
        admin_role_result = session.execute(text("SELECT id FROM roles WHERE name = 'admin'")).fetchone()
        viewer_role_result = session.execute(text("SELECT id FROM roles WHERE name = 'viewer'")).fetchone()
        
        if admin_role_result:
            admin_role_id = admin_role_result[0]
            # Atualizar usuários admin
            session.execute(text(
                "UPDATE users SET role_id = :role_id WHERE is_admin = true"
            ), {'role_id': admin_role_id})
            
            if viewer_role_result:
                viewer_role_id = viewer_role_result[0]
                # Usuários não-admin recebem role viewer por padrão
                session.execute(text(
                    "UPDATE users SET role_id = :role_id WHERE is_admin = false AND role_id IS NULL"
                ), {'role_id': viewer_role_id})
        session.commit()
        print("✅ Migração concluída com sucesso!")
        
        # Exibir roles criados
        roles_result = session.execute(text("SELECT name, description, allowed_pages FROM roles")).fetchall()
        print(f"\n📋 Roles criados ({len(roles_result)}):")
        for role_row in roles_result:
            name, description, allowed_pages = role_row
            pages = json.loads(allowed_pages)
            print(f"  • {name}: {description}")
            print(f"    Páginas: {', '.join(pages)}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Erro na migração: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate_to_simple_permissions()