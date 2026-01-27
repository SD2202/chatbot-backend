import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "AquaChat Local Server is running"}

def test_webhook_verification_success():
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "123456789",
        "hub.verify_token": settings.VERIFY_TOKEN
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 200
    assert response.text == "123456789"

def test_webhook_verification_failure():
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "123456789",
        "hub.verify_token": "wrong_token"
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 403

def test_webhook_post_message_structure():
    # Mock payload from WhatsApp
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "PHONE_NUMBER",
                                "phone_number_id": "PHONE_NUMBER_ID"
                            },
                            "contacts": [{"profile": {"name": "NAME"}, "wa_id": "PHONE_NUMBER"}],
                            "messages": [
                                {
                                    "from": "1234567890",
                                    "id": "MESSAGE_ID",
                                    "timestamp": "TIMESTAMP",
                                    "text": {"body": "Hello bot!"},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_invalid_endpoint_with_hint():
    """Test that invalid endpoints return 404 with helpful hints"""
    # Test invalid endpoint (file path style - common mistake)
    response = client.get("/tests/test_webhook.py")
    assert response.status_code == 404
    
    # Verify the response includes helpful information
    response_data = response.json()
    assert "detail" in response_data
    assert "error" in response_data
    assert "requested_path" in response_data
    assert "valid_endpoints" in response_data
    
    # Check if hint about valid endpoints is included
    detail = response_data["detail"].lower()
    assert "invalid endpoint" in detail
    assert "webhook" in detail
    assert "api" in detail
    assert "file paths" in detail or "tests/test_webhook.py" in detail.lower()
    
    # Verify valid endpoints list is provided
    assert len(response_data["valid_endpoints"]) > 0
    assert "/webhook" in str(response_data["valid_endpoints"])
