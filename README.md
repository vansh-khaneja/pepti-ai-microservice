# Pepti Wiki AI

An intelligent AI-powered peptide information and search API built with FastAPI, featuring vector similarity search, web integration, and comprehensive cost tracking.

## 🚀 Features

- **AI-Powered Chat**: Intelligent peptide chatbot with context-aware responses
- **Vector Search**: Advanced peptide discovery using Qdrant vector database
- **Web Integration**: Real-time web search with SerpAPI and Tavily
- **Cost Tracking**: Comprehensive analytics and cost monitoring
- **Database Migrations**: Modern Alembic-based migration system
- **Redis Caching**: High-performance caching for improved response times
- **Admin Dashboard**: Complete analytics and management interface

## 🏗️ Architecture

### Tech Stack
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (cloud-hosted)
- **Vector DB**: Qdrant Cloud (cosine similarity)
- **AI/LLM**: OpenAI (GPT-4o-mini, text-embedding-3-small)
- **Web Search**: SerpAPI + Tavily API
- **Caching**: Redis
- **Migrations**: Alembic

### Core Components
- **Chat System**: Multi-workflow chatbot with smart routing
- **Peptide Database**: Vector-based peptide information storage
- **Web Search**: Intelligent content scraping and processing
- **Analytics**: Comprehensive usage and cost tracking
- **Admin Panel**: Management and monitoring interface

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL database (cloud recommended)
- Qdrant Cloud account
- OpenAI API key
- SerpAPI key
- Tavily API key
- Redis server (optional, for caching)

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/pepti-wiki-ai.git
cd pepti-wiki-ai
```

### 2. Create Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the project root:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Database Configuration (Cloud PostgreSQL)
DATABASE_URL=postgresql+asyncpg://username:password@your-cloud-host:5432/pepti_wiki
DATABASE_NAME=pepti_wiki

# Qdrant Configuration (Cloud)
QDRANT_URL=https://your-cluster-id.eu-west-1-0.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key_here
PEPTIDE_COLLECTION=peptides

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_DB=0
CACHE_TTL=3600

# API Keys
OPENAI_API_KEY=your_openai_api_key_here
SERP_API_KEY=your_serp_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Pricing Configuration
SERPAPI_DEVELOPER_PLAN_PRICE=0.015
OPENAI_GPT4O_INPUT_PRICE=0.005
OPENAI_GPT4O_OUTPUT_PRICE=0.015
OPENAI_GPT4O_MINI_INPUT_PRICE=0.00015
OPENAI_GPT4O_MINI_OUTPUT_PRICE=0.0006
OPENAI_EMBEDDING_3_LARGE_PRICE=0.00013
OPENAI_EMBEDDING_3_SMALL_PRICE=0.00002
OPENAI_EMBEDDING_ADA002_PRICE=0.0001
TAVILY_BASIC_SEARCH_PRICE=0.001
TAVILY_ADVANCED_SEARCH_PRICE=0.002

# CORS Configuration
ALLOWED_HOSTS=["*"]
```

## 🗄️ Database Setup

### 1. Cloud PostgreSQL Setup

#### Option A: Neon (Recommended - Free tier available)
1. Sign up at [Neon](https://neon.tech/)
2. Create a new project
3. Copy the connection string
4. Update your `.env` file

#### Option B: Supabase
1. Sign up at [Supabase](https://supabase.com/)
2. Create a new project
3. Go to Settings > Database
4. Copy the connection string

### 2. Database Migration

#### Using Migration Script (Recommended)
```bash
# Initialize database with migrations
python migrate_db.py init

# Create new migration after model changes
python migrate_db.py create -m "Add new fields to user table"

# Upgrade database to latest
python migrate_db.py upgrade

# Show current revision
python migrate_db.py current

# Show migration history
python migrate_db.py history
```

#### Direct Alembic Commands
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Show current status
alembic current
```

## 🔍 Vector Database Setup

### Qdrant Cloud Setup
1. Sign up at [Qdrant Cloud](https://cloud.qdrant.io/)
2. Create a new cluster
3. Note down your cluster URL and API key
4. Update your `.env` file with the credentials

### Collection Configuration
- **Collection Name**: `peptides`
- **Vector Size**: 768 (OpenAI embeddings truncated)
- **Distance Metric**: Cosine similarity
- **Payload Fields**: name, overview, mechanism_of_actions, potential_research_fields, text_content

## 🚀 Running the Application

### Development Mode
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### With Docker
```bash
docker-compose up -d
```

## 📚 API Documentation

Once running, access the interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 Core Workflows

### 1. General Chatbot Workflow
```
User Query → Generate Embedding → Search Qdrant → 
If Found: Use Database Result → Generate AI Response
If Not Found: Trigger Web Search → Process Content → Generate AI Response
```

### 2. Peptide-Specific Chat Workflow
```
Specific Peptide Query → Extract Name → Search Qdrant by Name → 
Get Peptide Details → Generate Comprehensive Response
```

### 3. Web Search Integration Workflow
```
Low Confidence Result → SerpAPI Search → Scrape Content → 
Chunk Processing → Embedding Generation → Similarity Calculation → 
AI Response Generation with Source Citations
```

### 4. Advanced Peptide Info Generation
```
Peptide Name + Requirements → Tavily Search → Accuracy Assessment → 
If High Accuracy: LLM Tuning → Database Storage → Response
If Low Accuracy: SerpAPI Fallback → Scraping → LLM Processing → Response
```

## 📊 Admin Dashboard

### Access Admin Dashboard
- **URL**: `GET /api/v1/admin-dashboard`
- **Features**: 
  - Chat restrictions management
  - Allowed URLs management
  - Daily/Weekly/Monthly analytics
  - Cost tracking and analysis
  - Server information

### Cost Analytics
- **Daily Cost Trends**: `GET /api/v1/admin-dashboard/cost-analytics`
- **Top Costing Services**: `GET /api/v1/admin-dashboard/top-costing-services`
- **Cost Summary**: `GET /api/v1/admin-dashboard/cost-summary`

## 🔄 Caching System

### Redis Integration
- **Cache Keys**: `chat_cache:{hash}` (based on query + peptide_name)
- **TTL**: 1 hour (configurable via `CACHE_TTL`)
- **Cache Flow**: Always store in database, cache for performance

### Cache Management
- **Stats**: `GET /api/v1/chat/cache/stats`
- **Clear Cache**: `DELETE /api/v1/chat/cache/clear`

## 🛡️ Security Features

### Chat Restrictions
- No medical advice/dosage recommendations
- Avoid illegal/controlled substance guidance
- Encourage professional consultation
- Configurable via admin dashboard

### Allowed URLs
- Admin-managed domain allowlist
- Web search results filtered by allowed domains
- Prevents scraping of unauthorized sites

## 📈 Analytics & Monitoring

### Endpoint Usage Tracking
- Request/response logging
- Performance metrics
- Error tracking
- Cost calculation per API call

### External API Usage
- OpenAI token usage tracking
- SerpAPI request tracking
- Qdrant operation monitoring
- Tavily API usage analytics

## 🚀 Deployment

### Production Deployment (Hostinger)

#### 1. Server Setup
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y python3.11 python3.11-pip python3.11-venv git curl wget nginx

# Install system dependencies
sudo apt install -y gcc g++ libpq-dev
```

#### 2. Application Deployment
```bash
# Clone repository
git clone https://github.com/yourusername/pepti-wiki-ai.git
cd pepti-wiki-ai

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python migrate_db.py init
```

#### 3. Nginx Configuration
Create `/etc/nginx/sites-available/pepti-wiki`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 4. Systemd Service
Create `/etc/systemd/system/pepti-wiki.service`:
```ini
[Unit]
Description=Pepti Wiki AI FastAPI Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/pepti-wiki-ai
Environment=PATH=/path/to/your/pepti-wiki-ai/venv/bin
ExecStart=/path/to/your/pepti-wiki-ai/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

#### 5. SSL Certificate
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## 🔧 Configuration

### Environment Variables
| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `QDRANT_URL` | Qdrant cluster URL | Yes | - |
| `QDRANT_API_KEY` | Qdrant API key | Yes | - |
| `OPENAI_API_KEY` | OpenAI API key | Yes | - |
| `SERP_API_KEY` | SerpAPI key | Yes | - |
| `TAVILY_API_KEY` | Tavily API key | Yes | - |
| `REDIS_URL` | Redis connection string | No | `redis://localhost:6379` |
| `CACHE_TTL` | Cache TTL in seconds | No | `3600` |
| `CONFIDENCE_SCORE` | Minimum confidence threshold | No | `70` |
| `MIN_VECTOR_SIMILARITY` | Vector similarity threshold | No | `0.35` |

### Pricing Configuration
All pricing is configurable via environment variables:
- OpenAI model pricing (per 1K tokens)
- SerpAPI pricing (per request)
- Tavily pricing (per request)
- Qdrant pricing (currently free tier)

## 📝 API Endpoints

### Chat Endpoints
- `POST /api/v1/chat/search` - General peptide search
- `POST /api/v1/chat/query/{peptide_name}` - Specific peptide query
- `GET /api/v1/chat/sessions` - List chat sessions
- `GET /api/v1/chat/sessions/{session_id}` - Get session history

### Peptide Endpoints
- `GET /api/v1/peptides/search` - Search peptides by query
- `GET /api/v1/peptides/{peptide_name}` - Get specific peptide info
- `GET /api/v1/peptides/similar/{peptide_name}` - Get similar peptides
- `POST /api/v1/peptides` - Add new peptide

### Peptide Info Generation
- `POST /api/v1/peptide-info/generate` - Generate comprehensive peptide info
- `GET /api/v1/peptide-info/sessions` - List peptide info sessions
- `GET /api/v1/peptide-info/sessions/{session_id}` - Get session details

### Search Endpoints
- `POST /api/v1/search/peptide` - Web search for peptide information
- `GET /api/v1/search/sources` - Get search sources

### Admin Endpoints
- `GET /api/v1/admin-dashboard` - Complete admin dashboard data
- `GET /api/v1/admin-dashboard/cost-analytics` - Cost analytics
- `GET /api/v1/admin-dashboard/top-costing-services` - Top costing services
- `GET /api/v1/admin-dashboard/cost-summary` - Cost summary

### Management Endpoints
- `GET /api/v1/chat-restrictions` - List chat restrictions
- `POST /api/v1/chat-restrictions` - Add chat restriction
- `DELETE /api/v1/chat-restrictions` - Remove chat restriction
- `GET /api/v1/allowed-urls` - List allowed URLs
- `POST /api/v1/allowed-urls` - Add allowed URL
- `DELETE /api/v1/allowed-urls/{url_id}` - Remove allowed URL

### Analytics Endpoints
- `GET /api/v1/analytics/daily` - Daily usage analytics
- `GET /api/v1/analytics/weekly` - Weekly usage analytics
- `GET /api/v1/analytics/monthly` - Monthly usage analytics
- `GET /api/v1/analytics/external-api-summary` - External API usage summary

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### Test Chat Endpoint
```bash
curl -X POST "http://localhost:8000/api/v1/chat/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "What peptides help with muscle recovery?"}'
```

### Test Peptide Search
```bash
curl "http://localhost:8000/api/v1/peptides/search?query=BPC-157"
```

## 🔍 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Test database connection
python -c "
import psycopg2
try:
    conn = psycopg2.connect('your_database_url_here')
    print('Database connection successful')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

#### Application Won't Start
```bash
# Check service status
sudo systemctl status pepti-wiki

# Check logs
sudo journalctl -u pepti-wiki -n 50

# Test manually
cd /path/to/your/project
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Migration Issues
```bash
# Check current revision
python migrate_db.py current

# Show migration history
python migrate_db.py history

# Force upgrade
alembic upgrade head
```

## 📊 Performance Optimization

### Production Recommendations
1. **Use Gunicorn**: For production deployment
2. **Enable Redis Caching**: For improved response times
3. **Database Connection Pooling**: Configure proper pool settings
4. **CDN**: Use CDN for static assets
5. **Monitoring**: Set up proper logging and monitoring

### Scaling Considerations
- **Horizontal Scaling**: Multiple application instances behind load balancer
- **Database Scaling**: Use managed PostgreSQL with read replicas
- **Vector DB Scaling**: Qdrant Cloud handles scaling automatically
- **Caching Strategy**: Redis clustering for high availability

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
1. Check the [troubleshooting section](#troubleshooting)
2. Review the [API documentation](http://localhost:8000/docs)
3. Open an issue on GitHub
4. Contact the development team

## 🔄 Changelog

### Version 1.0.0
- Initial release with core functionality
- AI-powered peptide chatbot
- Vector similarity search
- Web search integration
- Cost tracking and analytics
- Admin dashboard
- Database migration system
- Redis caching integration

---

**Built with ❤️ for the peptide research community**