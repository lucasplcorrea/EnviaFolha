import psycopg2
import json

# Conectar ao PostgreSQL
db_url = "postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db"
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Buscar período Julho 2025
cur.execute("""
    SELECT id, period_name 
    FROM payroll_periods 
    WHERE period_name LIKE '%Julho%' OR period_name LIKE '%07%'
    ORDER BY id DESC 
    LIMIT 1
""")

period = cur.fetchone()

if not period:
    print("❌ Período Julho 2025 não encontrado!")
    conn.close()
    exit()

period_id, period_name = period
print(f"✅ Período encontrado: {period_name} (ID {period_id})")

# Buscar registros com gratificações
cur.execute("""
    SELECT employee_id, earnings_data 
    FROM payroll_data 
    WHERE period_id = %s
""", (period_id,))

rows = cur.fetchall()
print(f"📊 Total de registros: {len(rows)}\n")

# Analisar gratificações
total_gratificacoes = 0
detalhes = {}

for emp_id, earnings_json in rows:
    if earnings_json:
        earnings = earnings_json if isinstance(earnings_json, dict) else json.loads(earnings_json)
        
        gratif_fields = {
            'GRATIFICACAO_FUNCAO': 'Gratificação de Função',
            'GRATIFICACAO_FUNCAO_20': 'Gratificação de Função 20%',
            'GRATIFICACAO_FUNCAO_13_SAL_PROP': 'Gratificação 13º Sal Prop',
            'GRATIFICACAO_FUNCAO_ABONO': 'Gratificação Abono',
            'GRATIFICACAO_FUNCAO_FERIAS': 'Gratificação Férias',
            'GRATIFICACAO_FUNCAO_FERIAS_PROP': 'Gratificação Férias Prop'
        }
        
        for field, label in gratif_fields.items():
            if field in earnings:
                value = float(earnings[field])
                total_gratificacoes += value
                
                if label not in detalhes:
                    detalhes[label] = {'count': 0, 'total': 0}
                detalhes[label]['count'] += 1
                detalhes[label]['total'] += value

if detalhes:
    print("💰 Gratificações encontradas:")
    for label, data in detalhes.items():
        print(f"   {label}: {data['count']} registros, R$ {data['total']:,.2f}")
    print(f"\n   🎁 TOTAL GRATIFICAÇÕES: R$ {total_gratificacoes:,.2f}")
    print(f"\n   📊 Valor esperado: R$ 7.232,19")
    print(f"   {'✅ CORRETO!' if abs(total_gratificacoes - 7232.19) < 1 else '❌ DIFERENÇA!'}")
else:
    print("⚠️ Nenhuma gratificação encontrada!")
    
    # Mostrar exemplo para debug
    if rows:
        emp_id, earnings_json = rows[0]
        if earnings_json:
            earnings = earnings_json if isinstance(earnings_json, dict) else json.loads(earnings_json)
            print("\n📋 Exemplo de earnings_data (primeiro registro):")
            print(json.dumps(earnings, indent=2, ensure_ascii=False)[:500])

conn.close()
