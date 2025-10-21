"""Migration: add employee status fields

This migration is idempotent: it checks for column existence before creating.
"""
from sqlalchemy import create_engine, inspect, text
import os


def run_migration(database_url=None):
    database_url = database_url or os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_URI')
    if not database_url:
        print('DATABASE_URL not provided; skipping migration')
        return

    engine = create_engine(database_url)
    inspector = inspect(engine)

    with engine.begin() as conn:
        # employees table alterations
        if 'employees' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('employees')]
            
            if 'employment_status' not in columns:
                try:
                    conn.execute(text('ALTER TABLE employees ADD COLUMN employment_status VARCHAR(50)'))
                    print('Added column employment_status to employees')
                except Exception as e:
                    print(f'Could not add column employment_status: {e}')
            
            if 'termination_date' not in columns:
                try:
                    conn.execute(text('ALTER TABLE employees ADD COLUMN termination_date DATE'))
                    print('Added column termination_date to employees')
                except Exception as e:
                    print(f'Could not add column termination_date: {e}')
            
            if 'leave_start_date' not in columns:
                try:
                    conn.execute(text('ALTER TABLE employees ADD COLUMN leave_start_date DATE'))
                    print('Added column leave_start_date to employees')
                except Exception as e:
                    print(f'Could not add column leave_start_date: {e}')
            
            if 'leave_end_date' not in columns:
                try:
                    conn.execute(text('ALTER TABLE employees ADD COLUMN leave_end_date DATE'))
                    print('Added column leave_end_date to employees')
                except Exception as e:
                    print(f'Could not add column leave_end_date: {e}')
            
            # Atualizar status_reason para TEXT se for VARCHAR
            try:
                conn.execute(text('ALTER TABLE employees ALTER COLUMN status_reason TYPE TEXT'))
                print('Updated status_reason to TEXT type')
            except Exception as e:
                print(f'Could not update status_reason type (may already be TEXT): {e}')


if __name__ == '__main__':
    run_migration()
