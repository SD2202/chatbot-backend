from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db.models import engine, PropertyTax
from app.services.pdf_service import generate_vmc_receipt
from fastapi.responses import Response

router = APIRouter()

def get_session():
    with Session(engine) as session:
        yield session

@router.get("/admin/tax")
async def get_all_tax_records(session: Session = Depends(get_session)):
    """
    Fetch all property tax records from the SQL database.
    """
    statement = select(PropertyTax)
    records = session.exec(statement).all()
    return records

@router.get("/admin/tax/pdf/{record_id}")
async def download_tax_pdf(record_id: int, session: Session = Depends(get_session)):
    """
    Generate and download a VMC Property Tax Receipt PDF.
    """
    statement = select(PropertyTax).where(PropertyTax.id == record_id)
    record = session.exec(statement).first()
    
    if not record:
        return {"error": "Record not found"}
    
    pdf_buffer = generate_vmc_receipt(record.dict())
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=VMC_Receipt_{record.customer_id}.pdf"}
    )
