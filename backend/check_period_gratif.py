import sqlite3
import json

conn = sqlite3.connect('payroll.db')
cur = conn.cursor()

# Verificar períodos
print("📅 Períodos cadastrados:")
periods = cur.execute("SELECT id, period_name FROM payroll_periods ORDER BY id DESC LIMIT 5").fetchall()
for p in periods:
    print(f"  ID {p[0]}: {p[1]}")

# Buscar último período
if periods:
    period_id = periods[0][0]
    period_name = periods[0][1]
    
    print(f"\n🔍 Analisando período: {period_name} (ID {period_id})")
    
    # Contar registros
    total_records = cur.execute("SELECT COUNT(*) FROM payroll_data WHERE period_id = ?", (period_id,)).fetchone()[0]
    print(f"   Total de registros: {total_records}")
    
    # Verificar gratificações
    print("\n💰 Gratificações encontradas:")
    rows = cur.execute("SELECT employee_id, earnings_data FROM payroll_data WHERE period_id = ?", (period_id,)).fetchall()
    
    total_gratificacoes = 0
    detalhes = {}
    
    for emp_id, earnings_json in rows:
        if earnings_json:
            earnings = json.loads(earnings_json)
            
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
        for label, data in detalhes.items():
            print(f"   {label}: {data['count']} registros, R$ {data['total']:,.2f}")
        print(f"\n   🎁 TOTAL GRATIFICAÇÕES: R$ {total_gratificacoes:,.2f}")
    else:
        print("   ⚠️ Nenhuma gratificação encontrada!")
        
        # Mostrar um exemplo de earnings_data para debug
        print("\n📋 Exemplo de earnings_data (primeiro registro):")
        if rows:
            emp_id, earnings_json = rows[0]
            if earnings_json:
                earnings = json.loads(earnings_json)
                print(json.dumps(earnings, indent=2, ensure_ascii=False))

conn.close()
