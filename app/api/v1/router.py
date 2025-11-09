from fastapi import APIRouter
from .endpoints import allowed_urls, chat_restrictions, search, peptides, chat, analytics, admin_dashboard, peptide_info, tavily_toggle

api_router = APIRouter()

# Include allowed URLs router
api_router.include_router(allowed_urls.router, prefix="/allowed-urls", tags=["allowed-urls"])

# Include chat restrictions router
api_router.include_router(chat_restrictions.router, prefix="/chat-restrictions", tags=["chat-restrictions"])

# Include Tavily toggle router
api_router.include_router(tavily_toggle.router, prefix="/tavily-toggle", tags=["tavily-toggle"])

# Include search router
api_router.include_router(search.router, prefix="/search", tags=["search"])

# Include peptides router
api_router.include_router(peptides.router, prefix="/peptides", tags=["peptides"])

# Include chat router
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

# Include analytics router
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

# Include admin dashboard router
api_router.include_router(admin_dashboard.router, prefix="", tags=["admin-dashboard"])

# Include peptide info router
api_router.include_router(peptide_info.router, prefix="/peptide-info", tags=["peptide-info"])

@api_router.get("/")
async def api_root():
    """API root endpoint"""
    return {"message": "API v1 is active", "endpoints": ["/allowed-urls", "/chat-restrictions", "/tavily-toggle", "/search", "/peptides", "/chat", "/analytics", "/admin-dashboard", "/peptide-info"]}
