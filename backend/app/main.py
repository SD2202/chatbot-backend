from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.db.database import create_db_and_tables, seed_data, SessionLocal
from app.db.models import PropertyTax, Complaint, User, ComplaintStatus
from app.services.whatsapp import whatsapp_service
from app.services.conversation_router import ConversationRouter
from app.services.pdf_service import generate_property_tax_pdf
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="VMC WhatsApp Chatbot API")

# Initialize database
create_db_and_tables()
seed_data()

# Create upload and PDF directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.PDF_DIR, exist_ok=True)

# Mount static directories
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/pdfs", StaticFiles(directory=settings.PDF_DIR), name="pdfs")

# Enable CORS for frontend
# Parse CORS origins from settings
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")] if settings.CORS_ORIGINS else ["*"]
# Add frontend URL if specified
if settings.FRONTEND_URL and settings.FRONTEND_URL not in cors_origins:
    cors_origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["*"],
    max_age=3600,
)

# Initialize conversation router
conversation_router = ConversationRouter()

@app.get("/")
async def root():
    return {"message": "VMC WhatsApp Chatbot API is running"}

async def send_response(to: str, response):
    """Send appropriate response type based on response structure"""
    if isinstance(response, dict):
        response_type = response.get("type", "text")
        footer = response.get("footer")
        
        if response_type == "buttons":
            await whatsapp_service.send_button_message(
                to,
                response["body"],
                response["buttons"],
                footer=footer
            )
        elif response_type == "list":
            await whatsapp_service.send_list_message(
                to,
                response["body"],
                response["list_button"],
                response["sections"],
                footer=footer
            )
        else:
            # Fallback to text
            await whatsapp_service.send_text_message(to, response.get("body", str(response)))
    else:
        # Plain text response
        await whatsapp_service.send_text_message(to, str(response))

@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    WhatsApp Webhook Verification (GET)
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.VERIFY_TOKEN:
        logger.info("Webhook verified successfully!")
        return int(hub_challenge)
    
    logger.warning("Webhook verification failed!")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/webhook")
async def handle_whatsapp_message(request: Request):
    """
    Handle incoming WhatsApp messages (POST)
    """
    payload = await request.json()
    logger.info(f"Received WHATSAPP payload: {payload}")
    
    try:
        # Extract message data
        if payload.get("entry") and payload["entry"][0].get("changes"):
            change = payload["entry"][0]["changes"][0]
            value = change.get("value", {})
            
            # Handle messages
            if value.get("messages"):
                message_data = value["messages"][0]
                from_number = message_data["from"]
                message_type = message_data.get("type")
                
                # Handle text messages
                if message_type == "text":
                    message_text = message_data["text"]["body"]
                    logger.info(f"Processing text message from {from_number}: {message_text}")
                    
                    # Process message through conversation router
                    response = conversation_router.process_message(from_number, message_text)
                    
                    # Send appropriate response type
                    await send_response(from_number, response)
                
                # Handle interactive button/list responses
                elif message_type == "interactive":
                    interactive_data = message_data["interactive"]
                    interactive_type = interactive_data["type"]
                    
                    if interactive_type == "button_reply":
                        button_id = interactive_data["button_reply"]["id"]
                        logger.info(f"Processing button reply from {from_number}: {button_id}")
                        response = conversation_router.process_message(from_number, button_id)
                    elif interactive_type == "list_reply":
                        list_id = interactive_data["list_reply"]["id"]
                        logger.info(f"Processing list reply from {from_number}: {list_id}")
                        response = conversation_router.process_message(from_number, list_id)
                    else:
                        logger.warning(f"Unknown interactive type: {interactive_type}")
                        response = "Please select a valid option."
                    
                    # Send appropriate response type
                    await send_response(from_number, response)
                
                # Handle image messages
                elif message_type == "image":
                    image_id = message_data["image"]["id"]
                    logger.info(f"Received image ID: {image_id}")
                    
                    # 1. Get media URL from Meta
                    media_url = await whatsapp_service.get_media_url(image_id)
                    if media_url:
                        # 2. Download and save locally
                        filename = f"{image_id}.jpg"
                        save_path = os.path.join(settings.UPLOAD_DIR, filename)
                        success = await whatsapp_service.download_media(media_url, save_path)
                        
                        if success:
                            # Use local URL for processing
                            local_url = f"/uploads/{filename}"
                            response = conversation_router.process_message(from_number, "", image_url=local_url)
                            await send_response(from_number, response)
                        else:
                            await whatsapp_service.send_text_message(from_number, "Error processing image. Please try again.")
                    else:
                        await whatsapp_service.send_text_message(from_number, "Could not retrieve image from WhatsApp.")

                # Handle location messages
                elif message_type == "location":
                    location_data = {
                        "latitude": message_data["location"]["latitude"],
                        "longitude": message_data["location"]["longitude"]
                    }
                    logger.info(f"Processing location from {from_number}: {location_data}")
                    
                    # Process location through conversation router
                    response = conversation_router.process_message(from_number, "", location=location_data)
                    
                    # Send response
                    await send_response(from_number, response)
                
                else:
                    logger.info(f"Unsupported message type: {message_type}")
                    await whatsapp_service.send_text_message(
                        from_number, 
                        "Please send a text message, image, or location."
                    )
            
            # Handle status updates (delivered, read, etc.)
            elif value.get("statuses"):
                status = value["statuses"][0]
                logger.info(f"Message status update: {status}")
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        # Return 200 to WhatsApp to avoid retries
        return {"status": "error", "detail": str(e)}

    return {"status": "success"}

@app.get("/api/property-tax/pdf/{property_id}")
async def get_property_tax_pdf(property_id: str):
    """Generate and return property tax PDF"""
    db = SessionLocal()
    try:
        tax_record = db.query(PropertyTax).filter(
            PropertyTax.property_id == property_id.upper()
        ).first()
        
        if not tax_record:
            raise HTTPException(status_code=404, detail="Property not found")
        
        pdf_path = generate_property_tax_pdf(tax_record)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"property_tax_{property_id}.pdf"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise HTTPException(status_code=500, detail="Error generating PDF")
    finally:
        db.close()

@app.get("/api/complaints")
async def get_complaints():
    """Get all complaints with user details joined"""
    db = SessionLocal()
    try:
        results = db.query(Complaint, User).join(User, Complaint.user_id == User.id).all()
        
        complaints_with_users = []
        for complaint, user in results:
            complaint_data = {
                "id": complaint.id,
                "complaint_id": complaint.complaint_id,
                "user_id": complaint.user_id,
                "login_id": complaint.login_id,
                "category": complaint.category,
                "sub_issue": complaint.sub_issue,
                "description": complaint.description,
                "image_url": complaint.image_url,
                "latitude": complaint.latitude,
                "longitude": complaint.longitude,
                "status": complaint.status,
                "created_at": complaint.created_at,
                "user_name": user.name,
                "user_mobile": user.mobile,
                "user_area": user.area,
                "user_ward": user.ward_number
            }
            complaints_with_users.append(complaint_data)
        return complaints_with_users
    finally:
        db.close()

@app.patch("/api/complaints/{complaint_id}/status")
async def update_complaint_status(complaint_id: str, status: str):
    """Update complaint status"""
    logger.info(f"Updating complaint {complaint_id} status to {status}")
    db = SessionLocal()
    try:
        complaint = db.query(Complaint).filter(Complaint.complaint_id == complaint_id.strip()).first()
        if not complaint:
            logger.error(f"Complaint {complaint_id} not found")
            raise HTTPException(status_code=404, detail="Complaint not found")
        
        # Match enum Case
        new_status = status.lower()
        if new_status == "completed":
            complaint.status = ComplaintStatus.RESOLVED
        else:
            complaint.status = ComplaintStatus.PENDING
            
        complaint.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(complaint)
        logger.info(f"Successfully updated complaint {complaint_id} to {complaint.status}")
        return {"message": "Status updated successfully", "status": complaint.status}
    except Exception as e:
        logger.error(f"Error updating status for {complaint_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/properties")
async def get_properties():
    """Get all property tax records"""
    db = SessionLocal()
    try:
        properties = db.query(PropertyTax).all()
        return properties
    finally:
        db.close()

# Custom 404 handler
@app.exception_handler(StarletteHTTPException)
async def not_found_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code != 404:
        raise exc
    
    return JSONResponse(
        status_code=404,
        content={
            "detail": f"Invalid endpoint: {request.url.path}",
            "error": "Not Found",
            "valid_endpoints": [
                "/",
                "/webhook (GET for verification, POST for messages)",
                "/api/complaints",
                "/api/properties",
                "/api/property-tax/pdf/{property_id}",
                "/docs",
                "/redoc"
            ]
        }
    )

if __name__ == "__main__":
    import uvicorn
    # uvicorn app.main:app --host 0.0.0.0 --port $PORT
    port = int(os.getenv("PORT", settings.PORT))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=settings.DEBUG)
