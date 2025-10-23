from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Create synchronous engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create base class for models
Base = declarative_base()

def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables using Alembic migrations"""
    try:
        import subprocess
        import sys
        
        # Run Alembic migrations to ensure database is up to date
        result = subprocess.run([
            sys.executable, "-m", "alembic", "upgrade", "head"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("✅ Database migrations applied successfully")
            print(result.stdout)
        else:
            print(f"❌ Migration failed: {result.stderr}")
            # Fallback to manual table creation if migrations fail
            print("🔄 Falling back to manual table creation...")
            _fallback_table_creation()
            
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        print("🔄 Falling back to manual table creation...")
        _fallback_table_creation()

def _fallback_table_creation():
    """Fallback method for manual table creation"""
    try:
        # Check if tables exist and create them if they don't
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if not existing_tables:
            # Create all tables if none exist
            Base.metadata.create_all(bind=engine)
            print("✅ Database tables created successfully")
        else:
            # Check if our specific tables exist
            required_tables = [
                'allowed_urls', 'chat_restrictions', 'endpoint_usage', 'external_api_usage', 
                'chat_sessions', 'chat_messages', 'peptide_info_sessions', 'peptide_info_messages'
            ]
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if missing_tables:
                # Only create missing tables
                Base.metadata.create_all(bind=engine)
                print(f"✅ Created missing tables: {missing_tables}")
            else:
                # Check if existing tables need schema updates
                update_existing_schemas(inspector)
                print("✅ All required tables already exist")
                
    except Exception as e:
        print(f"❌ Error in fallback table creation: {e}")
        raise

def update_existing_schemas(inspector):
    """Update existing table schemas if needed"""
    try:
        # Check if chat_restrictions table has old schema
        if 'chat_restrictions' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('chat_restrictions')]
            
            # If table has old schema (id, category, description, updated_at columns)
            if 'id' in columns and 'category' in columns and 'description' in columns and 'updated_at' in columns:
                print("Updating chat_restrictions table schema...")
                
                # Drop the old table and recreate with new schema
                with engine.begin() as conn:
                    conn.execute(text("DROP TABLE IF EXISTS chat_restrictions"))
                
                # Create new table with correct schema
                from app.models.chat_restriction import ChatRestriction
                ChatRestriction.__table__.create(bind=engine)
                print("chat_restrictions table schema updated successfully")
                
    except Exception as e:
        print(f"Warning: Could not update existing schemas: {e}")
        print("You may need to manually drop and recreate tables")

def close_db():
    """Close database connection"""
    engine.dispose()
