from sqlalchemy import create_engine, text
import json

engine = create_engine('postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db')
conn = engine.connect()

# Query valores de 13º e férias por período
result = conn.execute(text("""
    SELECT 
        pp.period_name, 
        pp.month, 
        pp.year,
        SUM((pd.earnings_data->>'FERIAS_VALOR_BASE')::numeric) as ferias_base,
        SUM((pd.earnings_data->>'FERIAS_ABONO_1_3')::numeric) as ferias_abono,
        SUM((pd.earnings_data->>'13_SALARIO_ADIANTAMENTO')::numeric) as t13_adiant,
        SUM((pd.earnings_data->>'13_SALARIO_INTEGRAL')::numeric) as t13_integral,
        COUNT(*) as total_records
    FROM payroll_data pd
    JOIN payroll_periods pp ON pd.period_id = pp.id
    WHERE pp.year = 2025
    GROUP BY pp.period_name, pp.month, pp.year
    ORDER BY pp.year, pp.month
"""))

print('\n' + '='*150)
print('VALORES DE 13º E FÉRIAS POR PERÍODO - 2025')
print('='*150)
print(f"{'Período':40} | {'Férias Base':>12} | {'1/3 Abono':>12} | {'13º Adiant':>12} | {'13º Integral':>12} | {'Registros':>10}")
print('-'*150)

total_ferias_base = 0
total_ferias_abono = 0
total_13_adiant = 0
total_13_integral = 0

for row in result:
    ferias_base = row[3] or 0
    ferias_abono = row[4] or 0
    t13_adiant = row[5] or 0
    t13_integral = row[6] or 0
    
    total_ferias_base += ferias_base
    total_ferias_abono += ferias_abono
    total_13_adiant += t13_adiant
    total_13_integral += t13_integral
    
    # Destacar linhas com valores significativos
    highlight = ''
    if ferias_base > 1000 or ferias_abono > 1000 or t13_adiant > 1000 or t13_integral > 1000:
        highlight = ' <<<'
    
    print(f"{row[0]:40} | R$ {ferias_base:>10,.2f} | R$ {ferias_abono:>10,.2f} | R$ {t13_adiant:>10,.2f} | R$ {t13_integral:>10,.2f} | {row[7]:>10}{highlight}")

print('-'*150)
print(f"{'TOTAL':40} | R$ {total_ferias_base:>10,.2f} | R$ {total_ferias_abono:>10,.2f} | R$ {total_13_adiant:>10,.2f} | R$ {total_13_integral:>10,.2f}")
print('='*150)

# Agora verificar exemplos de colaboradores com provento < salário base
print('\n' + '='*150)
print('EXEMPLOS DE COLABORADORES COM PROVENTOS < SALÁRIO BASE')
print('='*150)

result2 = conn.execute(text("""
    SELECT 
        e.name,
        pp.period_name,
        (pd.additional_data->>'Valor Salário')::numeric as valor_salario,
        (pd.additional_data->>'Total de Proventos')::numeric as total_proventos,
        pd.additional_data->>'Status' as status,
        (pd.additional_data->>'Horas Faltas Diurnas')::numeric as horas_faltas
    FROM payroll_data pd
    JOIN employees e ON e.id = pd.employee_id
    JOIN payroll_periods pp ON pd.period_id = pp.id
    WHERE 
        (pd.additional_data->>'Valor Salário')::numeric > 0
        AND (pd.additional_data->>'Total de Proventos')::numeric > 0
        AND (pd.additional_data->>'Total de Proventos')::numeric < (pd.additional_data->>'Valor Salário')::numeric
        AND pp.year = 2025
    ORDER BY 
        ((pd.additional_data->>'Valor Salário')::numeric - (pd.additional_data->>'Total de Proventos')::numeric) DESC
    LIMIT 10
"""))

print(f"{'Nome':40} | {'Período':20} | {'Salário Base':>14} | {'Proventos':>14} | {'Diferença':>14} | {'Status':20} | {'H.Faltas':>10}")
print('-'*150)

for row in result2:
    nome = row[0][:38] if row[0] else 'N/A'
    periodo = row[1][:18] if row[1] else 'N/A'
    salario = row[2] or 0
    proventos = row[3] or 0
    status = row[4] if row[4] else 'N/A'
    faltas = row[5] or 0
    diferenca = salario - proventos
    
    print(f"{nome:40} | {periodo:20} | R$ {salario:>10,.2f} | R$ {proventos:>10,.2f} | R$ {diferenca:>10,.2f} | {status:20} | {faltas:>10.1f}")

print('='*150)

conn.close()
