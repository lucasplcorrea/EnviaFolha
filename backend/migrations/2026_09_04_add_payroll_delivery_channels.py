"""Adiciona metadados de canal às filas e aos registros de holerite.

A migração é idempotente e é executada pelo docker-entrypoint existente.
"""

import os

from sqlalchemy import create_engine, inspect, text


def _add_column(conn, table_name, existing_columns, column_name, definition):
    if column_name not in existing_columns:
        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}'))
        print(f'✅ Coluna {table_name}.{column_name} adicionada')


def run_migration(database_url=None):
    database_url = database_url or os.getenv('DATABASE_URL') or os.getenv('DATABASE_URI')
    if not database_url:
        print('ℹ️  DATABASE_URL não definida; migration de canais ignorada')
        return

    engine = create_engine(database_url)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as conn:
        if 'payroll_sends' in table_names:
            columns = {column['name'] for column in inspector.get_columns('payroll_sends')}
            _add_column(conn, 'payroll_sends', columns, 'channel', "VARCHAR(20) DEFAULT 'whatsapp' NOT NULL")
            _add_column(conn, 'payroll_sends', columns, 'recipient', 'VARCHAR(320)')
            _add_column(conn, 'payroll_sends', columns, 'attempt_count', 'INTEGER DEFAULT 0 NOT NULL')
            _add_column(conn, 'payroll_sends', columns, 'provider_message_id', 'VARCHAR(255)')
            _add_column(conn, 'payroll_sends', columns, 'idempotency_key', 'VARCHAR(255)')
            conn.execute(text("UPDATE payroll_sends SET channel = 'whatsapp' WHERE channel IS NULL"))
            conn.execute(text("UPDATE payroll_sends SET attempt_count = 0 WHERE attempt_count IS NULL"))
            conn.execute(text(
                'CREATE UNIQUE INDEX IF NOT EXISTS ix_payroll_sends_idempotency_key '
                'ON payroll_sends (idempotency_key)'
            ))

        if 'send_queue_items' in table_names:
            columns = {column['name'] for column in inspector.get_columns('send_queue_items')}
            _add_column(conn, 'send_queue_items', columns, 'channel', "VARCHAR(20) DEFAULT 'whatsapp' NOT NULL")
            _add_column(conn, 'send_queue_items', columns, 'recipient', 'VARCHAR(320)')
            conn.execute(text("UPDATE send_queue_items SET channel = 'whatsapp' WHERE channel IS NULL"))
            conn.execute(text(
                'UPDATE send_queue_items SET recipient = phone_number '
                'WHERE recipient IS NULL AND phone_number IS NOT NULL'
            ))

    print('✅ Migration de canais de envio concluída')


if __name__ == '__main__':
    run_migration()
