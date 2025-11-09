from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.tavily_toggle import TavilyToggle, TavilyToggleSchema, TavilyToggleUpdate
from app.utils.helpers import logger

class TavilyToggleService:
    def __init__(self, db: Session):
        self.db = db

    def get_tavily_toggle(self) -> TavilyToggleSchema:
        """Get the current Tavily search toggle setting"""
        result = self.db.execute(
            select(TavilyToggle).where(TavilyToggle.id == "main")
        )
        toggle = result.scalar_one_or_none()
        
        # If no toggle exists, create one with default value (enabled=True)
        if toggle is None:
            logger.info("Tavily toggle not found, creating default (enabled=True)")
            toggle = TavilyToggle(id="main", enabled=True)
            self.db.add(toggle)
            self.db.commit()
            self.db.refresh(toggle)
        
        return TavilyToggleSchema.model_validate(toggle)

    def update_tavily_toggle(self, toggle_data: TavilyToggleUpdate) -> TavilyToggleSchema:
        """Update the Tavily search toggle setting"""
        result = self.db.execute(
            select(TavilyToggle).where(TavilyToggle.id == "main")
        )
        toggle = result.scalar_one_or_none()
        
        if toggle is None:
            # Create new toggle
            toggle = TavilyToggle(id="main", enabled=toggle_data.enabled)
            self.db.add(toggle)
        else:
            # Update existing toggle
            toggle.enabled = toggle_data.enabled
        
        self.db.commit()
        self.db.refresh(toggle)
        
        logger.info(f"Tavily search toggle updated: enabled={toggle.enabled}")
        return TavilyToggleSchema.model_validate(toggle)

    def is_tavily_enabled(self) -> bool:
        """Check if Tavily search is enabled (quick check without full schema)"""
        result = self.db.execute(
            select(TavilyToggle.enabled).where(TavilyToggle.id == "main")
        )
        enabled = result.scalar_one_or_none()
        
        # Default to True if no toggle exists
        return enabled if enabled is not None else True

