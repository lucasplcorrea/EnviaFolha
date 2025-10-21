#!/usr/bin/env python3
"""Script para inserir dados padrão no sistema de usuários"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.permission import Permission, Role, RolePermission
from app.models.user import User
from app.core.auth import get_password_hash

def create_default_data():
    try:
        engine = create_engine(settings.DATABASE_URL, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("🚀 Criando dados padrão do sistema...")
        
        # 1. Criar permissões padrão
        permissions_data = [
            # Módulo Colaboradores
            {"name": "employees_view", "description": "Visualizar colaboradores", "module": "employees", "action": "read"},
            {"name": "employees_create", "description": "Criar colaboradores", "module": "employees", "action": "create"},
            {"name": "employees_edit", "description": "Editar colaboradores", "module": "employees", "action": "update"},
            {"name": "employees_delete", "description": "Excluir colaboradores", "module": "employees", "action": "delete"},
            {"name": "employees_bulk", "description": "Operações em lote", "module": "employees", "action": "bulk"},
            
            # Módulo Holerites
            {"name": "payroll_view", "description": "Visualizar holerites", "module": "payroll", "action": "read"},
            {"name": "payroll_send", "description": "Enviar holerites", "module": "payroll", "action": "send"},
            {"name": "payroll_process", "description": "Processar dados de folha", "module": "payroll", "action": "process"},
            
            # Módulo Comunicados
            {"name": "communications_view", "description": "Visualizar comunicados", "module": "communications", "action": "read"},
            {"name": "communications_send", "description": "Enviar comunicados", "module": "communications", "action": "send"},
            
            # Módulo Relatórios
            {"name": "reports_view", "description": "Visualizar relatórios", "module": "reports", "action": "read"},
            {"name": "reports_export", "description": "Exportar relatórios", "module": "reports", "action": "export"},
            
            # Módulo Configurações
            {"name": "settings_view", "description": "Visualizar configurações", "module": "settings", "action": "read"},
            {"name": "settings_edit", "description": "Editar configurações", "module": "settings", "action": "update"},
            
            # Módulo Usuários
            {"name": "users_view", "description": "Visualizar usuários", "module": "users", "action": "read"},
            {"name": "users_create", "description": "Criar usuários", "module": "users", "action": "create"},
            {"name": "users_edit", "description": "Editar usuários", "module": "users", "action": "update"},
            {"name": "users_delete", "description": "Excluir usuários", "module": "users", "action": "delete"},
            
            # Módulo Sistema
            {"name": "system_admin", "description": "Administração do sistema", "module": "system", "action": "admin"}
        ]
        
        created_permissions = []
        for perm_data in permissions_data:
            existing = db.query(Permission).filter_by(name=perm_data["name"]).first()
            if not existing:
                permission = Permission(**perm_data)
                db.add(permission)
                created_permissions.append(perm_data["name"])
        
        db.commit()
        print(f"✅ Criadas {len(created_permissions)} permissões")
        
        # 2. Criar papéis padrão
        roles_data = [
            {
                "name": "admin",
                "description": "Administrador do sistema - acesso total",
                "permissions": [p["name"] for p in permissions_data]  # Todas as permissões
            },
            {
                "name": "manager",
                "description": "Gestor - pode gerenciar colaboradores e envios",
                "permissions": [
                    "employees_view", "employees_create", "employees_edit", "employees_bulk",
                    "payroll_view", "payroll_send", "payroll_process",
                    "communications_view", "communications_send",
                    "reports_view", "reports_export",
                    "settings_view"
                ]
            },
            {
                "name": "operator",
                "description": "Operador - pode enviar holerites e comunicados",
                "permissions": [
                    "employees_view",
                    "payroll_view", "payroll_send",
                    "communications_view", "communications_send",
                    "reports_view"
                ]
            },
            {
                "name": "viewer",
                "description": "Visualizador - apenas leitura",
                "permissions": [
                    "employees_view",
                    "payroll_view",
                    "communications_view",
                    "reports_view"
                ]
            }
        ]
        
        created_roles = []
        for role_data in roles_data:
            existing = db.query(Role).filter_by(name=role_data["name"]).first()
            if not existing:
                role = Role(
                    name=role_data["name"],
                    description=role_data["description"]
                )
                db.add(role)
                db.flush()  # Para obter o ID
                
                # Associar permissões ao papel
                for perm_name in role_data["permissions"]:
                    permission = db.query(Permission).filter_by(name=perm_name).first()
                    if permission:
                        role_perm = RolePermission(role_id=role.id, permission_id=permission.id)
                        db.add(role_perm)
                
                created_roles.append(role_data["name"])
        
        db.commit()
        print(f"✅ Criados {len(created_roles)} papéis")
        
        # 3. Criar usuário administrador padrão se não existir
        admin_user = db.query(User).filter_by(username="admin").first()
        if not admin_user:
            admin_role = db.query(Role).filter_by(name="admin").first()
            admin_user = User(
                username="admin",
                email="admin@sistema.com",
                full_name="Administrador do Sistema",
                password_hash=get_password_hash("admin123"),
                is_active=True,
                is_admin=True,
                role_id=admin_role.id if admin_role else None
            )
            db.add(admin_user)
            db.commit()
            print("✅ Criado usuário administrador padrão")
            print("   📧 Email: admin@sistema.com")
            print("   🔑 Senha: admin123")
        else:
            print("ℹ️  Usuário administrador já existe")
        
        print("\n🎉 Dados padrão criados com sucesso!")
        print("\n📋 Resumo:")
        print(f"   • Permissões: {len(permissions_data)}")
        print(f"   • Papéis: {len(roles_data)}")
        print("   • Usuário admin: ✅")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()

if __name__ == "__main__":
    create_default_data()