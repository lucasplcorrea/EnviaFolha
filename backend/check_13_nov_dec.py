from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

query = """
SELECT 
    pp.month, 
    pp.year, 
    COUNT(*) as records, 
    COALESCE(SUM((earnings_data->>'13_SALARIO_ADIANTAMENTO')::numeric), 0) as adiant, 
    COALESCE(SUM((earnings_data->>'13_SALARIO_INTEGRAL')::numeric), 0) as integral,
    COALESCE(SUM((earnings_data->>'13_GRATIFICACAO_FUNCAO_ADIANTAMENTO')::numeric), 0) as gratif_adiant,
    COALESCE(SUM((earnings_data->>'13_GRATIFICACAO_FUNCAO_INTEGRAL')::numeric), 0) as gratif_integral
FROM payroll_data pd 
INNER JOIN payroll_periods pp ON pp.id = pd.period_id 
WHERE pp.year = 2025 AND pp.month IN (11, 12) 
GROUP BY pp.month, pp.year 
ORDER BY pp.month
"""

with engine.connect() as conn:
    result = conn.execute(text(query))
    rows = result.fetchall()
    
    print("VALORES DE 13º SALÁRIO - NOVEMBRO E DEZEMBRO 2025")
    print("="*80)
    print(f"{'MÊS':12} | {'REGISTROS':>9} | {'13º ADIANT':>12} | {'13º INTEGRAL':>13} | {'TOTAL':>12}")
    print("-"*80)
    
    for r in rows:
        month = "Novembro" if r[0] == 11 else "Dezembro"
        total = r[3] + r[4] + r[5] + r[6]
        print(f"{month:12} | {r[2]:9} | R$ {r[3]:>9,.2f} | R$ {r[4]:>10,.2f} | R$ {total:>9,.2f}")
