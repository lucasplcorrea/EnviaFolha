"""
Script para migrar senhas de MD5 para bcrypt
"""
import json
import sys
import os

from common import ensure_backend_on_path, get_database_url, load_repo_env

ensure_backend_on_path()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.core.auth import get_password_hash

load_repo_env()

DATABASE_URL = get_database_url()

# Criar engine e sessão
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def load_password_overrides() -> tuple[dict[str, str], str | None]:
    raw_map = os.getenv("PASSWORD_MIGRATION_MAP", "{}")
    try:
        password_map = json.loads(raw_map)
    except json.JSONDecodeError as exc:
        raise RuntimeError("PASSWORD_MIGRATION_MAP deve ser um JSON válido.") from exc

    if not isinstance(password_map, dict):
        raise RuntimeError("PASSWORD_MIGRATION_MAP deve ser um objeto JSON com usuario -> senha.")

    normalized_map = {str(key): str(value) for key, value in password_map.items()}
    fallback_password = os.getenv("DEFAULT_MIGRATION_PASSWORD")
    return normalized_map, fallback_password

def migrate_passwords():
    """Migra senhas de MD5 para bcrypt"""
    db = SessionLocal()
    
    try:
        print("🔄 Iniciando migração de senhas...")
        
        # Buscar todos os usuários
        users = db.query(User).all()
        print(f"📊 Encontrados {len(users)} usuários")
        password_overrides, fallback_password = load_password_overrides()
        
        migrated = 0
        skipped = 0
        for user in users:
            # Se o hash não parece bcrypt (bcrypt começa com $2b$)
            if not user.password_hash.startswith('$2b$'):
                print(f"\n👤 Usuário: {user.username}")
                print(f"   Hash antigo (MD5): {user.password_hash[:20]}...")
                
                password = password_overrides.get(user.username)
                if password:
                    new_hash = get_password_hash(password)
                    user.password_hash = new_hash
                    print("   ✅ Hash atualizado usando senha definida por variável de ambiente")
                    print(f"   Novo hash (bcrypt): {new_hash[:30]}...")
                    migrated += 1
                elif fallback_password:
                    new_hash = get_password_hash(fallback_password)
                    user.password_hash = new_hash
                    print("   ⚠️ Hash atualizado usando DEFAULT_MIGRATION_PASSWORD")
                    print(f"   Novo hash (bcrypt): {new_hash[:30]}...")
                    migrated += 1
                else:
                    print("   ⚠️ Senha não informada via ambiente; usuário preservado sem alteração")
                    skipped += 1
            else:
                print(f"✅ {user.username} já usa bcrypt")
        
        if migrated > 0:
            db.commit()
            print(f"\n✅ {migrated} senha(s) migrada(s) com sucesso!")
        else:
            print(f"\n✅ Nenhuma senha precisou ser migrada")

        if skipped > 0:
            print(f"⚠️ {skipped} usuário(s) ficaram sem migração por falta de senha no ambiente")
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_passwords()
