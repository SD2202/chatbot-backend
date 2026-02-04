from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db.models import Base, User, Session as SessionModel, Complaint, PropertyTax
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create MariaDB connection string
DATABASE_URL = f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_db_and_tables():
    """Create all tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def seed_data():
    """Seed initial data if needed"""
    db = SessionLocal()
    try:
        # Check if property tax data exists
        if db.query(PropertyTax).first() is None:
            # Seed sample property tax records
            sample_taxes = [
                PropertyTax(
                    property_id="PROP-001",
                    owner_name="John Doe",
                    address="123 Main Street, Ward 1",
                    amount=15000.0,
                    status="paid",
                    year=2025,
                    receipt_no="REC-2025-001",
                    bill_no="BILL-2025-001"
                ),
                PropertyTax(
                    property_id="PROP-002",
                    owner_name="Jane Smith",
                    address="456 Oak Avenue, Ward 2",
                    amount=20000.0,
                    status="due",
                    year=2025,
                    receipt_no=None,
                    bill_no="BILL-2025-002"
                ),
                PropertyTax(
                    property_id="PROP-003",
                    owner_name="Bob Johnson",
                    address="789 Pine Road, Ward 3",
                    amount=18000.0,
                    status="pending",
                    year=2025,
                    receipt_no=None,
                    bill_no="BILL-2025-003"
                ),
            ]
            db.add_all(sample_taxes)
            db.commit()
            logger.info("Sample property tax data seeded")
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

