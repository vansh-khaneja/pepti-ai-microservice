from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.peptide_info_service import PeptideInfoService
from app.core.database import get_db
from app.models.search import SearchRequest, SearchAPIResponse
from app.utils.helpers import log_api_call, logger
from typing import Optional

router = APIRouter()

# OLD ENDPOINT - COMMENTED OUT
# @router.post("/peptide", response_model=SearchAPIResponse, tags=["search"])
# async def search_peptide_old(
#     search_request: SearchRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     OLD: Search for peptide information using SerpAPI, web scraping, and LLM processing
#     """
#     try:
#         log_api_call("/search/peptide", "POST")
#         search_service = SearchService()
#         search_response = search_service.search_peptide(search_request, db)
#         return SearchAPIResponse(
#             success=True,
#             message="Peptide search completed successfully",
#             data=search_response
#         )
#     except Exception as e:
#         log_api_call("/search/peptide", "POST", error=str(e))
#         raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/peptide", response_model=SearchAPIResponse, tags=["search"])
async def search_peptide(
    search_request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    NEW: Search for peptide information using Tavily-first approach with SerpAPI fallback
    
    This endpoint:
    1. First tries Tavily search for quick, accurate results
    2. Checks accuracy score (threshold 0.8)
    3. If accuracy is good, tunes with LLM and returns
    4. If accuracy is poor, falls back to SerpAPI approach
    5. Saves all data to database including source content and metadata
    """
    try:
        # Log the API call
        log_api_call("/search/peptide", "POST")
        
        # Print received parameters
        logger.info(f"🔍 Received peptide search request:")
        logger.info(f"   Peptide Name: '{search_request.peptide_name}'")
        logger.info(f"   Requirements: '{search_request.requirements}'")
        
        # Initialize peptide info service
        peptide_info_service = PeptideInfoService()
        
        # Create session for this search
        session = peptide_info_service.create_session(
            peptide_name=search_request.peptide_name,
            requirements=search_request.requirements,
            db=db
        )
        
        # Store user message
        peptide_info_service.add_message(
            session_id=session.session_id,
            role="user",
            content=f"Search for {search_request.peptide_name}" + (f" with requirements: {search_request.requirements}" if search_request.requirements else ""),
            query=f"Search for {search_request.peptide_name}",
            db=db
        )
        
        # Generate peptide information using Tavily-first approach
        result = peptide_info_service.generate_peptide_info(
            search_request.peptide_name, 
            search_request.requirements, 
            db
        )
        
        # Store assistant response
        peptide_info_service.add_message(
            session_id=session.session_id,
            role="assistant",
            content=result["generated_response"],
            query=f"Search for {search_request.peptide_name}",
            response=result["generated_response"],
            source=result["source"],
            accuracy_score=result["accuracy_score"],
            source_content=result["source_content"],
            source_urls=result["source_urls"],
            meta=result["metadata"],
            db=db
        )
        
        # Convert to SearchAPIResponse format for frontend compatibility
        from app.models.search import SearchResponse, SourceSite
        
        # Create source sites from the result (matching old schema exactly)
        source_sites = []
        # SerpAPI path returns rich objects under source_urls (from search_service)
        if str(result.get("source", "")).startswith("serpapi"):
            serp_sites = result.get("source_urls") or result.get("source_sites") or []
            for site in serp_sites:
                try:
                    source_sites.append(SourceSite(
                        url=site.get("url"),
                        title=site.get("title") or "Source",
                        similarity_score=round(float(site.get("similarity_score", 0.0)), 6),
                        content_length=int(site.get("content_length") or 0)
                    ))
                except Exception:
                    continue
        else:
            # Tavily path: use per-URL scores from metadata if available
            urls = result.get("source_urls") or []
            tavily_scores = []
            meta = result.get("metadata") or {}
            try:
                tavily_scores = meta.get("tavily_scores") or []
            except Exception:
                tavily_scores = []

            for i, url in enumerate(urls):
                score = None
                if i < len(tavily_scores):
                    try:
                        score = float(tavily_scores[i])
                    except Exception:
                        score = None
                if score is None:
                    score = float(result.get("accuracy_score") or 0.0)

                source_sites.append(SourceSite(
                    url=url,
                    title=f"Source {i+1}",
                    similarity_score=round(score, 6),
                    content_length=len(result.get("source_content") or []) if isinstance(result.get("source_content"), list) else (len(result.get("source_content") or ""))
                ))
        
        search_response = SearchResponse(
            peptide_name=search_request.peptide_name,
            requirements=search_request.requirements,
            generated_response=result["generated_response"],
            source_sites=source_sites,
            search_timestamp=result["metadata"].get("search_timestamp")
        )
        
        return SearchAPIResponse(
            success=True,
            message=f"Peptide search completed successfully for {search_request.peptide_name}",
            data=search_response
        )
        
    except Exception as e:
        logger.error(f"Error in peptide search: {str(e)}")
        log_api_call("/search/peptide", "POST", error=str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Search failed: {str(e)}"
        )
