from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.peptide_service import PeptideService
from app.utils.helpers import logger, log_api_call

router = APIRouter()

@router.post("/search", tags=["chat"])
async def search_and_answer(
    query: str = Query(..., description="Your question about peptides"),
    db: Session = Depends(get_db)
):
    """
    General search endpoint that finds the best matching peptide and answers your question
    
    This endpoint:
    1. Uses vector similarity to find the best matching peptide
    2. Answers your question using that peptide's context
    3. Returns the answer, peptide name, and similarity score
    """
    try:
        # Log the API call
        log_api_call("/chat/search", query)
        
        # Initialize peptide service
        peptide_service = PeptideService()
        
        # Search and answer
        result = peptide_service.search_and_answer(query)
        
        return {
            "success": True,
            "message": "Search completed successfully",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error in search and answer: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search and answer: {str(e)}"
        )

@router.post("/query/{peptide_name}", tags=["chat"])
async def query_specific_peptide(
    peptide_name: str,
    query: str = Query(..., description="Your question about this specific peptide"),
    db: Session = Depends(get_db)
):
    """
    Query a specific peptide by name
    
    This endpoint:
    1. Finds the peptide by name in Qdrant
    2. Uses its context to answer your question
    3. Returns the answer based on that peptide's information
    """
    try:
        # Log the API call
        log_api_call(f"/chat/query/{peptide_name}", query)
        
        # Initialize peptide service
        peptide_service = PeptideService()
        
        # Query the specific peptide
        result = peptide_service.query_peptide(peptide_name, query)
        
        return {
            "success": True,
            "message": f"Query for {peptide_name} completed successfully",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error querying peptide {peptide_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query peptide: {str(e)}"
        )
