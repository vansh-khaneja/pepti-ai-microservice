from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.chat_session import ChatSession, ChatMessage
from app.utils.helpers import logger
from typing import List, Optional, Dict, Any
import uuid

class ChatSessionService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(self, user_id: Optional[str] = None, title: Optional[str] = None) -> ChatSession:
        """Create a new chat session"""
        try:
            session = ChatSession(
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                title=title or "New Chat Session"
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            
            logger.info(f"Created new chat session: {session.session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error creating chat session: {str(e)}")
            self.db.rollback()
            raise
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID"""
        try:
            return self.db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        except Exception as e:
            logger.error(f"Error getting chat session {session_id}: {str(e)}")
            return None
    
    def get_or_create_session(self, session_id: Optional[str] = None, user_id: Optional[str] = None) -> ChatSession:
        """Get existing session or create new one"""
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        
        # Create new session
        return self.create_session(user_id=user_id)
    
    def add_message(self, session_id: str, role: str, content: str = None, 
                   query: Optional[str] = None, response: Optional[str] = None,
                   score: Optional[float] = None,
                   source: Optional[str] = None, metadata: Optional[dict] = None) -> ChatMessage:
        """Add a message to a chat session"""
        try:
            # Normalize fields per role
            normalized_query = query if role == "user" else None
            normalized_response = response if role == "assistant" else None
            normalized_content = content or normalized_query or normalized_response or ""

            message = ChatMessage(
                msg_id=str(uuid.uuid4()),
                session_id=session_id,
                role=role,
                content=normalized_content,
                query=normalized_query,
                response=normalized_response,
                score=score,
                source=source,
                meta=metadata or {}
            )
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            
            logger.info(f"Added {role} message to session {session_id}")
            return message
            
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {str(e)}")
            self.db.rollback()
            raise
    
    def get_session_messages(self, session_id: str, limit: int = 50) -> List[ChatMessage]:
        """Get messages for a session, ordered by creation time"""
        try:
            return self.db.query(ChatMessage)\
                .filter(ChatMessage.session_id == session_id)\
                .order_by(desc(ChatMessage.created_at))\
                .limit(limit)\
                .all()
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {str(e)}")
            return []
    
    def get_session_history(self, session_id: str) -> Dict[str, Any]:
        """Get session with its message history"""
        try:
            session = self.get_session(session_id)
            if not session:
                return None
            
            messages = self.get_session_messages(session_id)
            
            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "title": session.title,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "message_count": len(messages),
                "messages": [
                    {
                        "msg_id": msg.msg_id,
                        "role": msg.role,
                        "query": msg.query,
                        "response": msg.response,
                        "content": msg.content,
                        "source": msg.source,
                        "score": msg.score,
                        "metadata": msg.meta or {},
                        "created_at": msg.created_at
                    }
                    for msg in messages
                ]
            }
        except Exception as e:
            logger.error(f"Error getting session history for {session_id}: {str(e)}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session and all its messages"""
        try:
            session = self.get_session(session_id)
            if not session:
                return False
            
            self.db.delete(session)
            self.db.commit()
            
            logger.info(f"Deleted chat session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            self.db.rollback()
            return False
    
    def list_user_sessions(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """List sessions for a user"""
        try:
            sessions = self.db.query(ChatSession)\
                .filter(ChatSession.user_id == user_id)\
                .order_by(desc(ChatSession.updated_at))\
                .limit(limit)\
                .all()
            
            return [
                {
                    "session_id": session.session_id,
                    "title": session.title,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "message_count": len(session.messages)
                }
                for session in sessions
            ]
        except Exception as e:
            logger.error(f"Error listing sessions for user {user_id}: {str(e)}")
            return []
