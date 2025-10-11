from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.peptide_service import PeptideService
from app.services.chat_session_service import ChatSessionService
from app.services.intent_router_service import IntentRouterService
from app.services.redis_cache_service import RedisCacheService
from app.utils.helpers import logger, log_api_call
from typing import Optional
from datetime import datetime

router = APIRouter()

@router.post("/search", tags=["chat"])
async def search_and_answer(
    query: str = Query(..., description="Your question about peptides"),
    session_id: Optional[str] = Query(None, description="Optional session ID to continue conversation"),
    db: Session = Depends(get_db)
):
    """
    General search endpoint that finds the best matching peptide and answers your question
    
    This endpoint:
    1. Checks Redis cache first for existing answers
    2. Uses vector similarity to find the best matching peptide
    3. Answers your question using that peptide's context
    4. Caches the result for future queries
    5. Returns the answer, peptide name, and similarity score
    """
    try:
        # Log the API call
        log_api_call("/chat/search", query)
        
        # Initialize Redis cache service
        cache_service = RedisCacheService()
        
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
        cached_response = cache_service.get_cached_response(query, endpoint_type="general")
        if cached_response:
            logger.info(f"Returning cached response for query: {query[:50]}...")
            
            # Store assistant response from cache
            session_service.add_message(
                session_id=session.session_id,
                role="assistant",
                query=query,
                response=cached_response["response"]["llm_response"],
                score=cached_response["response"].get("similarity_score"),
                source=cached_response["response"].get("source"),
                metadata={"cached": True}
            )
            
            # Add session info to cached response
            result = cached_response["response"].copy()
            result["session_id"] = session.session_id
            
            return {
                "success": True,
                "message": "Search completed successfully (from cache)",
                "data": result,
                "cached": True
            }
        
        # Intent classification and routing
        classification = intent_service.classify_intent(query)
        intent = classification.get("intent", "general")
        result = None
        if intent == "peptide":
            # Create peptide service lazily only when needed
            peptide_service = PeptideService()
            result = peptide_service.search_and_answer(query)
        else:
            # General path: answer directly
            answer = intent_service.answer_general_query(query)
            result = {
                "llm_response": answer,
                "peptide_name": None,
                "similarity_score": None,
                "peptide_context": None,
                "source": "general"
            }
        
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
        cache_service.set_cached_response(query, result, endpoint_type="general")
        
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
        
        # Initialize Redis cache service
        cache_service = RedisCacheService()
        
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
        cached_response = cache_service.get_cached_response(query, peptide_name, endpoint_type="specific")
        if cached_response:
            logger.info(f"Returning cached response for peptide query: {peptide_name} - {query[:50]}...")
            
            # Store assistant response from cache
            session_service.add_message(
                session_id=session.session_id,
                role="assistant",
                query=query,
                response=cached_response["response"]["llm_response"],
                score=cached_response["response"].get("similarity_score"),
                source=cached_response["response"].get("source"),
                metadata={"cached": True, "peptide_name": peptide_name}
            )
            
            # Add session info to cached response
            result = cached_response["response"].copy()
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
        cache_service.set_cached_response(query, result, peptide_name, endpoint_type="specific")
        
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
        cache_service = RedisCacheService()
        stats = cache_service.get_cache_stats()
        
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
        cache_service = RedisCacheService()
        deleted_count = cache_service.invalidate_cache()
        
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
