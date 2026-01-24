from typing import Optional, Dict, Tuple
from app.services.conversation_state import ConversationState, conversation_manager
from app.services.complaint_templates import (
    get_category_name, get_sub_issues, get_solution, is_other_option
)
from app.services.translations import get_text
from app.db.database import SessionLocal
from app.db.models import User, Session as SessionModel, Complaint, PropertyTax, ComplaintStatus, TaxStatus
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class ConversationRouter:
    def __init__(self):
        pass
    
    def _get_db(self):
        """Get database session"""
        return SessionLocal()
    
    def process_message(self, phone_number: str, message_text: str, image_url: Optional[str] = None, location: Optional[Dict] = None) -> str:
        """Process incoming message and return response"""
        session = conversation_manager.get_session(phone_number)
        state = ConversationState(session["state"])
        lang = session.get("language", "en")
        
        # Handle GPS Location
        if location:
            return self._handle_location(phone_number, location, state, lang)

        # Handle image uploads
        if image_url:
            return self._handle_image_upload(phone_number, image_url, state, lang)
        
        # Route based on state
        if state == ConversationState.LOGIN:
            return self._handle_login_start(phone_number)
        elif state == ConversationState.LANGUAGE_SELECTION:
            return self._handle_language_selection(phone_number, message_text)
        elif state == ConversationState.LOGIN_NAME:
            return self._handle_login_name(phone_number, message_text, lang)
        elif state == ConversationState.LOGIN_MOBILE:
            return self._handle_login_mobile(phone_number, message_text, lang)
        elif state == ConversationState.LOGIN_AREA_WARD:
            return self._handle_login_area_ward(phone_number, message_text, lang)
        elif state == ConversationState.MAIN_MENU:
            return self._handle_main_menu(phone_number, message_text, lang)
        elif state == ConversationState.CATEGORY_SELECTED:
            return self._handle_category_selection(phone_number, message_text, lang)
        elif state == ConversationState.SUB_ISSUE_SELECTED:
            return self._handle_sub_issue_selection(phone_number, message_text, lang)
        elif state == ConversationState.WAITING_LOCATION:
             return get_text("ask_gps", lang)
        elif state == ConversationState.WAITING_DESCRIPTION:
            return self._handle_description(phone_number, message_text, lang)
        elif state == ConversationState.WAITING_SOLUTION_CONFIRMATION:
            return self._handle_solution_confirmation(phone_number, message_text, lang)
        elif state == ConversationState.WAITING_RESOLUTION_CONFIRMATION:
            return self._handle_resolution_confirmation(phone_number, message_text, lang)
        elif state == ConversationState.PROPERTY_TAX_INPUT:
            return self._handle_property_tax_input(phone_number, message_text, lang)
        elif state == ConversationState.OTHER_ISSUES:
            return self._handle_other_issues(phone_number, message_text, lang)
        else:
            return "Invalid state. Please start over by sending 'Hi'."
    
    def _handle_login_start(self, phone_number: str) -> str:
        """Start login flow with language selection"""
        conversation_manager.update_state(phone_number, ConversationState.LANGUAGE_SELECTION)
        return get_text("greeting", "en")

    def _handle_language_selection(self, phone_number: str, choice: str) -> str:
        """Handle language selection"""
        choice = choice.strip()
        lang_map = {"1": "en", "2": "hi", "3": "gu"}
        
        if choice in lang_map:
            selected_lang = lang_map[choice]
            conversation_manager.set_user_data(phone_number, language=selected_lang)
            conversation_manager.update_state(phone_number, ConversationState.LOGIN_NAME)
            return get_text("welcome", selected_lang)
        else:
            return "Please reply with 1, 2, or 3.\n\n1. English\n2. Hindi\n3. Gujarati"
    
    def _handle_login_name(self, phone_number: str, name: str, lang: str) -> str:
        """Handle name input"""
        conversation_manager.set_user_data(phone_number, name=name)
        conversation_manager.update_state(phone_number, ConversationState.LOGIN_MOBILE)
        return get_text("ask_mobile", lang, name=name)
    
    def _handle_login_mobile(self, phone_number: str, mobile: str, lang: str) -> str:
        """Handle mobile input"""
        conversation_manager.set_user_data(phone_number, mobile=mobile)
        conversation_manager.update_state(phone_number, ConversationState.LOGIN_AREA_WARD)
        return get_text("ask_area_ward", lang)
    
    def _handle_login_area_ward(self, phone_number: str, area_ward: str, lang: str) -> str:
        """Handle merged area and ward input and complete login"""
        # Simple heuristic split or just save the whole string
        # For better data, we might want to regex it, but for now we trust the user input
        # We will save the raw input to 'area' and leave 'ward' empty or try to parse
        
        area = area_ward
        ward = "N/A" # Placeholder or try to extract if "Ward" is in string
        
        if "ward" in area_ward.lower():
            parts = area_ward.lower().split("ward")
            if len(parts) > 1:
                ward = "Ward " + parts[1].strip()
                area = parts[0].strip().rstrip(",").strip()

        session = conversation_manager.get_session(phone_number)
        login_id = conversation_manager.generate_login_id()
        
        # Save user to database
        db = self._get_db()
        try:
            user = User(
                login_id=login_id,
                name=session["name"],
                mobile=session["mobile"],
                area=area,
                ward_number=ward
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            conversation_manager.set_user_data(
                phone_number,
                user_id=user.id,
                login_id=login_id,
                area=area,
                ward_number=ward
            )
            
            # Save session to database
            db_session = SessionModel(
                user_id=user.id,
                phone_number=phone_number,
                state=ConversationState.MAIN_MENU.value,
                login_id=login_id
            )
            db.add(db_session)
            db.commit()
            
            conversation_manager.update_state(phone_number, ConversationState.MAIN_MENU)
            return get_text("login_success", lang, login_id=login_id)
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            db.rollback()
            return get_text("error", lang)
        finally:
            db.close()
    
    def _handle_main_menu(self, phone_number: str, choice: str, lang: str) -> str:
        """Handle main menu selection"""
        choice = choice.strip()
        
        category_map = {
            "1": "sewage_potholes_roads",
            "2": "garbage_cleanliness",
            "3": "electricity_issues"
        }

        if choice in category_map:
            category = category_map[choice]
            conversation_manager.set_user_data(phone_number, current_category=category)
            conversation_manager.update_state(phone_number, ConversationState.CATEGORY_SELECTED)
            sub_issues = get_sub_issues(category)
            # Fetch category name (could be translated if we updated complaint_templates)
            # For now stick to strict template behavior but wrap in translation
            return self._format_sub_issues_menu(sub_issues, category, lang)
        elif choice == "4":
            conversation_manager.update_state(phone_number, ConversationState.PROPERTY_TAX_INPUT)
            return get_text("ask_property_id", lang)
        else:
            return get_text("invalid_choice", lang)
    
    def _format_sub_issues_menu(self, sub_issues: list, category_key: str, lang: str) -> str:
        """Format sub-issues menu"""
        # We need to map category keys to display names if possible
        category_name = get_category_name(category_key) # This returns English default likely
        
        options = ""
        for i, issue in enumerate(sub_issues, 1):
            options += f"{i}️⃣ {issue}\n"
            
        return get_text("ask_sub_issue", lang, category=category_name, options=options)
    
    def _handle_category_selection(self, phone_number: str, choice: str, lang: str) -> str:
        """Handle sub-issue selection"""
        try:
            choice_num = int(choice.strip())
            session = conversation_manager.get_session(phone_number)
            category = session["current_category"]
            sub_issues = get_sub_issues(category)
            
            if 1 <= choice_num <= len(sub_issues):
                selected_issue = sub_issues[choice_num - 1]
                conversation_manager.set_user_data(phone_number, current_sub_issue=selected_issue)
                conversation_manager.update_state(phone_number, ConversationState.SUB_ISSUE_SELECTED)
                
                if is_other_option(selected_issue):
                    conversation_manager.update_state(phone_number, ConversationState.WAITING_DESCRIPTION)
                    return get_text("ask_description", lang)
                else:
                    conversation_manager.update_state(phone_number, ConversationState.WAITING_IMAGE)
                    return get_text("ask_image", lang, issue=selected_issue)
            else:
                return get_text("invalid_choice", lang) # Generic invalid
        except ValueError:
            return get_text("invalid_choice", lang)
    
    def _handle_sub_issue_selection(self, phone_number: str, message: str, lang: str) -> str:
        """This should not be called as state transitions to WAITING_IMAGE"""
        return "Please upload an image"
    
    def _handle_image_upload(self, phone_number: str, image_url: str, state: ConversationState, lang: str) -> str:
        """Handle image upload"""
        conversation_manager.set_user_data(phone_number, image_url=image_url)
        
        if state == ConversationState.WAITING_IMAGE:
            # Change: Ask for GPS location now instead of showing solution immediately
            conversation_manager.update_state(phone_number, ConversationState.WAITING_LOCATION)
            return get_text("ask_gps", lang)
        
        return "Image received. Processing..."

    def _handle_location(self, phone_number: str, location: Dict, state: ConversationState, lang: str) -> str:
        """Handle GPS location from WhatsApp"""
        lat = location.get("latitude")
        long = location.get("longitude")
        
        conversation_manager.set_user_data(phone_number, location_lat=lat, location_long=long)
        
        if state == ConversationState.WAITING_LOCATION:
             session = conversation_manager.get_session(phone_number)
             sub_issue = session["current_sub_issue"]
             category = session["current_category"]
             solution = get_solution(sub_issue, category)
             
             conversation_manager.update_state(phone_number, ConversationState.WAITING_SOLUTION_CONFIRMATION)
             return get_text("solution_steps", lang, solution=solution)
        
        return "Location received."

    
    def _handle_description(self, phone_number: str, description: str, lang: str) -> str:
        """Handle 'Other' issue description"""
        session = conversation_manager.get_session(phone_number)
        complaint_id = f"CMP-{uuid.uuid4().hex[:8].upper()}"
        
        db = self._get_db()
        try:
            # Save complaint
            complaint = Complaint(
                complaint_id=complaint_id,
                user_id=session["user_id"],
                login_id=session["login_id"],
                category=session["current_category"],
                sub_issue="Other",
                description=description,
                status=ComplaintStatus.PENDING
            )
            db.add(complaint)
            db.commit()
            
            conversation_manager.set_user_data(phone_number, complaint_id=complaint_id, description=description)
            conversation_manager.update_state(phone_number, ConversationState.TERMINATED)
            
            return get_text("pending_msg", lang).split("\n\n")[0] # Just the first part for Other
        except Exception as e:
            logger.error(f"Error saving complaint: {e}")
            db.rollback()
            return get_text("error", lang)
        finally:
            db.close()
    
    def _handle_solution_confirmation(self, phone_number: str, response: str, lang: str) -> str:
        """Handle solution completion confirmation"""
        response_lower = response.lower().strip()
        
        # Simple multilingual yes/no check (could be improved)
        yes_variants = ["yes", "y", "ha", "haan", "ha"]
        no_variants = ["no", "n", "nahi", "na"]
        
        if any(v in response_lower for v in yes_variants):
            conversation_manager.update_state(phone_number, ConversationState.WAITING_RESOLUTION_CONFIRMATION)
            return get_text("resolution_confirm", lang)
        elif any(v in response_lower for v in no_variants):
            return self._save_complaint_as_pending(phone_number, lang)
        else:
            return get_text("yes_no_invalid", lang)
    
    def _handle_resolution_confirmation(self, phone_number: str, response: str, lang: str) -> str:
        """Handle resolution confirmation"""
        response_lower = response.lower().strip()
        yes_variants = ["yes", "y", "ha", "haan", "ha"]
        no_variants = ["no", "n", "nahi", "na"]
        
        if any(v in response_lower for v in yes_variants):
            return self._mark_complaint_resolved(phone_number, lang)
        elif any(v in response_lower for v in no_variants):
            return self._save_complaint_as_pending(phone_number, lang)
        else:
            return get_text("yes_no_invalid", lang)
    
    def _save_complaint_as_pending(self, phone_number: str, lang: str) -> str:
        """Save complaint as pending"""
        session = conversation_manager.get_session(phone_number)
        complaint_id = f"CMP-{uuid.uuid4().hex[:8].upper()}"
        
        db = self._get_db()
        try:
            complaint = Complaint(
                complaint_id=complaint_id,
                user_id=session["user_id"],
                login_id=session["login_id"],
                category=session["current_category"],
                sub_issue=session["current_sub_issue"],
                image_url=session.get("image_url"),
                status=ComplaintStatus.PENDING
            )
            # Add location if available (schema update might be needed but for now models.py wasn't requested to change)
            # Assuming models might not have lat/long yet, ignoring for now or just saving in logs
            
            db.add(complaint)
            db.commit()
            
            conversation_manager.set_user_data(phone_number, complaint_id=complaint_id)
            conversation_manager.update_state(phone_number, ConversationState.OTHER_ISSUES)
            
            return get_text("pending_msg", lang)
        except Exception as e:
            logger.error(f"Error saving complaint: {e}")
            db.rollback()
            return get_text("error", lang)
        finally:
            db.close()
    
    def _mark_complaint_resolved(self, phone_number: str, lang: str) -> str:
        """Mark complaint as resolved"""
        session = conversation_manager.get_session(phone_number)
        complaint_id = f"CMP-{uuid.uuid4().hex[:8].upper()}"
        
        db = self._get_db()
        try:
            complaint = Complaint(
                complaint_id=complaint_id,
                user_id=session["user_id"],
                login_id=session["login_id"],
                category=session["current_category"],
                sub_issue=session["current_sub_issue"],
                image_url=session.get("image_url"),
                status=ComplaintStatus.RESOLVED
            )
            db.add(complaint)
            db.commit()
            
            conversation_manager.set_user_data(phone_number, complaint_id=complaint_id)
            conversation_manager.update_state(phone_number, ConversationState.OTHER_ISSUES)
            
            return get_text("resolved_msg", lang)
        except Exception as e:
            logger.error(f"Error saving complaint: {e}")
            db.rollback()
            return get_text("error", lang)
        finally:
            db.close()
    
    def _handle_property_tax_input(self, phone_number: str, property_id: str, lang: str) -> str:
        """Handle property tax query"""
        # ... logic remains same but use get_text ...
        session = conversation_manager.get_session(phone_number)
        
        db = self._get_db()
        try:
            tax_record = db.query(PropertyTax).filter(
                PropertyTax.property_id == property_id.upper()
            ).first()
            
            if tax_record:
                conversation_manager.set_user_data(phone_number, property_id=property_id)
                conversation_manager.update_state(phone_number, ConversationState.PROPERTY_TAX_RESULT)
                
                status_emoji = {
                    "paid": "✅",
                    "due": "⚠️",
                    "pending": "⏳"
                }
                
                # We can't easily translate dynamic DB content, but we can structure the response better or use templates
                # For now keeping it simple English but wrapped
                response = f"Property Tax Details:\n\n"
                response += f"Property ID: {tax_record.property_id}\n"
                # ... rest ...
                response += f"Amount: ₹{tax_record.amount}\n"
                
                pdf_url = f"/api/property-tax/pdf/{property_id}"
                response += f"\n📄 PDF: {pdf_url}\n"
                
                conversation_manager.update_state(phone_number, ConversationState.OTHER_ISSUES)
                response += "\nDo you have any other issues? (Reply: Yes/No)" # Could be translated
                return response
            else:
                return get_text("property_not_found", lang, property_id=property_id)
        except Exception as e:
            logger.error(f"Error querying property tax: {e}")
            return get_text("error", lang)
        finally:
            db.close()
    
    def _handle_other_issues(self, phone_number: str, response: str, lang: str) -> str:
        """Handle other issues question"""
        response_lower = response.lower().strip()
        yes_variants = ["yes", "y", "ha", "haan", "ha"]
        no_variants = ["no", "n", "nahi", "na"]
        
        if any(v in response_lower for v in yes_variants):
            conversation_manager.update_state(phone_number, ConversationState.MAIN_MENU)
            # Send main menu again
            return self._handle_main_menu(phone_number, "INVALID_TRIGGER_SHOW_MENU", lang).replace(get_text("invalid_choice", lang), get_text("login_success", lang, login_id="...").split("\n\n")[2]) 
            # This is a bit hacky, better to extract menu text. 
            # Let's just hardcode the menu prompt for 'Yes' return
            return get_text("login_success", lang, login_id=session["login_id"]).split("\n\nOther")[0] # Actually just use the menu part
            # Simplified:
            return get_text("login_success", lang, login_id="EXISTING").split("Please select")[1] if "Please select" in get_text("login_success", lang, login_id="X") else "Please select options..."
        elif any(v in response_lower for v in no_variants):
            conversation_manager.update_state(phone_number, ConversationState.TERMINATED)
            return get_text("terminate", lang)
        else:
            return get_text("yes_no_invalid", lang)

