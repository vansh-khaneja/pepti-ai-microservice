from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.peptide_info_service import PeptideInfoService
from app.utils.helpers import logger, log_api_call
from typing import Optional

router = APIRouter()

@router.post("/generate", tags=["peptide-info"])
async def generate_peptide_info(
    peptide_name: str = Query(..., description="Name of the peptide to research"),
    requirements: str = Query("", description="Specific requirements for the information"),
    session_id: Optional[str] = Query(None, description="Optional session ID to continue research"),
    user_id: Optional[str] = Query(None, description="Optional user ID"),
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive peptide information using Tavily-first approach with SerpAPI fallback
    
    This endpoint:
    1. First tries Tavily search for quick, accurate results
    2. Checks accuracy score (threshold 0.8)
    3. If accuracy is good, tunes with LLM and returns
    4. If accuracy is poor, falls back to SerpAPI approach
    5. Saves all data to database including source content and metadata
    """
    try:
        # Log the API call
        log_api_call("/peptide-info/generate", f"peptide={peptide_name}, requirements={requirements}")
        
        # Initialize services
        peptide_info_service = PeptideInfoService()
        
        # Get or create session
        session = peptide_info_service.get_or_create_session(
            peptide_name=peptide_name,
            requirements=requirements,
            user_id=user_id,
            session_id=session_id,
            db=db
        )
        
        # Store user message
        peptide_info_service.add_message(
            session_id=session.session_id,
            role="user",
            content=f"Generate info for {peptide_name}" + (f" with requirements: {requirements}" if requirements else ""),
            query=f"Generate info for {peptide_name}",
            db=db
        )
        
        # Generate peptide information
        result = peptide_info_service.generate_peptide_info(peptide_name, requirements, db)
        
        # Store assistant response
        peptide_info_service.add_message(
            session_id=session.session_id,
            role="assistant",
            content=result["generated_response"],
            query=f"Generate info for {peptide_name}",
            response=result["generated_response"],
            source=result["source"],
            accuracy_score=result["accuracy_score"],
            source_content=result["source_content"],
            source_urls=result["source_urls"],
            meta=result["metadata"],
            db=db
        )
        
        # Add session info to response
        result["session_id"] = session.session_id
        
        return {
            "success": True,
            "message": f"Peptide information generated successfully for {peptide_name}",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error generating peptide info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate peptide information: {str(e)}"
        )

@router.get("/sessions/{session_id}", tags=["peptide-info"])
async def get_session_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the history of a peptide info generation session
    
    Returns all messages and metadata for the session
    """
    try:
        # Log the API call
        log_api_call(f"/peptide-info/sessions/{session_id}", "GET")
        
        # Initialize service
        peptide_info_service = PeptideInfoService()
        
        # Get session
        session = peptide_info_service.get_session(session_id, db)
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        # Get messages
        messages = db.query(PeptideInfoMessage).filter(
            PeptideInfoMessage.session_id == session_id
        ).order_by(PeptideInfoMessage.created_at).all()
        
        # Format response
        session_data = {
            "session_id": session.session_id,
            "peptide_name": session.peptide_name,
            "requirements": session.requirements,
            "user_id": session.user_id,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "messages": [
                {
                    "msg_id": msg.msg_id,
                    "role": msg.role,
                    "content": msg.content,
                    "query": msg.query,
                    "response": msg.response,
                    "source": msg.source,
                    "accuracy_score": msg.accuracy_score,
                    "source_content": msg.source_content,
                    "source_urls": msg.source_urls,
                    "meta": msg.meta,
                    "created_at": msg.created_at
                }
                for msg in messages
            ]
        }
        
        return {
            "success": True,
            "message": "Session history retrieved successfully",
            "data": session_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session history: {str(e)}"
        )

@router.get("/sessions", tags=["peptide-info"])
async def list_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    db: Session = Depends(get_db)
):
    """
    List peptide info generation sessions
    
    Returns a paginated list of sessions
    """
    try:
        # Log the API call
        log_api_call("/peptide-info/sessions", f"user_id={user_id}, limit={limit}, offset={offset}")
        
        # Build query
        query = db.query(PeptideInfoSession)
        
        if user_id:
            query = query.filter(PeptideInfoSession.user_id == user_id)
        
        # Get total count
        total = query.count()
        
        # Get sessions
        sessions = query.order_by(PeptideInfoSession.updated_at.desc()).offset(offset).limit(limit).all()
        
        # Format response
        sessions_data = [
            {
                "session_id": session.session_id,
                "peptide_name": session.peptide_name,
                "requirements": session.requirements,
                "user_id": session.user_id,
                "title": session.title,
                "created_at": session.created_at,
                "updated_at": session.updated_at
            }
            for session in sessions
        ]
        
        return {
            "success": True,
            "message": "Sessions retrieved successfully",
            "data": {
                "sessions": sessions_data,
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
        
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {str(e)}"
        )
