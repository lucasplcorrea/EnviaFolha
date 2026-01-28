import sys
import json
sys.path.insert(0, r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\backend')

import sqlite3

# Conectar ao banco
conn = sqlite3.connect('payroll.db')
cur = conn.cursor()

# Buscar período 37 ou 38
print("Verificando período Julho 2025...")
period = cur.execute("""
    SELECT id, period_name 
    FROM payroll_periods 
    WHERE period_name LIKE '%Julho%' 
    ORDER BY id DESC 
    LIMIT 1
""").fetchone()

if not period:
    print("Período não encontrado!")
    conn.close()
    exit()

period_id = period[0]
period_name = period[1]
print(f"✅ Período encontrado: ID {period_id} - {period_name}\n")

# Buscar registros com gratificações
print("Verificando gratificações capturadas...")
rows = cur.execute("""
    SELECT employee_id, earnings_data 
    FROM payroll_data 
    WHERE period_id = ?
""", (period_id,)).fetchall()

total_gratificacoes = 0
registros_com_gratificacoes = 0

for emp_id, earnings_json in rows:
    if earnings_json:
        earnings = json.loads(earnings_json)
        gratif_total = 0
        
        # Somar todos os tipos de gratificação
        gratif_fields = [
            'GRATIFICACAO_FUNCAO',
            'GRATIFICACAO_FUNCAO_20',
            'GRATIFICACAO_FUNCAO_13_SAL_PROP',
            'GRATIFICACAO_FUNCAO_ABONO',
            'GRATIFICACAO_FUNCAO_FERIAS',
            'GRATIFICACAO_FUNCAO_FERIAS_PROP'
        ]
        
        for field in gratif_fields:
            if field in earnings:
                gratif_total += float(earnings[field])
        
        if gratif_total > 0:
            registros_com_gratificacoes += 1
            total_gratificacoes += gratif_total
            print(f"  Funcionário {emp_id}: R$ {gratif_total:,.2f}")
            for field in gratif_fields:
                if field in earnings:
                    print(f"    - {field}: R$ {earnings[field]:,.2f}")

print(f"\n📊 RESUMO:")
print(f"   Registros com gratificações: {registros_com_gratificacoes}")
print(f"   Total de Gratificações: R$ {total_gratificacoes:,.2f}")

conn.close()
