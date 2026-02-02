"""
Ajustar campo upload_filename em benefits_data
"""
import sys
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text

# Construir DATABASE_URL
database_url = os.getenv('DATABASE_URL')
if not database_url:
    db_user = os.getenv('DB_USER', 'enviafolha_user')
    db_password = os.getenv('DB_PASSWORD', 'secure_password')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'enviafolha_db')
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Criar engine
engine = create_engine(database_url, echo=False)

print("🔧 Ajustando campos...")

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE benefits_data ALTER COLUMN upload_filename TYPE VARCHAR(500);'))
    conn.execute(text('ALTER TABLE benefits_data ALTER COLUMN cpf TYPE VARCHAR(20);'))
    conn.commit()
    print("✅ Campos alterados com sucesso!")
