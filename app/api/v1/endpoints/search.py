from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.search_service import SearchService
from app.core.database import get_db
from app.models.search import SearchRequest, SearchAPIResponse
from app.utils.helpers import log_api_call

router = APIRouter()

@router.post("/peptide", response_model=SearchAPIResponse, tags=["search"])
async def search_peptide(
    search_request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search for peptide information using SerpAPI, web scraping, and LLM processing
    
    This endpoint:
    1. Searches for peptide information using SerpAPI (top 50 results)
    2. Filters results to only include URLs from the allowed URLs database
    3. Scrapes content from allowed websites (max 5)
    4. Chunks content into manageable pieces
    5. Performs similarity search to find most relevant chunks
    6. Generates a focused response using OpenAI LLM
    """
    try:
        # Log the API call
        log_api_call("/search/peptide", "POST")
        
        # Initialize search service
        search_service = SearchService()
        
        # Perform the search
        search_response = search_service.search_peptide(search_request, db)
        
        # Return the response
        return SearchAPIResponse(
            success=True,
            message="Peptide search completed successfully",
            data=search_response
        )
        
    except Exception as e:
        # Log the error
        log_api_call("/search/peptide", "POST", error=str(e))
        
        # Return error response
        raise HTTPException(
            status_code=500, 
            detail=f"Search failed: {str(e)}"
        )
