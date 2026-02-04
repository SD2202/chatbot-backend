"""
Setup MariaDB database for VMC Chatbot
Creates database and tables if they don't exist.
Works for local and cloud deployments.
"""

import sys
import logging
from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 50)
print("VMC Chatbot - MariaDB Database Setup")
print("=" * 50)

print("\nConfiguration:")
print(f"  Host: {settings.DB_HOST}")
print(f"  Port: {settings.DB_PORT}")
print(f"  User: {settings.DB_USER}")
print(f"  Database: {settings.DB_NAME}")
print()

try:
    # Base connection (no DB selected)
    base_url = (
        f"mysql+pymysql://{settings.DB_USER}:"
        f"{settings.DB_PASSWORD}@{settings.DB_HOST}:"
        f"{settings.DB_PORT}"
    )

    engine = create_engine(base_url, pool_pre_ping=True)

    with engine.connect() as conn:

        # Check if database exists
        result = conn.execute(
            text("SHOW DATABASES LIKE :db_name"),
            {"db_name": settings.DB_NAME},
        )

        db_exists = result.fetchone() is not None

        if not db_exists:
            print(f"Creating database '{settings.DB_NAME}'...")
            conn.execute(
                text(
                    f"CREATE DATABASE {settings.DB_NAME} "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
            conn.commit()
            print("✓ Database created successfully!")
        else:
            print("✓ Database already exists")

    # Connect directly to DB
    db_url = (
        f"mysql+pymysql://{settings.DB_USER}:"
        f"{settings.DB_PASSWORD}@{settings.DB_HOST}:"
        f"{settings.DB_PORT}/{settings.DB_NAME}"
    )

    db_engine = create_engine(db_url, pool_pre_ping=True)

    print("\nCreating tables...")
    from app.db.models import Base

    Base.metadata.create_all(bind=db_engine)
    print("✓ Tables ready")

    print("\nSeeding initial data...")
    from app.db.database import seed_data

    seed_data()
    print("✓ Initial data seeded")

    print("\n" + "=" * 50)
    print("✓ Database setup completed successfully!")
    print("=" * 50)

except Exception as e:
    logger.exception("Database setup failed")
    print("\nTroubleshooting:")
    print("1. Ensure database server is reachable")
    print("2. Verify credentials")
    print("3. Confirm DB user permissions")
    sys.exit(1)
