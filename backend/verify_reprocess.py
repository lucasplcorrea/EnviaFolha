from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

print("\n📊 Verificando dados reprocessados - Período 37\n")
print("=" * 80)

# Status
print("\n👥 STATUS DOS COLABORADORES:")
result = db.execute(text("""
    SELECT 
        additional_data->>'Status' as status,
        COUNT(*) as quantidade
    FROM payroll_data
    WHERE period_id = 37
    GROUP BY additional_data->>'Status'
    ORDER BY quantidade DESC
"""))
for row in result:
    print(f"   {row[0]}: {row[1]} funcionários")

# INSS
print("\n💰 INSS:")
result = db.execute(text("""
    SELECT 
        COALESCE(SUM((deductions_data->>'INSS')::numeric), 0) as total_inss
    FROM payroll_data
    WHERE period_id = 37
"""))
row = result.fetchone()
print(f"   Total: R$ {row[0]:,.2f}")

# Vantagens
print("\n🎁 TOTAL DE VANTAGENS:")
result = db.execute(text("""
    SELECT 
        COUNT(CASE WHEN additional_data->>'Total de Vantagens' IS NOT NULL THEN 1 END) as com_vantagens,
        COALESCE(SUM((additional_data->>'Total de Vantagens')::numeric), 0) as total
    FROM payroll_data
    WHERE period_id = 37
"""))
row = result.fetchone()
print(f"   Registros com vantagens: {row[0]}")
print(f"   Total: R$ {row[1]:,.2f}")

# Plano de Saúde
print("\n💊 PLANO DE SAÚDE:")
result = db.execute(text("""
    SELECT 
        COUNT(CASE WHEN benefits_data->>'PLANO_SAUDE' IS NOT NULL THEN 1 END) as com_plano,
        COALESCE(SUM((benefits_data->>'PLANO_SAUDE')::numeric), 0) as total
    FROM payroll_data
    WHERE period_id = 37
"""))
row = result.fetchone()
print(f"   Registros com plano: {row[0]}")
print(f"   Total: R$ {row[1]:,.2f}")

print("\n" + "=" * 80)
db.close()
