from fastapi import APIRouter
from .endpoints import allowed_urls, chat_restrictions, search, peptides, chat, analytics

api_router = APIRouter()

# Include allowed URLs router
api_router.include_router(allowed_urls.router, prefix="/allowed-urls", tags=["allowed-urls"])

# Include chat restrictions router
api_router.include_router(chat_restrictions.router, prefix="/chat-restrictions", tags=["chat-restrictions"])

# Include search router
api_router.include_router(search.router, prefix="/search", tags=["search"])

# Include peptides router
api_router.include_router(peptides.router, prefix="/peptides", tags=["peptides"])

# Include chat router
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

# Include analytics router
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

@api_router.get("/")
async def api_root():
    """API root endpoint"""
    return {"message": "API v1 is active", "endpoints": ["/allowed-urls", "/chat-restrictions", "/search", "/peptides", "/chat", "/analytics"]}
