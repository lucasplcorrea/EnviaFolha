#!/usr/bin/env python3
"""
Data Migration Script: JSON to PostgreSQL
==========================================

This script migrates existing employee and user data from the employees.json file
to the new PostgreSQL database schema.

Usage:
    python migrate_json_to_postgres.py

Requirements:
    - PostgreSQL database running and accessible
    - Alembic migrations applied (run: alembic upgrade head)
    - Environment variables configured (.env file)
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Add the app root to Python path
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Import all models
from app.models import User, Employee, AuditLog, SystemSetting

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class DataMigrator:
    """Handles migration of JSON data to PostgreSQL"""
    
    def __init__(self, database_url: str, json_file_path: str = "employees.json"):
        self.database_url = database_url
        self.json_file_path = json_file_path
        self.engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = SessionLocal()
        
        # Statistics
        self.stats = {
            'users_migrated': 0,
            'employees_migrated': 0,
            'errors': 0,
            'skipped': 0
        }
    
    def load_json_data(self) -> Dict:
        """Load and validate JSON data"""
        try:
            if not os.path.exists(self.json_file_path):
                logger.error(f"JSON file not found: {self.json_file_path}")
                return {}
            
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loaded JSON data: {len(data.get('users', []))} users, {len(data.get('employees', []))} employees")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading JSON: {e}")
            return {}
    
    def create_audit_log(self, action: str, entity_type: str, entity_id: str = None, 
                        description: str = None, user_id: int = 1):
        """Create audit log entry"""
        try:
            audit = AuditLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                description=description,
                ip_address="127.0.0.1",
                user_agent="Migration Script v1.0"
            )
            self.db.add(audit)
            self.db.flush()  # Don't commit yet
            
        except Exception as e:
            logger.error(f"Error creating audit log: {e}")
    
    def migrate_users(self, users_data: List[Dict]) -> Dict[int, int]:
        """Migrate users and return old_id -> new_id mapping"""
        user_id_mapping = {}
        
        for user_data in users_data:
            try:
                # Check if user already exists
                existing_user = self.db.query(User).filter(
                    (User.username == user_data.get('username')) |
                    (User.email == user_data.get('email'))
                ).first()
                
                if existing_user:
                    logger.warning(f"User {user_data.get('username')} already exists, skipping")
                    user_id_mapping[user_data.get('id')] = existing_user.id
                    self.stats['skipped'] += 1
                    continue
                
                # Hash password
                password = user_data.get('password', 'changeme123')
                password_hash = pwd_context.hash(password)
                
                # Create new user
                new_user = User(
                    username=user_data.get('username'),
                    email=user_data.get('email'),
                    full_name=user_data.get('full_name'),
                    password_hash=password_hash,
                    is_active=True,
                    is_admin=user_data.get('is_admin', False)
                )
                
                self.db.add(new_user)
                self.db.flush()  # Get the ID without committing
                
                # Map old ID to new ID
                user_id_mapping[user_data.get('id')] = new_user.id
                
                # Create audit log
                self.create_audit_log(
                    action="USER_MIGRATED",
                    entity_type="User",
                    entity_id=str(new_user.id),
                    description=f"Migrated user from JSON: {new_user.username}",
                    user_id=new_user.id
                )
                
                self.stats['users_migrated'] += 1
                logger.info(f"Migrated user: {new_user.username} (ID: {new_user.id})")
                
            except Exception as e:
                logger.error(f"Error migrating user {user_data.get('username', 'unknown')}: {e}")
                self.stats['errors'] += 1
                self.db.rollback()
        
        return user_id_mapping
    
    def validate_cpf(self, cpf: str) -> Optional[str]:
        """Validate and format CPF"""
        if not cpf:
            return None
        
        # Remove non-digits
        cpf_digits = ''.join(filter(str.isdigit, cpf))
        
        # Check length
        if len(cpf_digits) != 11:
            return None
        
        # Simple validation (you can add more sophisticated CPF validation)
        if cpf_digits == cpf_digits[0] * 11:  # All same digits
            return None
        
        return cpf_digits
    
    def validate_phone(self, phone: str) -> Optional[str]:
        """Validate and format phone number"""
        if not phone:
            return None
        
        # Remove non-digits
        phone_digits = ''.join(filter(str.isdigit, phone))
        
        # Add +55 if not present and is Brazilian format
        if len(phone_digits) == 11 and phone_digits.startswith(('1', '2', '3', '4', '5')):
            phone_digits = '55' + phone_digits
        elif len(phone_digits) == 10 and phone_digits.startswith(('1', '2', '3', '4', '5')):
            phone_digits = '55' + phone_digits
        
        # Format as +55XXXXXXXXXXX
        if len(phone_digits) >= 12:
            return '+' + phone_digits
        
        return phone
    
    def migrate_employees(self, employees_data: List[Dict], user_id_mapping: Dict[int, int]):
        """Migrate employees"""
        default_user_id = list(user_id_mapping.values())[0] if user_id_mapping else 1
        
        for emp_data in employees_data:
            try:
                # Validate unique_id
                unique_id = emp_data.get('unique_id')
                if not unique_id:
                    logger.warning(f"Employee missing unique_id: {emp_data.get('full_name', 'unknown')}")
                    self.stats['errors'] += 1
                    continue
                
                # Check if employee already exists
                existing_emp = self.db.query(Employee).filter(
                    Employee.unique_id == unique_id
                ).first()
                
                if existing_emp:
                    logger.warning(f"Employee {unique_id} already exists, skipping")
                    self.stats['skipped'] += 1
                    continue
                
                # Validate and format phone
                phone = self.validate_phone(emp_data.get('phone_number'))
                if not phone:
                    logger.warning(f"Invalid phone for employee {unique_id}: {emp_data.get('phone_number')}")
                
                # Generate CPF if not provided (for demo purposes)
                cpf = self.validate_cpf(emp_data.get('cpf', ''))
                if not cpf:
                    # Generate a dummy CPF for migration (you should provide real CPFs)
                    cpf = f"{unique_id:0>11}"[:11]
                    logger.warning(f"Generated dummy CPF for employee {unique_id}: {cpf}")
                
                # Create new employee
                new_employee = Employee(
                    unique_id=unique_id,
                    name=emp_data.get('full_name'),
                    cpf=cpf,
                    phone=phone or emp_data.get('phone_number', ''),
                    email=emp_data.get('email'),
                    department=emp_data.get('department'),
                    position=emp_data.get('position'),
                    company_code=emp_data.get('company_code'),
                    registration_number=emp_data.get('registration_number'),
                    sector=emp_data.get('sector'),
                    is_active=emp_data.get('is_active', True),
                    created_by=default_user_id,
                    updated_by=default_user_id
                )
                
                self.db.add(new_employee)
                self.db.flush()
                
                # Create audit log
                self.create_audit_log(
                    action="EMPLOYEE_MIGRATED",
                    entity_type="Employee",
                    entity_id=str(new_employee.id),
                    description=f"Migrated employee from JSON: {new_employee.name}",
                    user_id=default_user_id
                )
                
                self.stats['employees_migrated'] += 1
                logger.info(f"Migrated employee: {new_employee.name} (ID: {new_employee.id})")
                
            except Exception as e:
                logger.error(f"Error migrating employee {emp_data.get('unique_id', 'unknown')}: {e}")
                self.stats['errors'] += 1
                self.db.rollback()
    
    def create_default_admin(self):
        """Create default admin user if none exists"""
        admin_user = self.db.query(User).filter(User.is_admin == True).first()
        
        if not admin_user:
            logger.info("No admin user found, creating default admin")
            
            password_hash = pwd_context.hash("admin123")
            
            admin = User(
                username="admin",
                email="admin@enviafolha.local",
                full_name="Administrador do Sistema",
                password_hash=password_hash,
                is_active=True,
                is_admin=True
            )
            
            self.db.add(admin)
            self.db.flush()
            
            # Create audit log
            self.create_audit_log(
                action="ADMIN_CREATED",
                entity_type="User",
                entity_id=str(admin.id),
                description="Default admin user created during migration",
                user_id=admin.id
            )
            
            logger.info(f"Created default admin user: {admin.username}")
            return admin.id
        
        return admin_user.id
    
    def run_migration(self):
        """Run the complete migration process"""
        logger.info("=== Starting Data Migration ===")
        
        try:
            # Load JSON data
            data = self.load_json_data()
            if not data:
                logger.error("No data to migrate")
                return False
            
            # Start transaction
            self.db.begin()
            
            # Ensure we have an admin user
            self.create_default_admin()
            
            # Migrate users
            users_data = data.get('users', [])
            user_id_mapping = self.migrate_users(users_data)
            
            # Migrate employees
            employees_data = data.get('employees', [])
            self.migrate_employees(employees_data, user_id_mapping)
            
            # Create final audit log
            self.create_audit_log(
                action="MIGRATION_COMPLETED",
                entity_type="System",
                description=f"Migration completed: {self.stats['users_migrated']} users, {self.stats['employees_migrated']} employees",
                user_id=1
            )
            
            # Commit transaction
            self.db.commit()
            
            # Print results
            logger.info("=== Migration Complete ===")
            logger.info(f"Users migrated: {self.stats['users_migrated']}")
            logger.info(f"Employees migrated: {self.stats['employees_migrated']}")
            logger.info(f"Records skipped: {self.stats['skipped']}")
            logger.info(f"Errors: {self.stats['errors']}")
            
            return self.stats['errors'] == 0
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.db.rollback()
            return False
        
        finally:
            self.db.close()

def main():
    """Main entry point"""
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        logger.info("Please set DATABASE_URL or create a .env file")
        sys.exit(1)
    
    # Create migrator and run
    migrator = DataMigrator(database_url)
    success = migrator.run_migration()
    
    if success:
        logger.info("Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()