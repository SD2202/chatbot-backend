from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.db.database import create_db_and_tables, seed_data, SessionLocal
from app.db.models import PropertyTax
from app.services.whatsapp import whatsapp_service
from app.services.conversation_router import ConversationRouter
from app.services.pdf_service import generate_property_tax_pdf
import logging
import os

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
                    response_text = conversation_router.process_message(from_number, message_text)
                    
                    # Send response
                    await whatsapp_service.send_text_message(from_number, response_text)
                
                # Handle image messages
                elif message_type == "image":
                    image_id = message_data["image"]["id"]
                    # In production, download image from WhatsApp API
                    # For now, we'll use a placeholder URL
                    image_url = f"https://graph.facebook.com/v18.0/{image_id}"
                    logger.info(f"Processing image from {from_number}: {image_id}")
                    
                    # Process image through conversation router
                    response_text = conversation_router.process_message(from_number, "", image_url=image_url)
                    
                    # Send response
                    await whatsapp_service.send_text_message(from_number, response_text)
                
                else:
                    logger.info(f"Unsupported message type: {message_type}")
                    await whatsapp_service.send_text_message(
                        from_number, 
                        "Please send a text message or image."
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
                "/api/property-tax/pdf/{property_id}",
                "/docs",
                "/redoc"
            ]
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", reload=settings.DEBUG)
