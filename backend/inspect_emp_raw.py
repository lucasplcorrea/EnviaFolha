import psycopg2
import os

database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/dbname")
conn = psycopg2.connect(database_url)
conn.autocommit = False
cur = conn.cursor()
try:
    cur.execute("TRUNCATE TABLE payroll_periods RESTART IDENTITY CASCADE")
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM payroll_periods")
    print(f"payroll_periods: {'✅ 0' if cur.fetchone()[0] == 0 else '⚠️  ainda tem registros'}")
    print("🎉 Banco totalmente zerado (exceto users e roles)!")
except Exception as e:
    conn.rollback()
    print(f"❌ Erro: {e}")
finally:
    cur.close(); conn.close()
