from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db.models import engine, Complaint
from typing import List

router = APIRouter()

def get_session():
    with Session(engine) as session:
        yield session

@router.get("/admin/complaints")
async def get_all_complaints(session: Session = Depends(get_session)):
    """
    Fetch all registered complaints from the SQL database.
    """
    statement = select(Complaint)
    records = session.exec(statement).all()
    return records

@router.get("/admin/complaints/recent")
async def get_recent_complaints(session: Session = Depends(get_session)):
    """
    Fetch the 5 most recent complaints.
    """
    statement = select(Complaint).order_by(Complaint.created_at.desc()).limit(5)
    records = session.exec(statement).all()
    return records
