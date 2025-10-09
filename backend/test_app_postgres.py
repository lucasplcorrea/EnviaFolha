#!/usr/bin/env python3
"""
Teste da aplicação com PostgreSQL
"""
import os
import sys

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(__file__))

def test_app_with_postgres():
    """Testa aplicação com PostgreSQL"""
    print("🧪 Testando aplicação com PostgreSQL...")
    
    try:
        # Configurar variável de ambiente
        os.environ['DATABASE_URL'] = 'postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db'
        
        # Importar e testar models
        from app.models.base import SessionLocal, engine
        from app.models import Employee, User
        from sqlalchemy import text
        
        print("✅ Modelos importados com sucesso")
        
        # Testar conexão com banco
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ PostgreSQL conectado: {version}")
        
        # Testar sessão
        db = SessionLocal()
        
        # Contar funcionários
        employees_count = db.query(Employee).count()
        print(f"👥 Funcionários no banco: {employees_count}")
        
        # Contar usuários
        users_count = db.query(User).count()
        print(f"👤 Usuários no banco: {users_count}")
        
        # Listar alguns funcionários
        employees = db.query(Employee).limit(3).all()
        print(f"📋 Funcionários encontrados:")
        for emp in employees:
            print(f"  - {emp.name} ({emp.unique_id})")
        
        db.close()
        
        print("\n🎉 Aplicação funcionando perfeitamente com PostgreSQL!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar aplicação: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_app_with_postgres()
    if success:
        print("\n✅ Teste realizado com sucesso!")
        print("🚀 Sua aplicação está pronta para usar PostgreSQL!")
    else:
        print("\n❌ Falha no teste")
    
    sys.exit(0 if success else 1)