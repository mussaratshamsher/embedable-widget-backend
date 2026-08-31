# FlyRank AI Widget Backend

A multi-tenant FastAPI backend for an AI-powered embeddable website widget with lead capture and qualification using Groq LLM.

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── core/
│   │   ├── config.py          # Configuration from environment
│   │   ├── security.py        # JWT, password hashing, auth
│   │   └── exceptions.py      # Custom exception classes
│   ├── db/
│   │   ├── database.py        # SQLAlchemy engine and session
│   │   └── base.py            # Base model classes
│   ├── models/                # SQLAlchemy ORM models
│   ├── schemas/               # Pydantic request/response schemas
│   ├── api/                   # Route handlers
│   ├── services/              # Business logic layer
│   └── dependencies/          # FastAPI dependencies
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   ├── security/              # Security tests
│   └── e2e/                   # End-to-end tests
├── alembic/                   # Database migrations
├── Dockerfile                 # Container image
├── docker-compose.yml         # Local development environment
├── requirements.txt           # Python dependencies
├── pytest.ini                 # Pytest configuration
├── .env.example              # Example environment variables
└── README.md                  # This file
```

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Docker & Docker Compose (optional)
- Groq API key

### Setup with Docker (Recommended)

1. Clone the repository and navigate to the backend directory:
```bash
cd backend
```

2. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

3. Update `.env` with your Groq API key:
```
GROQ_API_KEY=your-actual-groq-key
```

4. Start the application:
```bash
docker-compose up
```

The API will be available at `http://localhost:8000`

### Setup Locally

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```bash
cp .env.example .env
```

4. Set up PostgreSQL and update `DATABASE_URL` in `.env`.

5. Run migrations (once implemented):
```bash
alembic upgrade head
```

6. Start the application:
```bash
uvicorn app.main:app --reload
```

## API Documentation

Once running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

## Testing the API via Swagger UI

1. Start the backend server:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Open Swagger UI in your browser:
   ```
   http://localhost:8000/docs
   ```

3. Follow these steps to test the complete workflow:

   ### Step 1: Register a User
   - Expand `POST /api/auth/register`
   - Click **Try it out**
   - Enter user details:
     ```json
     {
       "email": "test@example.com",
       "password": "testpassword123",
       "first_name": "Test",
       "last_name": "User"
     }
     ```
   - Click **Execute**
   - Copy the `access_token` from the response

   ### Step 2: Create an Organization
   - Expand `POST /api/organizations`
   - Click **Try it out**
   - Click the **Authorize** button at the top right and paste the `access_token`
   - Enter organization details:
     ```json
     {
       "name": "Test Organization",
       "slug": "test-org",
       "description": "Test organization"
     }
     ```
   - Click **Execute**
   - Copy the organization `id`

   ### Step 3: Create a Project
   - Expand `POST /api/projects`
   - Click **Try it out**
   - In the `organization_id` field, paste the organization ID
   - Enter project details:
     ```json
     {
       "name": "Test Project",
       "website_url": "https://example.com",
       "description": "Test project"
     }
     ```
   - Click **Execute**
   - Copy the project `api_key`

   ### Step 4: Create a Widget Session
   - Expand `POST /api/widget/session`
   - Click **Try it out**
   - Enter session details:
     ```json
     {
       "project_api_key": "paste-api-key-here",
       "visitor_identifier": "test_visitor_123"
     }
     ```
   - Click **Execute**
   - Copy the `visitor_id` and `conversation_id`

   ### Step 5: Send a Message
   - Expand `POST /api/widget/conversations/{conversation_id}/messages`
   - Click **Try it out**
   - Paste the `conversation_id` and `api_key`
   - Enter message content:
     ```json
     {
       "content": "Hello, I need help with your product"
     }
     ```
   - Click **Execute**

   ### Step 6: Get Conversation Messages
   - Expand `GET /api/widget/conversations/{conversation_id}/messages`
   - Click **Try it out**
   - Paste the `conversation_id` and `api_key`
   - Click **Execute**

   ### Step 7: View Leads (Admin)
   - Expand `GET /api/leads`
   - Click **Try it out**
   - Ensure you're authorized with the user token
   - Click **Execute**

## Environment Variables

See `.env.example` for all available configuration options.

### Key Variables
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET`: Secret key for JWT signing
- `GROQ_API_KEY`: API key for Groq LLM
- `CORS_ORIGINS`: Allowed CORS origins (JSON list)
- `ENVIRONMENT`: Environment (development/production)

## Development

### Running Tests

```bash
# All tests
pytest

# With coverage report
pytest --cov=app

# Specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/security/

# With live Groq API (requires GROQ_API_KEY)
RUN_LIVE_LLM_TESTS=true pytest
```

### Code Style

Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

## Implementation Status

Follow the development order in `Backend_Implementation_Plan.md`:

- [ ] Step 1: Foundation (FastAPI, PostgreSQL, Docker) - **IN PROGRESS**
- [ ] Step 2: Database (models, relationships, migrations)
- [ ] Step 3: Authentication
- [ ] Step 4: Multi-tenancy
- [ ] Step 5: Projects and widget configuration
- [ ] Step 6: Visitors, conversations, messages
- [ ] Step 7: Groq service and structured output
- [ ] Step 8: SSE chat endpoint
- [ ] Step 9: Lead qualification
- [ ] Step 10: Lead APIs
- [ ] Step 11-15: Testing, CI/CD, deployment

## Architecture

### Request Flow
```
HTTP Request
    ↓
FastAPI Route Handler
    ↓
Pydantic Schema Validation
    ↓
Service Layer (Business Logic)
    ↓
SQLAlchemy Models
    ↓
PostgreSQL Database
```

### AI Chat Flow
```
Chat Request
    ↓
Validate & Load Project Config
    ↓
Fetch Conversation History
    ↓
Build LLM Prompt
    ↓
Call Groq API
    ↓
Stream Response (SSE)
    ↓
Save Message to DB
    ↓
Extract & Qualify Lead
    ↓
Persist Lead
```

## Security

- Passwords hashed with bcrypt
- JWT tokens for authentication
- Multi-tenant isolation (all queries scoped to user's organization)
- CORS protection
- Rate limiting on public endpoints
- No stack traces or credentials in error responses
- HTTPS in production (via reverse proxy)

## Support

See `Backend_Implementation_Plan.md` for detailed requirements and specifications.

## License

Internal use only - FlyRank Hackathon Project - LeadForge: An embedable Widget
