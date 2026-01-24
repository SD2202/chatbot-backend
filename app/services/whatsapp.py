import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/v18.0/{settings.PHONE_NUMBER_ID}/messages"
        self.headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }

    async def send_text_message(self, to: str, text: str):
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                logger.info(f"Message sent to {to}: {text[:20]}...")
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to send message: {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                return None

    async def get_media_url(self, media_id: str) -> str:
        """Get the actual URL for a media ID from WhatsApp API"""
        url = f"https://graph.facebook.com/v18.0/{media_id}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                return data.get("url")
            except Exception as e:
                logger.error(f"Error getting media URL: {e}")
                return None

    async def download_media(self, media_url: str, save_path: str) -> bool:
        """Download media from WhatsApp and save to disk"""
        async with httpx.AsyncClient() as client:
            try:
                # Meta media URLs require the same auth header
                response = await client.get(media_url, headers=self.headers)
                response.raise_for_status()
                with open(save_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Media downloaded and saved to: {save_path}")
                return True
            except Exception as e:
                logger.error(f"Error downloading media: {e}")
                return False

whatsapp_service = WhatsAppService()
