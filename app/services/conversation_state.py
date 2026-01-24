from enum import Enum
from typing import Dict, Optional
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class ConversationState(str, Enum):
    LANGUAGE_SELECTION = "language_selection"
    LOGIN = "login"
    TRACKING_LOGIN_ID = "tracking_login_id"
    WELCOME_SELECTION = "welcome_selection"
    LOGIN_NAME = "login_name"
    LOGIN_MOBILE = "login_mobile"
    LOGIN_AREA_WARD = "login_area_ward"
    MAIN_MENU = "main_menu"
    CATEGORY_SELECTED = "category_selected"
    SUB_ISSUE_SELECTED = "sub_issue_selected"
    WAITING_IMAGE = "waiting_image"
    WAITING_LOCATION = "waiting_location"
    WAITING_DESCRIPTION = "waiting_description"
    WAITING_SOLUTION_CONFIRMATION = "waiting_solution_confirmation"
    WAITING_RESOLUTION_CONFIRMATION = "waiting_resolution_confirmation"
    PROPERTY_TAX_INPUT = "property_tax_input"
    PROPERTY_TAX_RESULT = "property_tax_result"
    OTHER_ISSUES = "other_issues"
    TERMINATED = "terminated"

class ConversationManager:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
    
    def get_session(self, phone_number: str) -> Dict:
        """Get or create session for phone number"""
        if phone_number not in self.sessions:
            self.sessions[phone_number] = {
                "phone_number": phone_number,
                "state": ConversationState.LOGIN.value,
                "user_id": None,
                "login_id": None,
                "name": None,
                "mobile": None,
                "area": None,
                "ward_number": None,
                "current_category": None,
                "current_sub_issue": None,
                "complaint_id": None,
                "property_id": None,
                "image_url": None,
                "description": None,
                "failed_attempts": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        return self.sessions[phone_number]
    
    def update_state(self, phone_number: str, state: ConversationState):
        """Update conversation state"""
        session = self.get_session(phone_number)
        session["state"] = state.value
        session["updated_at"] = datetime.utcnow()
    
    def set_user_data(self, phone_number: str, **kwargs):
        """Set user data in session"""
        session = self.get_session(phone_number)
        for key, value in kwargs.items():
            session[key] = value
        session["updated_at"] = datetime.utcnow()
    
    def generate_login_id(self) -> str:
        """Generate unique login ID"""
        return f"LOGIN-{uuid.uuid4().hex[:8].upper()}"
    
    def reset_session(self, phone_number: str):
        """Reset session to initial state"""
        self.sessions[phone_number] = {
            "phone_number": phone_number,
            "state": ConversationState.LOGIN.value,
            "user_id": None,
            "login_id": None,
            "name": None,
            "mobile": None,
            "area": None,
            "ward_number": None,
            "current_category": None,
            "current_sub_issue": None,
            "complaint_id": None,
            "property_id": None,
            "image_url": None,
            "description": None,
            "failed_attempts": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

conversation_manager = ConversationManager()
