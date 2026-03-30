"""
WIPE TOTAL — Zera TODAS as tabelas exceto 'users' e 'roles'.
"""
import psycopg2

conn = psycopg2.connect("postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db")
conn.autocommit = False
cur = conn.cursor()

try:
    print("🚨 Iniciando wipe total do banco (preservando users e roles)...")

    cur.execute("""
        TRUNCATE TABLE
            payroll_data,
            payroll_records,
            payroll_periods,
            payroll_sends,
            payroll_templates,
            payroll_processing_logs,
            leave_records,
            benefit_records,
            benefits_data,
            benefits_periods,
            benefits_processing_logs,
            communication_recipients,
            communication_sends,
            tax_statements,
            tax_statement_uploads,
            send_queue_items,
            send_queues,
            hr_indicator_snapshots,
            movement_records,
            system_logs,
            employees,
            companies,
            work_locations
        RESTART IDENTITY CASCADE
    """)

    conn.commit()

    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
    tables = [r[0] for r in cur.fetchall()]

    print("\n✅ Wipe concluído! Contagem de registros:")
    skip = {'alembic_version', 'users', 'roles'}
    for t in tables:
        if t in skip:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            count = cur.fetchone()[0]
            print(f"  {t}: 🔒 {count} registros (preservado)")
        else:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                count = cur.fetchone()[0]
                status = "✅ 0" if count == 0 else f"⚠️  {count} (ATENÇÃO!)"
                print(f"  {t}: {status}")
            except Exception:
                print(f"  {t}: (tabela não existe mais)")

    print("\n🎉 Banco zerado e pronto para reimportação limpa!")

except Exception as e:
    conn.rollback()
    print(f"\n❌ ERRO: {e}")
    print("Nenhuma alteração salva (rollback realizado).")
finally:
    cur.close()
    conn.close()
