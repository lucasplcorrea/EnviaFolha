"""Completa colunas exigidas pelos módulos recuperados da develop."""

import os

from sqlalchemy import create_engine, inspect, text


def run_migration(database_url=None):
    database_url = database_url or os.getenv('DATABASE_URL') or os.getenv('DATABASE_URI')
    if not database_url:
        print('ℹ️  DATABASE_URL não definida; sincronização da develop ignorada')
        return

    engine = create_engine(database_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        if 'movement_records' in tables:
            columns = {column['name'] for column in inspector.get_columns('movement_records')}
            if 'previous_work_location_id' not in columns:
                connection.execute(text(
                    'ALTER TABLE movement_records ADD COLUMN previous_work_location_id INTEGER'
                ))
            if 'new_work_location_id' not in columns:
                connection.execute(text(
                    'ALTER TABLE movement_records ADD COLUMN new_work_location_id INTEGER'
                ))

    print('✅ Schema dos módulos da develop sincronizado')


if __name__ == '__main__':
    run_migration()
