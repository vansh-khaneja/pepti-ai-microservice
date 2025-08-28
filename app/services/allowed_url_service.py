from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from datetime import datetime
from app.models.allowed_url import AllowedUrl, AllowedUrlSchema
from app.core.exceptions import AllowedUrlNotFoundError
from app.utils.helpers import logger

class AllowedUrlService:
    def __init__(self, db: Session):
        self.db = db

    def create_allowed_url(self, url_data) -> AllowedUrlSchema:
        """Create a new allowed URL"""
        url_dict = url_data.dict()
        url_dict["url"] = str(url_dict["url"])  # Convert HttpUrl to string
        
        db_url = AllowedUrl(**url_dict)
        self.db.add(db_url)
        self.db.commit()
        self.db.refresh(db_url)
        
        return AllowedUrlSchema.model_validate(db_url)



    def get_all_allowed_urls(self, skip: int = 0, limit: int = 100) -> List[AllowedUrlSchema]:
        """Get all allowed URLs with pagination"""
        result = self.db.execute(
            select(AllowedUrl)
            .offset(skip)
            .limit(limit)
        )
        urls = result.scalars().all()
        return [AllowedUrlSchema.model_validate(url) for url in urls]



    def delete_allowed_url(self, url: str) -> bool:
        """Delete an allowed URL"""
        result = self.db.execute(
            delete(AllowedUrl).where(AllowedUrl.url == url)
        )
        
        if result.rowcount == 0:
            raise AllowedUrlNotFoundError(url)
        
        self.db.commit()
        return True






