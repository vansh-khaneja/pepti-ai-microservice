# Redis Cache Integration

## Overview
Redis caching has been integrated into both chat endpoints to improve performance by avoiding expensive LLM calls and database searches for repeated queries.

## Configuration

### Environment Variables
Set these in your `.env` file:

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_DB=0
CACHE_TTL=3600
```

### Docker Setup
If using Docker, you can use Redis Cloud or add Redis to your docker-compose.yml:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

## How It Works

### Cache Flow
1. **Store User Message**: Always store user message in database first
2. **Check Cache**: Check if the query exists in Redis cache
3. **Cache Hit**: If found, store assistant response in database and return cached response
4. **Cache Miss**: If not found, proceed with normal workflow (database → LLM → Tavily)
5. **Cache Store**: Store the final response in Redis for future queries

**Important**: Messages are ALWAYS stored in the database for conversation history, regardless of cache hit/miss.

### Cache Keys
- **General queries**: `chat_cache:{hash}` (based on query only)
- **Specific peptide queries**: `chat_cache:{hash}` (based on query + peptide_name)

### Cache TTL
- Default: 1 hour (3600 seconds)
- Configurable via `CACHE_TTL` environment variable

## API Endpoints

### Chat Endpoints (with caching)
- `POST /api/v1/chat/search` - General search with caching
- `POST /api/v1/chat/query/{peptide_name}` - Specific peptide query with caching

### Cache Management Endpoints
- `GET /api/v1/chat/cache/stats` - Get cache statistics and Redis info
- `DELETE /api/v1/chat/cache/clear` - Clear all cached entries

## Response Format
Both endpoints now return an additional `cached` field:

```json
{
  "success": true,
  "message": "Search completed successfully",
  "data": {
    "llm_response": "...",
    "peptide_name": "...",
    "similarity_score": 0.85,
    "source": "qdrant",
    "session_id": "...",
    "timestamp": "2024-01-01T00:00:00"
  },
  "cached": false
}
```

## Testing
Run the test script to verify Redis integration:

```bash
python test_redis_cache.py
```

## Benefits
- **Performance**: Instant responses for repeated queries
- **Cost Reduction**: Fewer LLM API calls
- **Scalability**: Reduced database load
- **User Experience**: Faster response times

## Monitoring
Use the `/api/v1/chat/cache/stats` endpoint to monitor:
- Cache hit/miss ratios
- Memory usage
- Number of cached entries
- Redis connection status
