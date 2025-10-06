#!/usr/bin/env python3
"""
Script to manually create database tables for peptide info generation
"""

from app.core.database import init_db, engine
from app.models import PeptideInfoSession, PeptideInfoMessage
from sqlalchemy import text

def create_tables():
    """Create the new peptide info tables"""
    try:
        print("Creating peptide info tables...")
        
        # Import all models to register them with SQLAlchemy
        from app.models import (
            ChatSession, ChatMessage, 
            PeptideInfoSession, PeptideInfoMessage,
            AllowedUrl, ChatRestriction, EndpointUsage
        )
        
        # Create all tables
        from app.core.database import Base
        Base.metadata.create_all(bind=engine)
        
        print("✅ All tables created successfully!")
        
        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"📋 Existing tables: {tables}")
        
        if 'peptide_info_sessions' in tables and 'peptide_info_messages' in tables:
            print("✅ Peptide info tables created successfully!")
        else:
            print("❌ Peptide info tables not found!")
            
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        raise

if __name__ == "__main__":
    create_tables()
