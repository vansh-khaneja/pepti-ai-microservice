from fastapi import APIRouter, Depends
from app.core.auth import verify_token
from .endpoints import allowed_urls, chat_restrictions, search, peptides, chat, analytics, admin_dashboard, peptide_info, tavily_toggle

api_router = APIRouter()

# Include allowed URLs router with authentication
api_router.include_router(
    allowed_urls.router, 
    prefix="/allowed-urls", 
    tags=["allowed-urls"],
    dependencies=[Depends(verify_token)]
)

# Include chat restrictions router with authentication
api_router.include_router(
    chat_restrictions.router, 
    prefix="/chat-restrictions", 
    tags=["chat-restrictions"],
    dependencies=[Depends(verify_token)]
)

# Include Tavily toggle router with authentication
api_router.include_router(
    tavily_toggle.router, 
    prefix="/tavily-toggle", 
    tags=["tavily-toggle"],
    dependencies=[Depends(verify_token)]
)

# Include search router with authentication
api_router.include_router(
    search.router, 
    prefix="/search", 
    tags=["search"],
    dependencies=[Depends(verify_token)]
)

# Include peptides router with authentication
api_router.include_router(
    peptides.router, 
    prefix="/peptides", 
    tags=["peptides"],
    dependencies=[Depends(verify_token)]
)

# Include chat router with authentication
api_router.include_router(
    chat.router, 
    prefix="/chat", 
    tags=["chat"],
    dependencies=[Depends(verify_token)]
)

# Include analytics router with authentication
api_router.include_router(
    analytics.router, 
    prefix="/analytics", 
    tags=["analytics"],
    dependencies=[Depends(verify_token)]
)

# Include admin dashboard router with authentication
api_router.include_router(
    admin_dashboard.router, 
    prefix="", 
    tags=["admin-dashboard"],
    dependencies=[Depends(verify_token)]
)

# Include peptide info router with authentication
api_router.include_router(
    peptide_info.router, 
    prefix="/peptide-info", 
    tags=["peptide-info"],
    dependencies=[Depends(verify_token)]
)

@api_router.get("/", dependencies=[Depends(verify_token)])
async def api_root():
    """API root endpoint"""
    return {"message": "API v1 is active", "endpoints": ["/allowed-urls", "/chat-restrictions", "/tavily-toggle", "/search", "/peptides", "/chat", "/analytics", "/admin-dashboard", "/peptide-info"]}
