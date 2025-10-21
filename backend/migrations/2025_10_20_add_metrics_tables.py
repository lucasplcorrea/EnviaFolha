"""Migration: add metrics tables and extend employees table

This migration is idempotent: it checks for table/column existence before creating.
"""
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Date, DateTime, Boolean, text
from sqlalchemy import inspect
import os


def run_migration(database_url=None):
    database_url = database_url or os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_URI')
    if not database_url:
        print('DATABASE_URL not provided; skipping migration')
        return

    engine = create_engine(database_url)
    inspector = inspect(engine)
    metadata = MetaData()
    metadata.bind = engine

    with engine.begin() as conn:  # Use begin() para auto-commit
        # employees table alterations
        if 'employees' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('employees')]
            alter_needed = False
            to_add = []
            if 'birth_date' not in columns:
                to_add.append(Column('birth_date', Date))
            if 'sex' not in columns:
                to_add.append(Column('sex', String(10)))
            if 'marital_status' not in columns:
                to_add.append(Column('marital_status', String(50)))
            if 'admission_date' not in columns:
                to_add.append(Column('admission_date', Date))
            if 'contract_type' not in columns:
                to_add.append(Column('contract_type', String(50)))
            if 'status_reason' not in columns:
                to_add.append(Column('status_reason', String(255)))

            for col in to_add:
                try:
                    # Use generic SQL - this is simple and should work for Postgres
                    sql = text(f'ALTER TABLE employees ADD COLUMN {col.name} {col.type.compile() if hasattr(col.type, "compile") else str(col.type)}')
                    conn.execute(sql)
                    print(f'Added column {col.name} to employees')
                except Exception as e:
                    print(f'Could not add column {col.name}: {e}')

        # create payroll_records
        if 'payroll_records' not in inspector.get_table_names():
            conn.execute(text('''
            CREATE TABLE payroll_records (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                unified_code VARCHAR(255),
                competence VARCHAR(7) NOT NULL,
                salary_base DOUBLE PRECISION,
                additions DOUBLE PRECISION,
                deductions DOUBLE PRECISION,
                hours_extra DOUBLE PRECISION,
                hours_absence DOUBLE PRECISION,
                net_salary DOUBLE PRECISION,
                created_at TIMESTAMP
            );
            '''))
            print('Created payroll_records')

        # create benefit_records
        if 'benefit_records' not in inspector.get_table_names():
            conn.execute(text('''
            CREATE TABLE benefit_records (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                unified_code VARCHAR(255),
                benefit_type VARCHAR(255) NOT NULL,
                value DOUBLE PRECISION,
                created_at TIMESTAMP
            );
            '''))
            print('Created benefit_records')

        # create movement_records
        if 'movement_records' not in inspector.get_table_names():
            conn.execute(text('''
            CREATE TABLE movement_records (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                unified_code VARCHAR(255),
                movement_type VARCHAR(100) NOT NULL,
                previous_position VARCHAR(255),
                new_position VARCHAR(255),
                previous_department VARCHAR(255),
                new_department VARCHAR(255),
                date DATE NOT NULL,
                reason TEXT,
                created_at TIMESTAMP
            );
            '''))
            print('Created movement_records')

        # create leave_records
        if 'leave_records' not in inspector.get_table_names():
            conn.execute(text('''
            CREATE TABLE leave_records (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                unified_code VARCHAR(255),
                leave_type VARCHAR(100) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                days DOUBLE PRECISION,
                notes TEXT,
                created_at TIMESTAMP
            );
            '''))
            print('Created leave_records')


if __name__ == '__main__':
    run_migration()
