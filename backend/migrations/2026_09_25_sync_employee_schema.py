"""Sincroniza colunas opcionais de employees em instalações existentes.

Base.metadata.create_all() não altera tabelas existentes. Esta migration é
idempotente e preserva todos os registros já armazenados.
"""

import os

from sqlalchemy import create_engine, inspect, text


EMPLOYEE_COLUMNS = {
    'email': 'VARCHAR(255)',
    'department': 'VARCHAR(100)',
    'position': 'VARCHAR(100)',
    'company_code': 'VARCHAR(20)',
    'registration_number': 'VARCHAR(20)',
    'sector': 'VARCHAR(100)',
    'is_active': 'BOOLEAN DEFAULT TRUE',
    'created_by': 'INTEGER',
    'updated_by': 'INTEGER',
    'birth_date': 'DATE',
    'sex': 'VARCHAR(10)',
    'marital_status': 'VARCHAR(50)',
    'admission_date': 'DATE',
    'contract_type': 'VARCHAR(50)',
    'employment_status': 'VARCHAR(50)',
    'termination_date': 'DATE',
    'leave_start_date': 'DATE',
    'leave_end_date': 'DATE',
    'status_reason': 'TEXT',
    'created_at': 'TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP',
    'updated_at': 'TIMESTAMP WITH TIME ZONE',
}


def run_migration(database_url=None):
    database_url = database_url or os.getenv('DATABASE_URL') or os.getenv('DATABASE_URI')
    if not database_url:
        print('ℹ️  DATABASE_URL não definida; sincronização de employees ignorada')
        return

    engine = create_engine(database_url)
    inspector = inspect(engine)
    if 'employees' not in inspector.get_table_names():
        print('ℹ️  Tabela employees ainda não existe; será criada pela aplicação')
        return

    existing_columns = {column['name'] for column in inspector.get_columns('employees')}
    added_columns = []
    with engine.begin() as connection:
        for column_name, column_type in EMPLOYEE_COLUMNS.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(
                f'ALTER TABLE employees ADD COLUMN {column_name} {column_type}'
            ))
            added_columns.append(column_name)

        connection.execute(text(
            'UPDATE employees SET is_active = TRUE WHERE is_active IS NULL'
        ))

    if added_columns:
        print(f"✅ Colunas adicionadas em employees: {', '.join(added_columns)}")
    else:
        print('✅ Schema de employees já está sincronizado')


if __name__ == '__main__':
    run_migration()
