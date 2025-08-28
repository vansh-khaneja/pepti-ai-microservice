from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.models.chat_restriction import ChatRestriction, ChatRestrictionSchema, ChatRestrictionCreate

class ChatRestrictionService:
    def __init__(self, db: Session):
        self.db = db

    def create_chat_restriction(self, restriction_data) -> ChatRestrictionSchema:
        """Create a new chat restriction"""
        restriction_dict = restriction_data.dict()
        
        db_restriction = ChatRestriction(**restriction_dict)
        self.db.add(db_restriction)
        self.db.commit()
        self.db.refresh(db_restriction)
        
        return ChatRestrictionSchema.model_validate(db_restriction)

    def get_all_chat_restrictions(self, skip: int = 0, limit: int = 100) -> List[ChatRestrictionSchema]:
        """Get all chat restrictions with pagination"""
        result = self.db.execute(
            select(ChatRestriction)
            .offset(skip)
            .limit(limit)
        )
        restrictions = result.scalars().all()
        return [ChatRestrictionSchema.model_validate(restriction) for restriction in restrictions]



    def delete_chat_restriction(self, restriction_text: str) -> bool:
        """Delete a chat restriction by its text"""
        result = self.db.execute(
            delete(ChatRestriction).where(ChatRestriction.restriction_text == restriction_text)
        )
        
        self.db.commit()
        return result.rowcount > 0

    def get_total_count(self) -> int:
        """Get total count of chat restrictions"""
        result = self.db.execute(select(ChatRestriction))
        return len(result.scalars().all())
