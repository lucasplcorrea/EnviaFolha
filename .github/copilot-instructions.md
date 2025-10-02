# Copilot Instructions - Sistema de Envio RH v2.0

## Project Overview
This is a WhatsApp HR automation system for sending payroll slips and communications using Evolution API. The system has a React frontend, FastAPI backend, and integrates with WhatsApp Business via Evolution API.

## Architecture & Core Components

### Stack
- **Backend**: FastAPI + SQLAlchemy + Python 3.11-3.13
- **Frontend**: React 18 + Tailwind CSS + React Query
- **Database**: SQLite (development) / PostgreSQL (production)
- **WhatsApp Integration**: Evolution API v2.2.2+
- **Authentication**: JWT tokens with role-based access

### Key Directories
```
backend/app/
├── core/           # Config, auth, and cross-cutting concerns
├── models/         # SQLAlchemy ORM models
├── schemas/        # Pydantic request/response schemas  
├── services/       # Business logic and external API integrations
└── migrations/     # Database migrations

frontend/src/
├── components/     # Reusable UI components
├── pages/         # Route-based page components
├── contexts/      # React contexts (AuthContext)
└── services/      # API client utilities
```

## Critical Workflows

### Environment Setup
- Use `python setup_environment.py` for Python 3.13 compatibility handling
- Use `python start_project.py` for full project startup (both backend and frontend)
- Docker Compose available with PostgreSQL for production-like development

### Development Commands
```bash
# Backend development
cd backend && uvicorn main:app --reload

# Frontend development  
cd frontend && npm start

# Full stack with Docker
docker-compose up --build
```

### Database Management
- SQLAlchemy models auto-create tables on startup via `Base.metadata.create_all()`
- No explicit migration system - uses declarative model changes
- Employee model uses `unique_id` field for payroll matching (not primary key `id`)

## Project-Specific Patterns

### Evolution API Integration
- **Service Pattern**: `EvolutionAPIService` class handles all WhatsApp communication
- **Rate Limiting**: Built-in random delays (30±10 seconds) between message sends
- **File Handling**: PDF files converted to base64 for API transmission
- **Phone Validation**: Uses `phonenumbers` library with Brazilian (+55) format defaults

### Authentication & Security
- JWT tokens with configurable expiration (default 30 minutes)
- Role-based access (admin/user permissions)
- All API routes require authentication except `/auth/login`
- Frontend uses `AuthContext` with automatic token refresh

### File Processing Workflows
- **Payroll PDFs**: Auto-segmented by employee unique_id, password-protected with first 4 CPF digits
- **Upload Flow**: `uploads/` → `processed/` → `enviados/` (sent files)
- **Communication Files**: Support multiple formats (PDF, images) with flexible recipient selection

### Error Handling & Logging
- Structured logging with timestamps and levels
- Failed sends tracked in `failed_employees` arrays
- Status management via `StatusManager` class for long-running operations
- Frontend uses `react-hot-toast` for user notifications

### Database Patterns
- **Models**: Use both `TimestampMixin` (created_at, updated_at) and declarative base
- **Relationships**: SQLAlchemy ORM with back_populates for bidirectional relations
- **Unique Constraints**: Employee `unique_id` is the business key, not auto-increment `id`

### Frontend State Management
- React Query for server state management and caching
- Context API for authentication state
- Hook-based form handling with `react-hook-form`
- Tailwind CSS with custom component patterns

## Integration Points

### Evolution API Configuration
Required environment variables in `.env`:
```
EVOLUTION_SERVER_URL=https://your-api.com
EVOLUTION_API_KEY=your-api-key
EVOLUTION_INSTANCE_NAME=your-instance
```

### Phone Number Format
- Expects Brazilian format: +55 (area code) number
- Validation via `PhoneValidator` service class
- WhatsApp availability checking before sending

### File Upload Constraints
- Max file size: 25MB (configurable via `MAX_FILE_SIZE`)
- Supported formats: PDF, JPG, PNG for communications
- Payroll files must be PDF format only

## Development Conventions

### Code Organization
- Services contain business logic, models are data-only
- Async/await patterns for external API calls
- Type hints required for service methods
- Pydantic schemas for all API request/response validation

### Error Patterns
- Use HTTP exceptions with descriptive messages
- Log errors before raising exceptions
- Return structured error responses with details
- Frontend displays user-friendly error messages via toast notifications

### Testing Considerations
- No existing test suite - consider adding pytest for backend
- Frontend components use standard React patterns suitable for testing
- Evolution API calls should be mocked in tests
- Database operations use SQLAlchemy session management

When making changes, prioritize maintaining the existing error handling patterns and ensure Evolution API rate limiting is preserved to avoid WhatsApp Business policy violations.