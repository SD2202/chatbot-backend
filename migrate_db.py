from sqlalchemy import create_engine, text
from app.core.config import settings

def migrate():
    DATABASE_URL = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("Migrating database...")
        try:
            # Add latitude column
            conn.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS latitude FLOAT AFTER image_url"))
            # Add longitude column
            conn.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS longitude FLOAT AFTER latitude"))
            conn.commit()
            print("Migration successful: Added latitude and longitude columns.")
        except Exception as e:
            print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
