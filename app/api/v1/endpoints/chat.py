from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.services.peptide_service import PeptideService
from app.services.chat_session_service import ChatSessionService
from app.services.intent_router_service import IntentRouterService
from app.repositories import repository_manager
from app.utils.helpers import logger, log_api_call
from typing import Optional, Dict, Any
from datetime import datetime

router = APIRouter()

def _save_session_messages_background(
    session_id: Optional[str],
    query: str,
    result: Dict[str, Any],
    is_cached: bool = False
):
    """Background task to save session messages to database"""
    try:
        db = SessionLocal()
        try:
            session_service = ChatSessionService(db)
            
            # Get or create session (handles None session_id)
            session = session_service.get_or_create_session(session_id)
            logger.debug(f"Background: Session {session.session_id} ready for message storage")
            
            # Store user message
            session_service.add_message(
                session_id=session.session_id,
                role="user",
                query=query,
                content=query
            )
            
            # Store assistant response
            session_service.add_message(
                session_id=session.session_id,
                role="assistant",
                query=query,
                response=result.get("llm_response"),
                score=result.get("similarity_score"),
                source=result.get("source"),
                metadata={"cached": is_cached}
            )
            
            # Update result with actual session_id for reference
            result["session_id"] = session.session_id
            
            logger.info(f"Background: Saved messages for session {session.session_id} (cached={is_cached})")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Background task error saving session messages: {str(e)}", exc_info=True)


def _cache_response_background(query: str, result: Dict[str, Any], endpoint_type: str = "general"):
    """Background task to cache response in Redis"""
    try:
        cache_repo = repository_manager.cache
        cache_repo.set_cached_response(query, result, endpoint_type=endpoint_type)
        logger.info(f"Background: Cached response for query: {query[:50]}...")
    except Exception as e:
        logger.error(f"Background task error caching response: {str(e)}")


@router.post("/search", tags=["chat"])
async def search_and_answer(
    query: str = Query(..., description="Your question about peptides"),
    session_id: Optional[str] = Query(None, description="Optional session ID to continue conversation"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    General search endpoint that finds the best matching peptide and answers your question
    
    This endpoint:
    1. Checks Redis cache FIRST (before any session management)
    2. If cache miss, uses vector similarity to find the best matching peptide in DB
    3. If DB search has decent accuracy, uses it; otherwise falls back to Tavily search
    4. Returns response immediately while session management and caching happen in background
    """
    try:
        # Log the API call
        log_api_call("/chat/search", query)
        
        # Initialize cache repository
        cache_repo = repository_manager.cache
        
        # Check cache FIRST (before any session management)
        cached_response = cache_repo.get_cached_response(query, endpoint_type="general")
        if cached_response:
            logger.info(f"Cache HIT for query: {query[:50]}...")
            
            # Add timestamp to cached response
            result = cached_response.copy()
            result["timestamp"] = datetime.utcnow().isoformat()
            
            # Schedule background task for session management (get/create session and save messages)
            background_tasks.add_task(
                _save_session_messages_background,
                session_id,  # Pass None if not provided, will be handled in background
                query,
                result,
                is_cached=True
            )
            
            return {
                "success": True,
                "message": "Search completed successfully (from cache)",
                "data": result,
                "cached": True
            }
        
        # Cache miss: Direct DB search (no intent classification)
        logger.info(f"Cache MISS for query: {query[:50]}...")
        peptide_service = PeptideService()
        result = peptide_service.search_and_answer(query)
        
        # Add timestamp to response
        result["timestamp"] = datetime.utcnow().isoformat()
        
        # Schedule background tasks for session management and caching
        background_tasks.add_task(
            _save_session_messages_background,
            session_id,  # Pass None if not provided, will be handled in background
            query,
            result,
            is_cached=False
        )
        background_tasks.add_task(
            _cache_response_background,
            query,
            result,
            endpoint_type="general"
        )
        
        return {
            "success": True,
            "message": "Search completed successfully",
            "data": result,
            "cached": False
        }
        
    except Exception as e:
        logger.error(f"Error in search and answer: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search and answer: {str(e)}"
        )

@router.post("/router", tags=["chat"])
async def route_and_answer(
    query: str = Query(..., description="Your message"),
    session_id: Optional[str] = Query(None, description="Optional session ID to continue conversation"),
    db: Session = Depends(get_db)
):
    """
    Classify query intent and route:
    - general: answer directly via LLM (bypass peptide flow)
    - peptide: run peptide search-and-answer flow
    """
    try:
        log_api_call("/chat/router", query)

        session_service = ChatSessionService(db)
        intent_service = IntentRouterService()

        session = session_service.get_or_create_session(session_id)

        # Store user message
        session_service.add_message(
            session_id=session.session_id,
            role="user",
            query=query,
            content=query
        )

        classification = intent_service.classify_intent(query)
        intent = classification.get("intent", "general")
        peptide_name = classification.get("peptide_name")

        if intent == "peptide":
            # If peptide_name not extracted, fall back to general search flow
            peptide_service = PeptideService()
            if peptide_name:
                result = peptide_service.query_peptide(peptide_name, query)
            else:
                result = peptide_service.search_and_answer(query)

            session_service.add_message(
                session_id=session.session_id,
                role="assistant",
                query=query,
                response=result["llm_response"],
                score=result.get("similarity_score"),
                source=result.get("source"),
                metadata={}
            )
            result["intent"] = intent
            result["session_id"] = session.session_id
            return {"success": True, "message": "Peptide path", "data": result}

        # General path
        answer = intent_service.answer_general_query(query)
        session_service.add_message(
            session_id=session.session_id,
            role="assistant",
            query=query,
            response=answer,
            score=None,
            source="general",
            metadata={}
        )
        return {
            "success": True,
            "message": "General path",
            "data": {"llm_response": answer, "intent": "general", "session_id": session.session_id}
        }
    except Exception as e:
        logger.error(f"Error in route_and_answer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to route query: {str(e)}")

@router.post("/query/{peptide_name}", tags=["chat"])
async def query_specific_peptide(
    peptide_name: str,
    query: str = Query(..., description="Your question about this specific peptide"),
    session_id: Optional[str] = Query(None, description="Optional session ID to continue conversation"),
    db: Session = Depends(get_db)
):
    """
    Query a specific peptide by name
    
    This endpoint:
    1. Checks Redis cache first for existing answers
    2. Finds the peptide by name in Qdrant
    3. Uses its context to answer your question
    4. Caches the result for future queries
    5. Returns the answer based on that peptide's information
    """
    try:
        # Log the API call
        log_api_call(f"/chat/query/{peptide_name}", query)
        
        # Initialize cache repository
        cache_repo = repository_manager.cache
        
        # Initialize services first (needed for both cache hit and miss)
        session_service = ChatSessionService(db)
        intent_service = IntentRouterService()
        
        # Get or create session
        session = session_service.get_or_create_session(session_id)
        
        # Always store user message (populate query field)
        session_service.add_message(
            session_id=session.session_id,
            role="user",
            query=query,
            content=query
        )
        
        # Check cache first
        cached_response = cache_repo.get_cached_response(query, peptide_name, endpoint_type="specific")
        if cached_response:
            logger.info(f"Returning cached response for peptide query: {peptide_name} - {query[:50]}...")
            
            # Store assistant response from cache
            session_service.add_message(
                session_id=session.session_id,
                role="assistant",
                query=query,
                response=cached_response["llm_response"],
                score=cached_response.get("similarity_score"),
                source=cached_response.get("source"),
                metadata={"cached": True, "peptide_name": peptide_name}
            )
            
            # Add session info to cached response
            result = cached_response.copy()
            result["session_id"] = session.session_id
            
            return {
                "success": True,
                "message": f"Query for {peptide_name} completed successfully (from cache)",
                "data": result,
                "cached": True
            }
        
        # Intent classification and routing for specific peptide queries
        classification = intent_service.classify_intent(query)
        intent = classification.get("intent", "peptide")
        if intent == "general":
            # General path: answer directly, bypass peptide context
            answer = intent_service.answer_general_query(query)
            result = {
                "llm_response": answer,
                "peptide_name": peptide_name,
                "similarity_score": None,
                "peptide_context": None,
                "source": "general"
            }
        else:
            # Peptide path
            peptide_service = PeptideService()
            result = peptide_service.query_peptide(peptide_name, query)
        
        # Store assistant response
        session_service.add_message(
            session_id=session.session_id,
            role="assistant",
            query=query,
            response=result["llm_response"],
            score=result.get("similarity_score"),
            source=result.get("source"),
            metadata={}
        )
        
        # Add session info and timestamp to response
        result["session_id"] = session.session_id
        result["timestamp"] = datetime.utcnow().isoformat()
        
        # Cache the response
        cache_repo.set_cached_response(query, result, peptide_name, endpoint_type="specific")
        
        return {
            "success": True,
            "message": f"Query for {peptide_name} completed successfully",
            "data": result,
            "cached": False
        }
        
    except Exception as e:
        logger.error(f"Error querying peptide {peptide_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query peptide: {str(e)}"
        )

@router.get("/sessions/{session_id}", tags=["chat"])
async def get_session_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get chat session history with all messages
    """
    try:
        session_service = ChatSessionService(db)
        history = session_service.get_session_history(session_id)
        
        if not history:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        return {
            "success": True,
            "message": "Session history retrieved successfully",
            "data": history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session history: {str(e)}"
        )

@router.post("/sessions", tags=["chat"])
async def create_new_session(
    user_id: Optional[str] = Query(None, description="Optional user ID"),
    title: Optional[str] = Query(None, description="Optional session title"),
    db: Session = Depends(get_db)
):
    """
    Create a new chat session
    """
    try:
        session_service = ChatSessionService(db)
        session = session_service.create_session(user_id=user_id, title=title)
        
        return {
            "success": True,
            "message": "New session created successfully",
            "data": {
                "session_id": session.session_id,
                "title": session.title,
                "created_at": session.created_at
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}"
        )

@router.delete("/sessions/{session_id}", tags=["chat"])
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a chat session and all its messages
    """
    try:
        session_service = ChatSessionService(db)
        success = session_service.delete_session(session_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        return {
            "success": True,
            "message": f"Session {session_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {str(e)}"
        )

@router.get("/cache/stats", tags=["chat"])
async def get_cache_stats():
    """
    Get Redis cache statistics and information
    """
    try:
        cache_repo = repository_manager.cache
        stats = cache_repo.get_cache_stats()
        
        return {
            "success": True,
            "message": "Cache statistics retrieved successfully",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache stats: {str(e)}"
        )

@router.delete("/cache/clear", tags=["chat"])
async def clear_cache():
    """
    Clear all chat cache entries
    """
    try:
        cache_repo = repository_manager.cache
        deleted_count = cache_repo.clear_cache()
        
        return {
            "success": True,
            "message": f"Cache cleared successfully. {deleted_count} entries deleted.",
            "data": {"deleted_count": deleted_count}
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )
