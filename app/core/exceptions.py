from fastapi import HTTPException, status

class PeptiWikiException(HTTPException):
    """Base exception for Pepti Wiki AI application"""
    pass

class ProductNotFoundError(PeptiWikiException):
    """Raised when a product is not found"""
    def __init__(self, product_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )

class FAQNotFoundError(PeptiWikiException):
    """Raised when a FAQ is not found"""
    def __init__(self, faq_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FAQ with id {faq_id} not found"
        )

class AllowedUrlNotFoundError(PeptiWikiException):
    """Raised when an allowed URL is not found"""
    def __init__(self, url: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Allowed URL '{url}' not found"
        )

class ChatRestrictionNotFoundError(PeptiWikiException):
    """Raised when a chat restriction is not found"""
    def __init__(self, restriction_text: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat restriction '{restriction_text}' not found"
        )
