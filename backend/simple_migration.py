#!/usr/bin/env python3
"""
Migração simples de JSON para PostgreSQL
"""
import os
import sys
import json
from datetime import datetime

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(__file__))

def simple_migration():
    """Migração simplificada dos dados"""
    print("🔄 Iniciando migração JSON → PostgreSQL...")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Configurações de conexão
        db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'enviafolha_db',
            'user': 'enviafolha_user',
            'password': 'secure_password'
        }
        
        # Carregar dados JSON
        json_file = 'employees.json'
        if not os.path.exists(json_file):
            print(f"❌ Arquivo {json_file} não encontrado")
            return False
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        employees = data.get('employees', [])
        users = data.get('users', [])
        
        print(f"📊 Dados carregados: {len(users)} usuários, {len(employees)} funcionários")
        
        # Conectar ao PostgreSQL
        print("🔌 Conectando ao PostgreSQL...")
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()  # Usar cursor normal
        print("✅ Conectado ao PostgreSQL")
        
        # 1. Criar usuário admin se não existir
        print("👤 Verificando usuário admin...")
        try:
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
            admin_count = cursor.fetchone()[0]
            print(f"📊 Usuários admin encontrados: {admin_count}")
        except Exception as e:
            print(f"❌ Erro ao consultar usuários: {e}")
            raise
        
        if admin_count == 0:
            print("👤 Criando usuário administrador...")
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, is_admin, is_active)
                VALUES ('admin', 'admin@enviafolha.com', 'admin123', 'Administrador', true, true)
            """)
            # Commit do usuário admin antes de continuar
            conn.commit()
            print("✅ Usuário admin criado")
        else:
            print("✅ Usuário admin já existe")
        
        # Obter ID do usuário admin
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_user = cursor.fetchone()
        admin_id = admin_user[0] if admin_user else 1
        print(f"👤 ID do usuário admin: {admin_id}")
        
        # 2. Migrar funcionários
        migrated_count = 0
        for emp in employees:
            try:
                # Verificar se funcionário já existe
                cursor.execute("SELECT id FROM employees WHERE unique_id = %s", (emp.get('unique_id'),))
                existing = cursor.fetchone()
                
                if existing:
                    print(f"⚠️  Funcionário {emp.get('full_name')} já existe, pulando...")
                    continue
                
                # Inserir funcionário
                cursor.execute("""
                    INSERT INTO employees (unique_id, name, cpf, phone, email, department, position, is_active, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    emp.get('unique_id'),
                    emp.get('full_name'),
                    emp.get('unique_id', '000.000.000-00'),  # Usar unique_id como CPF temporário
                    emp.get('phone_number'),
                    emp.get('email', ''),
                    emp.get('department', ''),
                    emp.get('position', ''),
                    emp.get('is_active', True),
                    admin_id  # Usar ID real do admin
                ))
                
                migrated_count += 1
                print(f"✅ Migrado: {emp.get('full_name')}")
                
            except Exception as e:
                print(f"❌ Erro ao migrar {emp.get('full_name')}: {e}")
                continue
        
        # Commit das alterações
        conn.commit()
        
        print(f"\n🎉 Migração concluída!")
        print(f"✅ {migrated_count} funcionários migrados")
        
        # Verificar dados migrados
        cursor.execute("SELECT COUNT(*) FROM employees")
        total_employees = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        print(f"📊 Total no banco: {total_users} usuários, {total_employees} funcionários")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        return False

if __name__ == "__main__":
    success = simple_migration()
    if success:
        print("\n🎉 Migração realizada com sucesso!")
    else:
        print("\n❌ Falha na migração")
    
    sys.exit(0 if success else 1)