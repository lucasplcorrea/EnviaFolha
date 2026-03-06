"""
Script para migrar senhas de MD5 para bcrypt
"""
import sys
import os

# Adicionar diretório backend ao path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.core.auth import get_password_hash
from dotenv import load_dotenv

# Carregar variáveis de ambiente
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Configuração do banco
DB_USER = os.getenv("DB_USER", "enviafolha_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secure_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "enviafolha_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Criar engine e sessão
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def migrate_passwords():
    """Migra senhas de MD5 para bcrypt"""
    db = SessionLocal()
    
    try:
        print("🔄 Iniciando migração de senhas...")
        
        # Buscar todos os usuários
        users = db.query(User).all()
        print(f"📊 Encontrados {len(users)} usuários")
        
        # Senhas padrão conhecidas (ajuste conforme necessário)
        default_passwords = {
            'admin': 'admin123',
            'lucas.pedro': '@Lmightpush1',  # Senha que você tentou atualizar
        }
        
        migrated = 0
        for user in users:
            # Se o hash não parece bcrypt (bcrypt começa com $2b$)
            if not user.password_hash.startswith('$2b$'):
                print(f"\n👤 Usuário: {user.username}")
                print(f"   Hash antigo (MD5): {user.password_hash[:20]}...")
                
                # Se conhecemos a senha, recriar o hash
                if user.username in default_passwords:
                    password = default_passwords[user.username]
                    new_hash = get_password_hash(password)
                    user.password_hash = new_hash
                    print(f"   ✅ Nova senha aplicada: {password}")
                    print(f"   Novo hash (bcrypt): {new_hash[:30]}...")
                    migrated += 1
                else:
                    print(f"   ⚠️ Senha desconhecida - usar senha padrão: admin123")
                    new_hash = get_password_hash('admin123')
                    user.password_hash = new_hash
                    migrated += 1
            else:
                print(f"✅ {user.username} já usa bcrypt")
        
        if migrated > 0:
            db.commit()
            print(f"\n✅ {migrated} senha(s) migrada(s) com sucesso!")
        else:
            print(f"\n✅ Nenhuma senha precisou ser migrada")
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_passwords()
