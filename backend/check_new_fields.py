from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

print("\n📊 Verificando novos campos capturados - Período 37\n")
print("="*80)

# Verificar HE
result = db.execute(text("""
    SELECT 
        COUNT(CASE WHEN earnings_data->>'HORAS_EXTRAS_50_DIURNAS' IS NOT NULL THEN 1 END) as he_50_diurnas,
        COALESCE(SUM((earnings_data->>'HORAS_EXTRAS_50_DIURNAS')::numeric), 0) as total_he_50_diurnas,
        COUNT(CASE WHEN earnings_data->>'HORAS_EXTRAS_50_NOTURNAS' IS NOT NULL THEN 1 END) as he_50_noturnas,
        COALESCE(SUM((earnings_data->>'HORAS_EXTRAS_50_NOTURNAS')::numeric), 0) as total_he_50_noturnas,
        COUNT(CASE WHEN earnings_data->>'HORAS_EXTRAS_60_DIURNAS' IS NOT NULL THEN 1 END) as he_60,
        COALESCE(SUM((earnings_data->>'HORAS_EXTRAS_60_DIURNAS')::numeric), 0) as total_he_60,
        COUNT(CASE WHEN earnings_data->>'HORAS_EXTRAS_100_DIURNAS' IS NOT NULL THEN 1 END) as he_100_diurnas,
        COALESCE(SUM((earnings_data->>'HORAS_EXTRAS_100_DIURNAS')::numeric), 0) as total_he_100_diurnas,
        COUNT(CASE WHEN earnings_data->>'HORAS_EXTRAS_100_NOTURNAS' IS NOT NULL THEN 1 END) as he_100_noturnas,
        COALESCE(SUM((earnings_data->>'HORAS_EXTRAS_100_NOTURNAS')::numeric), 0) as total_he_100_noturnas
    FROM payroll_data
    WHERE period_id = 37
"""))

row = result.fetchone()
print("\n💰 HORAS EXTRAS:")
print(f"   HE 50% Diurnas:   {row[0]} registros | R$ {row[1]:,.2f}")
print(f"   HE 50% Noturnas:  {row[2]} registros | R$ {row[3]:,.2f}")
print(f"   HE 60% Diurnas:   {row[4]} registros | R$ {row[5]:,.2f}")
print(f"   HE 100% Diurnas:  {row[6]} registros | R$ {row[7]:,.2f}")
print(f"   HE 100% Noturnas: {row[8]} registros | R$ {row[9]:,.2f}")

# Verificar Adicional Noturno
result = db.execute(text("""
    SELECT 
        COUNT(CASE WHEN earnings_data->>'ADICIONAL_NOTURNO' IS NOT NULL THEN 1 END),
        COALESCE(SUM((earnings_data->>'ADICIONAL_NOTURNO')::numeric), 0),
        COUNT(CASE WHEN additional_data->>'Horas Normais Noturnas' IS NOT NULL THEN 1 END),
        COALESCE(SUM((additional_data->>'Horas Normais Noturnas')::numeric), 0)
    FROM payroll_data
    WHERE period_id = 37
"""))

row = result.fetchone()
print(f"\n🌙 ADICIONAL NOTURNO:")
print(f"   Valor (R$):      {row[0]} registros | R$ {row[1]:,.2f}")
print(f"   Horas Noturnas:  {row[2]} registros | {row[3]:,.2f} horas")

# Verificar Gratificações
result = db.execute(text("""
    SELECT 
        COUNT(CASE WHEN earnings_data->>'GRATIFICACAO_FUNCAO' IS NOT NULL THEN 1 END),
        COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO')::numeric), 0),
        COUNT(CASE WHEN earnings_data->>'GRATIFICACAO_FUNCAO_20' IS NOT NULL THEN 1 END),
        COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO_20')::numeric), 0)
    FROM payroll_data
    WHERE period_id = 37
"""))

row = result.fetchone()
print(f"\n🎁 GRATIFICAÇÕES:")
print(f"   Gratificação de Função:     {row[0]} registros | R$ {row[1]:,.2f}")
print(f"   Gratificação de Função 20%: {row[2]} registros | R$ {row[3]:,.2f}")

# Verificar Adicionais Legais
result = db.execute(text("""
    SELECT 
        COUNT(CASE WHEN earnings_data->>'PERICULOSIDADE' IS NOT NULL THEN 1 END),
        COALESCE(SUM((earnings_data->>'PERICULOSIDADE')::numeric), 0),
        COUNT(CASE WHEN earnings_data->>'INSALUBRIDADE' IS NOT NULL THEN 1 END),
        COALESCE(SUM((earnings_data->>'INSALUBRIDADE')::numeric), 0)
    FROM payroll_data
    WHERE period_id = 37
"""))

row = result.fetchone()
print(f"\n⚠️  ADICIONAIS LEGAIS:")
print(f"   Periculosidade: {row[0]} registros | R$ {row[1]:,.2f}")
print(f"   Insalubridade:  {row[2]} registros | R$ {row[3]:,.2f}")

# Verificar Vale Transporte
result = db.execute(text("""
    SELECT 
        COUNT(CASE WHEN benefits_data->>'VALE_TRANSPORTE' IS NOT NULL THEN 1 END),
        COALESCE(SUM((benefits_data->>'VALE_TRANSPORTE')::numeric), 0)
    FROM payroll_data
    WHERE period_id = 37
"""))

row = result.fetchone()
print(f"\n🚌 VALE TRANSPORTE:")
print(f"   Registros: {row[0]} | R$ {row[1]:,.2f}")

print("\n" + "="*80)
db.close()
