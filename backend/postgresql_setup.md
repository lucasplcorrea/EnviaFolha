# PostgreSQL Database Setup for EnviaFolha v2.0

## Overview
This document details the complete PostgreSQL setup for the EnviaFolha application migration from JSON storage to a proper database.

## Quick Start

### 1. Start PostgreSQL with Docker
```bash
cd backend
docker-compose up -d postgres
```

### 2. Run Database Migrations
```bash
# Update alembic.ini to use PostgreSQL (set DATABASE_URL env var)
export DATABASE_URL="postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db"

# Run migrations
alembic upgrade head
```

### 3. Migrate Existing Data
```bash
python migrate_json_to_postgres.py
```

## Configuration

### Environment Variables
Create a `.env` file in the backend directory:

```env
DATABASE_URL=postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=enviafolha_db
DB_USER=enviafolha_user
DB_PASSWORD=secure_password
```

### Alembic Configuration
The `alembic.ini` file is configured to use the DATABASE_URL environment variable:

```ini
sqlalchemy.url = %(DATABASE_URL)s
```

## Database Schema

### Core Tables

1. **users** - User authentication and management
   - Primary admin/user access control
   - Last login tracking
   - Password hashing with bcrypt

2. **employees** - Employee master data
   - Unique identifiers for payroll matching
   - Phone number validation
   - Audit trail with created_by/updated_by

3. **audit_logs** - Full system audit trail
   - User actions tracking
   - Entity changes with before/after data
   - IP address and user agent logging

4. **payroll_sends** - Payroll transmission history
   - File path tracking
   - Send status and error logging
   - Monthly organization

5. **communication_sends** - Bulk communication campaigns
   - Message templates and file attachments
   - Progress tracking (total/successful/failed)
   - Status workflow management

6. **communication_recipients** - Individual send results
   - Per-employee delivery status
   - Error message tracking
   - Relationship to parent campaign

7. **system_settings** - Application configuration
   - Type-safe value storage (string/integer/boolean/json)
   - Category organization
   - Public/admin/private access levels

### Indexes and Performance

- All primary keys have automatic indexes
- Unique constraints on critical business fields (username, email, cpf, unique_id)
- Foreign key indexes for relationship performance
- Timestamp columns for audit and reporting queries

### Security Features

- Password hashing with bcrypt
- Audit trail for all critical operations
- User session tracking
- Role-based access control (admin/user)

## Migration Process

### From JSON to PostgreSQL

The migration script (`migrate_json_to_postgres.py`) handles:

1. **User Data Migration**
   - Imports existing users with password hash preservation
   - Creates default admin user if none exists
   - Maps old user IDs to new primary keys

2. **Employee Data Migration**
   - Validates and imports employee records
   - Phone number format validation
   - CPF validation and formatting
   - Unique ID conflict resolution

3. **Data Validation**
   - Constraint checking before import
   - Duplicate detection and handling
   - Missing field completion with defaults

4. **Audit Trail Creation**
   - Initial system setup audit logs
   - Data migration tracking
   - User action attribution

## Maintenance

### Backup Strategy
```bash
# Daily backup
pg_dump -h localhost -U enviafolha_user enviafolha_db > backup_$(date +%Y%m%d).sql

# Restore from backup
psql -h localhost -U enviafolha_user enviafolha_db < backup_20231003.sql
```

### Performance Monitoring
```sql
-- Check table sizes
SELECT schemaname,tablename,attname,n_distinct,correlation FROM pg_stats WHERE schemaname = 'public';

-- Monitor slow queries
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

### Schema Updates
Always use Alembic for schema changes:

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Check current version
alembic current
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if PostgreSQL container is running
   - Verify port 5432 is not blocked
   - Confirm credentials in .env file

2. **Migration Conflicts**
   - Use `alembic history` to check migration order
   - Reset with `alembic downgrade base` and `alembic upgrade head`

3. **Data Import Errors**
   - Check employee.json format
   - Validate phone numbers and CPF format
   - Review audit logs for detailed error information

### Performance Tuning

For production deployments:

```sql
-- Analyze tables after data import
ANALYZE;

-- Update statistics
VACUUM ANALYZE;

-- Monitor index usage
SELECT schemaname, tablename, attname, n_distinct FROM pg_stats WHERE schemaname = 'public';
```

## Production Deployment

### Docker Compose Configuration
The included `docker-compose.yml` provides:

- PostgreSQL 16 with optimized settings
- Persistent volume mounting
- Health checks
- Environment variable configuration
- Network isolation

### Security Considerations

1. **Database Access**
   - Use strong passwords (generated)
   - Limit network access to application servers
   - Enable SSL/TLS for connections

2. **Application Security**
   - JWT token configuration
   - Rate limiting on API endpoints
   - Input validation on all user data

3. **Audit Compliance**
   - All user actions logged
   - Data change tracking
   - Export capabilities for compliance reporting

This setup provides a robust, scalable foundation for the EnviaFolha application with proper data management, security, and audit capabilities.