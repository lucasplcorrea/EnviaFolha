"""
Script para criar as tabelas de benefícios no banco de dados
"""
import sys
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine

# Construir DATABASE_URL
database_url = os.getenv('DATABASE_URL')
if not database_url:
    db_user = os.getenv('DB_USER', 'enviafolha_user')
    db_password = os.getenv('DB_PASSWORD', 'secure_password')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'enviafolha_db')
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

print(f"🔌 Conectando ao PostgreSQL...")

# Criar engine
engine = create_engine(database_url, echo=False)

# Importar modelos
from app.models.base import Base
from app.models.payroll import BenefitsPeriod, BenefitsData, BenefitsProcessingLog

print("=" * 60)
print("🔧 Criando tabelas de benefícios...")
print("=" * 60)

try:
    # Criar apenas as tabelas de benefícios
    BenefitsPeriod.__table__.create(engine, checkfirst=True)
    print("✅ Tabela 'benefits_periods' criada/verificada")
    
    BenefitsData.__table__.create(engine, checkfirst=True)
    print("✅ Tabela 'benefits_data' criada/verificada")
    
    BenefitsProcessingLog.__table__.create(engine, checkfirst=True)
    print("✅ Tabela 'benefits_processing_logs' criada/verificada")
    
    print("=" * 60)
    print("✅ Tabelas de benefícios criadas com sucesso!")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Erro ao criar tabelas: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
