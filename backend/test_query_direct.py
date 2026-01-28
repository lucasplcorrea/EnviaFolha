import psycopg2

# Conectar ao PostgreSQL
db_url = "postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db"
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Testar query diretamente
cur.execute("""
    SELECT 
        COUNT(*) as total_employees,
        COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO')::numeric), 0) as gratif_funcao,
        COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO_20')::numeric), 0) as gratif_20,
        COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO_13_SAL_PROP')::numeric), 0) as gratif_13,
        COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO_ABONO')::numeric), 0) as gratif_abono,
        COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO_FERIAS')::numeric), 0) as gratif_ferias,
        COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO_FERIAS_PROP')::numeric), 0) as gratif_ferias_prop,
        (
            COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO')::numeric), 0) + 
            COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO_20')::numeric), 0) +
            COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO_13_SAL_PROP')::numeric), 0) +
            COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO_ABONO')::numeric), 0) +
            COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO_FERIAS')::numeric), 0) +
            COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO_FERIAS_PROP')::numeric), 0)
        ) as total_gratificacoes
    FROM payroll_data
    WHERE period_id = 39
""")

result = cur.fetchone()

print("📊 Resultado da query SQL:")
print(f"   Total Employees: {result[0]}")
print(f"   Gratif Função: R$ {result[1]:,.2f}")
print(f"   Gratif 20%: R$ {result[2]:,.2f}")
print(f"   Gratif 13º: R$ {result[3]:,.2f}")
print(f"   Gratif Abono: R$ {result[4]:,.2f}")
print(f"   Gratif Férias: R$ {result[5]:,.2f}")
print(f"   Gratif Férias Prop: R$ {result[6]:,.2f}")
print(f"   TOTAL: R$ {result[7]:,.2f}")

conn.close()
