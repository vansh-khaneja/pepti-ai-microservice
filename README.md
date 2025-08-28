# Pepti Wiki AI

An AI-powered peptide information and search API that combines vector search with large language models to provide intelligent answers about peptides.

## Features

- **Peptide Management**: Store and manage peptide information (name, overview, mechanism of actions, potential research fields)
- **Vector Search**: Semantic search using Qdrant vector database
- **AI-Powered Queries**: Get intelligent answers about specific peptides using OpenAI GPT models
- **General Search**: Find relevant peptides and get AI-generated answers based on similarity
- **Web Search & Scraping**: Search the web for peptide information using SerpAPI and intelligent content processing
- **Recommendations**: Find similar peptides based on vector similarity
- **Analytics**: Track API endpoint usage with comprehensive analytics
- **Chat Restrictions**: Enforce LLM behavior rules and content restrictions
- **URL Management**: Control which URLs can be accessed during web searches

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (external hosted - Neon, Supabase, Railway, etc.)
- **Vector Database**: Qdrant Cloud
- **AI Models**: OpenAI GPT-4o-mini, text-embedding-3-small
- **Web Search**: SerpAPI for intelligent web scraping
- **Containerization**: Docker & Docker Compose
- **Authentication**: Environment-based API keys

## Prerequisites

- Python 3.11+
- PostgreSQL database (external hosted)
- Qdrant Cloud instance
- OpenAI API key
- SerpAPI key (for web search functionality)

## Quick Start

### Option 1: Local Development

#### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd pepti-wiki-ai

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\Activate.ps1
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Environment Configuration
```bash
# Copy environment template
cp env.example .env

# Edit .env with your actual values
nano .env  # or use your preferred editor
```

#### 3. Configure External Services

**External PostgreSQL Database:**
```env
# Neon Database Example:
DATABASE_URL=postgresql://username:password@ep-xxx-xxx-xxx.region.aws.neon.tech/dbname?sslmode=require
DATABASE_NAME=your_database_name

# Supabase Example:
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
DATABASE_NAME=postgres

# Railway Example:
DATABASE_URL=postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway
DATABASE_NAME=railway
```

**Other Services:**
```env
# Qdrant Vector Database
QDRANT_URL=https://your-qdrant-instance.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key
PEPTIDE_COLLECTION=peptides

# API Keys
OPENAI_API_KEY=your_openai_api_key
SERP_API_KEY=your_serp_api_key

# Server Settings
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

#### 4. Run Locally
```bash
# Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python directly
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Docker Deployment

#### 1. Environment Setup
```bash
# Copy environment template
cp env.example .env

# Edit .env with your actual values
nano .env
```

#### 2. Build and Run with Docker
```bash
# Build and start the application
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop the application
docker-compose down

# Restart the application
docker-compose restart
```

#### 3. Manual Docker Commands
```bash
# Build the image
docker build -t pepti-wiki-ai .

# Run the container
docker run -d \
  --name pepti-wiki-app \
  -p 8000:8000 \
  --env-file .env \
  pepti-wiki-ai

# View logs
docker logs -f pepti-wiki-app

# Stop container
docker stop pepti-wiki-app
```

## API Endpoints

### Root Endpoints
- **Root**: `GET /` - Welcome message and API status
- **Health Check**: `GET /health` - Service health status
- **API Documentation**: `GET /docs` - Interactive API documentation (Swagger UI)
- **OpenAPI Schema**: `GET /openapi.json` - OpenAPI specification

### API v1 Endpoints

#### Peptide Management (`/api/v1/peptides/`)
- **Create Peptide**: `POST /api/v1/peptides/` - Add new peptide to vector database
- **Delete Peptide**: `DELETE /api/v1/peptides/{peptide_name}` - Remove peptide by name
- **Get Recommendations**: `GET /api/v1/peptides/recommendations/{peptide_name}` - Find similar peptides

#### Chat & AI Queries (`/api/v1/chat/`)
- **General Search**: `POST /api/v1/chat/search` - AI-powered peptide search with vector similarity
- **Specific Peptide Query**: `POST /api/v1/chat/query/{peptide_name}` - Query specific peptide with AI

#### Web Search & Scraping (`/api/v1/search/`)
- **Peptide Web Search**: `POST /api/v1/search/peptide` - Search web for peptide information using SerpAPI

#### Analytics (`/api/v1/analytics/`)
- **Daily Usage**: `GET /api/v1/analytics/daily?days=7` - Daily API usage statistics
- **Weekly Usage**: `GET /api/v1/analytics/weekly?weeks=4` - Weekly API usage statistics
- **Monthly Usage**: `GET /api/v1/analytics/monthly?months=6` - Monthly API usage statistics

#### URL Management (`/api/v1/allowed-urls/`)
- **Add Allowed URL**: `POST /api/v1/allowed-urls/` - Add URL to allowed scraping list
- **List Allowed URLs**: `GET /api/v1/allowed-urls/` - Get all allowed URLs
- **Delete Allowed URL**: `DELETE /api/v1/allowed-urls/{url_id}` - Remove URL from allowed list

#### Chat Restrictions (`/api/v1/chat-restrictions/`)
- **Add Restriction**: `POST /api/v1/chat-restrictions/` - Add new LLM behavior restriction
- **List Restrictions**: `GET /api/v1/chat-restrictions/` - Get all chat restrictions
- **Delete Restriction**: `DELETE /api/v1/chat-restrictions/{restriction_text}` - Remove restriction by text

## Usage Examples

### 1. Create a Peptide
```bash
curl -X POST "http://localhost:8000/api/v1/peptides/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "BPC-157",
    "overview": "A synthetic peptide with regenerative properties",
    "mechanism_of_actions": "Promotes tissue repair and regeneration",
    "potential_research_fields": "Wound healing, tissue regeneration, anti-inflammatory"
  }'
```

### 2. Query a Specific Peptide
```bash
curl -X POST "http://localhost:8000/api/v1/chat/query/BPC-157" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main benefits of BPC-157?"
  }'
```

### 3. General Peptide Search
```bash
curl -X POST "http://localhost:8000/api/v1/chat/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What peptides are good for muscle recovery?"
  }'
```

### 4. Web Search for Peptide Information
```bash
curl -X POST "http://localhost:8000/api/v1/search/peptide" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "BPC-157 research studies benefits"
  }'
```

### 5. Get Similar Peptides
```bash
curl -X GET "http://localhost:8000/api/v1/peptides/recommendations/BPC-157"
```

### 6. Add Chat Restriction
```bash
curl -X POST "http://localhost:8000/api/v1/chat-restrictions/" \
  -H "Content-Type: application/json" \
  -d '{
    "restriction_text": "Do not provide medical advice or dosage recommendations"
  }'
```

### 7. Add Allowed URL
```bash
curl -X POST "http://localhost:8000/api/v1/allowed-urls/" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "description": "Trusted peptide research site"
  }'
```

## Project Structure

```
pepti-wiki-ai/
├── app/                           # Main application code
│   ├── __init__.py               # Package initialization
│   ├── main.py                   # FastAPI application entry point
│   │
│   ├── api/                      # API layer
│   │   ├── __init__.py
│   │   └── v1/                   # API version 1
│   │       ├── __init__.py
│   │       ├── router.py         # Main API router configuration
│   │       └── endpoints/        # API endpoint implementations
│   │           ├── __init__.py
│   │           ├── allowed_urls.py      # URL management endpoints
│   │           ├── analytics.py         # Analytics endpoints
│   │           ├── chat.py              # Chat and AI query endpoints
│   │           ├── chat_restrictions.py # Chat restriction management
│   │           ├── peptides.py          # Peptide CRUD operations
│   │           └── search.py            # Web search and scraping endpoints
│   │
│   ├── core/                     # Core application components
│   │   ├── __init__.py
│   │   ├── config.py             # Settings and environment variables
│   │   ├── database.py           # Database connection and initialization
│   │   └── exceptions.py         # Custom exception classes
│   │
│   ├── middleware/               # FastAPI middleware
│   │   ├── __init__.py
│   │   └── analytics_middleware.py  # API usage tracking middleware
│   │
│   ├── models/                   # Data models and schemas
│   │   ├── __init__.py           # Model exports
│   │   ├── allowed_url.py        # URL management models
│   │   ├── analytics.py          # Analytics data models
│   │   ├── base.py               # Base model classes
│   │   ├── chat_restriction.py   # Chat restriction models
│   │   ├── peptide.py            # Peptide data models
│   │   └── search.py             # Search and scraping models
│   │
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   ├── allowed_url_service.py    # URL management business logic
│   │   ├── analytics_service.py      # Analytics processing
│   │   ├── chat_restriction_service.py # Chat restriction management
│   │   ├── peptide_service.py        # Peptide operations and AI queries
│   │   ├── qdrant_service.py         # Vector database operations
│   │   └── search_service.py         # Web search and content processing
│   │
│   └── utils/                    # Utility functions and helpers
│       ├── __init__.py
│       └── helpers.py            # Common utility functions
│
├── .dockerignore                 # Docker ignore file
├── .gitignore                    # Git ignore file
├── Dockerfile                    # Docker image configuration
├── docker-compose.yml            # Docker Compose configuration
├── requirements.txt              # Python dependencies
├── env.example                   # Environment variables template
├── venv/                         # Python virtual environment
└── README.md                     # This file
```

## Component Details

### API Layer (`app/api/`)
- **Router Configuration**: Centralized endpoint registration and URL prefixing
- **Endpoint Separation**: Each domain has its own endpoint file for maintainability
- **Request/Response Models**: Consistent API contract using Pydantic models

### Core Layer (`app/core/`)
- **Configuration Management**: Environment-based settings with validation
- **Database Connection**: PostgreSQL connection pooling and initialization
- **Exception Handling**: Custom exception classes for consistent error responses

### Models Layer (`app/models/`)
- **SQLAlchemy Models**: Database table definitions and relationships
- **Pydantic Schemas**: API request/response validation and serialization
- **Data Validation**: Input/output data validation and transformation

### Services Layer (`app/services/`)
- **Business Logic**: Core application functionality implementation
- **External Integrations**: OpenAI API, Qdrant, SerpAPI integrations
- **Data Processing**: Content scraping, chunking, and similarity search

### Middleware (`app/middleware/`)
- **Analytics Tracking**: Automatic API usage monitoring and logging
- **Request Processing**: Pre/post request processing and logging

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `DATABASE_NAME` | Database name | Yes | - |
| `QDRANT_URL` | Qdrant vector database URL | Yes | - |
| `QDRANT_API_KEY` | Qdrant API key | Yes | - |
| `OPENAI_API_KEY` | OpenAI API key | Yes | - |
| `SERP_API_KEY` | SerpAPI key for web search | Yes | - |
| `PEPTIDE_COLLECTION` | Qdrant collection name | No | `peptides` |
| `HOST` | Server host | No | `0.0.0.0` |
| `PORT` | Server port | No | `8000` |
| `DEBUG` | Debug mode | No | `false` |
| `ALLOWED_HOSTS` | CORS allowed origins | No | `["*"]` |

### Database Tables

The application automatically creates these tables on startup:
- `allowed_urls` - URLs allowed for web scraping
- `chat_restrictions` - LLM behavior restrictions
- `endpoint_usage` - API usage analytics

## Development

### Adding New Endpoints

1. Create endpoint file in `app/api/v1/endpoints/`
2. Add to router in `app/api/v1/router.py`
3. Create corresponding service in `app/services/`
4. Add models in `app/models/` if needed
5. Update this README with endpoint documentation

### Adding New Models

1. Create SQLAlchemy model in `app/models/`
2. Create Pydantic schemas in the same file
3. Update `app/models/__init__.py`
4. Add to database initialization in `app/core/database.py`



## Troubleshooting

### Common Issues

#### Database Connection Failed
```
Database initialization failed: connection to server failed
```
**Solution**: Check your `DATABASE_URL` and ensure the external PostgreSQL service is accessible.

#### Qdrant Connection Error
```
Failed to connect to Qdrant: connection refused
```
**Solution**: Verify your `QDRANT_URL` and `QDRANT_API_KEY` are correct.

#### Port Already in Use
```
Error: Port 8000 is already in use
```
**Solution**: Change the port in configuration or stop the conflicting service.

#### Environment Variables Not Loaded
```
Environment variable not found
```
**Solution**: Ensure your `.env` file exists and contains all required variables.

### Debug Mode

Enable debug mode for more detailed logging:
```env
DEBUG=true
```

### Logs

```bash
# Local development
# Check console output

# Docker
docker-compose logs -f app
docker logs -f pepti-wiki-app
```

## Support

For issues and questions:
- Check the troubleshooting section
- Review application logs
- Check health endpoints
- Verify external service connectivity
