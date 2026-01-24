"""
Setup MariaDB database for VMC Chatbot
This script will create the database and tables if they don't exist
"""
from app.core.config import settings
from sqlalchemy import create_engine, text
import sys

print("=" * 50)
print("VMC Chatbot - MariaDB Database Setup")
print("=" * 50)
print(f"\nConfiguration:")
print(f"  Host: {settings.DB_HOST}")
print(f"  Port: {settings.DB_PORT}")
print(f"  User: {settings.DB_USER}")
print(f"  Database: {settings.DB_NAME}")
print()

try:
    # Connect without specifying database first
    engine = create_engine(
        f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}",
        pool_pre_ping=True
    )
    
    with engine.connect() as conn:
        # Check if database exists
        result = conn.execute(text("SHOW DATABASES LIKE :db_name"), {"db_name": settings.DB_NAME})
        db_exists = result.fetchone() is not None
        
        if not db_exists:
            print(f"Creating database '{settings.DB_NAME}'...")
            conn.execute(text(f"CREATE DATABASE {settings.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
            print(f"✓ Database '{settings.DB_NAME}' created successfully!")
        else:
            print(f"✓ Database '{settings.DB_NAME}' already exists")
        
        # Now connect to the specific database
        conn.execute(text(f"USE {settings.DB_NAME}"))
        
        # Create tables using SQLAlchemy
        print("\nCreating tables...")
        try:
            from app.db.models import Base
            # Connect to the specific database for table creation
            db_engine = create_engine(
                f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}",
                pool_pre_ping=True
            )
            Base.metadata.create_all(bind=db_engine)
            print("✓ Tables created successfully!")
        except Exception as table_error:
            print(f"✗ Error creating tables: {table_error}")
            import traceback
            traceback.print_exc()
            raise
        
        # Seed initial data
        print("\nSeeding initial data...")
        from app.db.database import seed_data
        seed_data()
        print("✓ Initial data seeded!")
        
    print("\n" + "=" * 50)
    print("✓ Database setup completed successfully!")
    print("=" * 50)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure MariaDB/MySQL is running")
    print("2. Verify user credentials are correct")
    print("3. Check user has CREATE DATABASE permission")
    sys.exit(1)
