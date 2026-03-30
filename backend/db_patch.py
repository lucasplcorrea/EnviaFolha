import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.base import engine, Base
from app.models.movement import MovementRecord
from sqlalchemy import text, inspect

def run_patch():
    try:
        # Create tables that don't exist yet (including movement_records)
        print("Ensuring tables exist...")
        Base.metadata.create_all(bind=engine)
        
        # Verify if migration is needed anyway
        with engine.connect() as conn:
            is_sqlite = engine.url.drivername == 'sqlite'
            
            if is_sqlite:
                result = conn.execute(text("PRAGMA table_info(movement_records)"))
                columns = [row[1] for row in result]
            else:
                result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='movement_records'"))
                columns = [row[0] for row in result]
            
            if 'previous_work_location_id' not in columns:
                print("Adding previous_work_location_id...")
                conn.execute(text("ALTER TABLE movement_records ADD COLUMN previous_work_location_id INTEGER REFERENCES work_locations(id)"))
                conn.commit()
                print("Added previous_work_location_id successfully!")
            else:
                print("previous_work_location_id already exists.")

            if 'new_work_location_id' not in columns:
                print("Adding new_work_location_id...")
                conn.execute(text("ALTER TABLE movement_records ADD COLUMN new_work_location_id INTEGER REFERENCES work_locations(id)"))
                conn.commit()
                print("Added new_work_location_id successfully!")
            else:
                print("new_work_location_id already exists.")
                
            print("DB Patch completed successfully!")
            
    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    run_patch()
