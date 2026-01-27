from app.db.database import SessionLocal
from app.db.models import Complaint, PropertyTax, User, Session
from sqlalchemy import func

def verify_data():
    db = SessionLocal()
    try:
        complaint_count = db.query(func.count(Complaint.id)).scalar()
        tax_count = db.query(func.count(PropertyTax.id)).scalar()
        user_count = db.query(func.count(User.id)).scalar()
        
        print(f"Complaints: {complaint_count}")
        print(f"Property Tax Records: {tax_count}")
        print(f"Users: {user_count}")
        
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_data()
