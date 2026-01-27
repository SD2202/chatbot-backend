from typing import Optional, Dict, Tuple
from app.services.conversation_state import ConversationState, conversation_manager
from app.services.complaint_templates import (
    get_category_name, get_sub_issues, get_solution, is_other_option
)
from app.services.translations import get_text
from app.services.pdf_service import generate_property_tax_pdf
from app.db.database import SessionLocal
from app.db.models import User, Session as SessionModel, Complaint, PropertyTax, ComplaintStatus, TaxStatus
from datetime import datetime
import uuid
import logging
import re

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
        
        # Reset session if user says "hi"
        if message_text.lower().strip() == "hi":
            conversation_manager.reset_session(phone_number)
            return self._handle_login_start(phone_number)

        # Handle "Go Back" logic
        if message_text.strip() == "0":
            return self._handle_go_back(phone_number, state, lang)

        # Route based on state
        if state == ConversationState.LOGIN:
            return self._handle_login_start(phone_number)
        elif state == ConversationState.LANGUAGE_SELECTION:
            return self._handle_language_selection(phone_number, message_text)
        elif state == ConversationState.WELCOME_SELECTION:
            return self._handle_welcome_selection(phone_number, message_text, lang)
        elif state == ConversationState.TRACKING_LOGIN_ID:
            return self._handle_tracking_login_id(phone_number, message_text, lang)
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
        return self._get_state_prompt(ConversationState.LANGUAGE_SELECTION, "en", {})

    def _handle_language_selection(self, phone_number: str, choice: str) -> str:
        """Handle language selection"""
        choice = choice.strip()
        lang_map = {"1": "en", "2": "hi", "3": "gu"}
        
        if choice in lang_map:
            selected_lang = lang_map[choice]
            conversation_manager.set_user_data(phone_number, language=selected_lang)
            conversation_manager.update_state(phone_number, ConversationState.WELCOME_SELECTION)
            return self._get_state_prompt(ConversationState.WELCOME_SELECTION, selected_lang, {})
        else:
            return "Please reply with 1, 2, or 3.\n\n1. English\n2. Hindi\n3. Gujarati"

    def _handle_welcome_selection(self, phone_number: str, choice: str, lang: str) -> str:
        """Handle selection between New Complaint and Track Status"""
        choice = choice.strip()
        
        if choice == "1":
            # New Complaint -> Ask Name
            conversation_manager.update_state(phone_number, ConversationState.LOGIN_NAME)
            return get_text("welcome", lang)
        elif choice == "2":
            # Track Status -> Ask Login ID
            conversation_manager.update_state(phone_number, ConversationState.TRACKING_LOGIN_ID)
            return get_text("ask_login_id_track", lang)
        else:
            return get_text("invalid_choice", lang)

    def _handle_tracking_login_id(self, phone_number: str, login_id_input: str, lang: str) -> str:
        """Verify Login ID and fetch complaint status"""
        login_id = login_id_input.strip()
        session = conversation_manager.get_session(phone_number)
        
        db = self._get_db()
        try:
            # Check if login_id exists in User table
            user = db.query(User).filter(User.login_id == login_id).first()
            
            if not user:
                # Increment failed attempts
                failed_attempts = session.get("failed_attempts", 0) + 1
                conversation_manager.set_user_data(phone_number, failed_attempts=failed_attempts)
                
                if failed_attempts >= 3:
                    conversation_manager.update_state(phone_number, ConversationState.TERMINATED)
                    return get_text("too_many_attempts", lang)
                
                # Show remaining attempts
                remaining = 3 - failed_attempts
                error_msg = get_text("login_id_not_found", lang)
                return f"{error_msg} (Attempts remaining: {remaining})"
            
            # Reset failed attempts on success
            conversation_manager.set_user_data(phone_number, failed_attempts=0)
            
            # Fetch complaints for this user (login_id matches)
            complaints = db.query(Complaint).filter(Complaint.login_id == login_id).all()
            
            if not complaints:
                status_list = "No complaints found for this Login ID."
            else:
                lines = []
                for c in complaints:
                    status_text = c.status.value.replace("_", " ").title()
                    # Emoji mapping based on status
                    emoji = "⏳" if status_text == "Pending" else "✅" if status_text == "Resolved" else "🔧"
                    lines.append(f"🆔 {c.complaint_id}: {emoji} {status_text} ({c.sub_issue})")
                status_list = "\n".join(lines)
            
            # Update state to asking if they want anything else
            # Reusing OTHER_ISSUES state logic which asks Yes/No
            conversation_manager.update_state(phone_number, ConversationState.OTHER_ISSUES)
            return get_text("track_status_result", lang, status_list=status_list)
            
        except Exception as e:
            logger.error(f"Error fetching tracking info: {e}")
            return get_text("error", lang)
        finally:
            db.close()
    
    def _handle_login_name(self, phone_number: str, name: str, lang: str) -> str:
        """Handle name input"""
        conversation_manager.set_user_data(phone_number, name=name)
        conversation_manager.update_state(phone_number, ConversationState.LOGIN_MOBILE)
        return get_text("ask_mobile", lang, name=name)
    
    def _handle_login_mobile(self, phone_number: str, mobile: str, lang: str) -> str:
        """Handle mobile input"""
        mobile = mobile.strip()
        # Validation: 10 digits starting with 6, 7, 8, or 9
        if len(mobile) == 10 and mobile.isdigit() and mobile[0] in '6789':
            conversation_manager.set_user_data(phone_number, mobile=mobile)
            conversation_manager.update_state(phone_number, ConversationState.LOGIN_AREA_WARD)
            return get_text("ask_area_ward", lang)
        else:
            # Stay in the same state and ask for correction
            return get_text("invalid_mobile", lang)
    
    def _handle_login_area_ward(self, phone_number: str, area_ward: str, lang: str) -> str:
        """Handle merged area and ward input and complete login"""
        input_text = area_ward.strip()
        
        # Regex to match "Area Name, Ward Number" or "Area Name, Ward X"
        match = re.match(r"^([^,]+),\s*[Ww]ard\s+(\d+)$", input_text)
        
        if not match:
            return get_text("invalid_area_ward", lang)

        area = match.group(1).strip()
        ward = "Ward " + match.group(2).strip()

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
                status=ComplaintStatus.PENDING,
                latitude=session.get("location_lat"),
                longitude=session.get("location_long")
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
    
    def _handle_solution_confirmation(self, phone_number: str, response: str, lang: str):
        """Handle solution completion confirmation"""
        response_lower = response.lower().strip()
        
        # Check for button IDs or text variants
        yes_variants = ["yes", "y", "ha", "haan", "हाँ", "હા"]
        no_variants = ["no", "n", "nahi", "na", "नहीं", "ના"]
        
        if response_lower in yes_variants or any(v in response_lower for v in yes_variants):
            conversation_manager.update_state(phone_number, ConversationState.WAITING_RESOLUTION_CONFIRMATION)
            return get_text("resolution_confirm", lang)
        elif any(v in response_lower for v in no_variants):
            return self._save_complaint_as_pending(phone_number, lang)
        else:
            return get_text("yes_no_invalid", lang)
    
    def _handle_resolution_confirmation(self, phone_number: str, response: str, lang: str):
        """Handle resolution confirmation"""
        response_lower = response.lower().strip()
        yes_variants = ["yes", "y", "ha", "haan", "हाँ", "હા"]
        no_variants = ["no", "n", "nahi", "na", "नहीं", "ના"]
        
        if response_lower in yes_variants or any(v in response_lower for v in yes_variants):
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
                status=ComplaintStatus.PENDING,
                latitude=session.get("location_lat"),
                longitude=session.get("location_long")
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
                status=ComplaintStatus.RESOLVED,
                latitude=session.get("location_lat"),
                longitude=session.get("location_long")
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
    
    def _handle_property_tax_input(self, phone_number: str, receipt_no: str, lang: str) -> str:
        """Handle property tax query by receipt number"""
        db = self._get_db()
        try:
            tax_record = db.query(PropertyTax).filter(
                PropertyTax.receipt_no == receipt_no.strip().upper()
            ).first()
            
            if tax_record:
                status_emoji = {
                    "paid": "✅",
                    "due": "⚠️",
                    "pending": "⏳"
                }
                
                response = f"📋 *Property Tax Details*\n\n"
                response += f"Property ID: {tax_record.property_id}\n"
                response += f"Receipt No: {tax_record.receipt_no}\n"
                response += f"Owner: {tax_record.owner_name}\n"
                response += f"Amount: ₹{tax_record.amount}\n"
                response += f"Status: {status_emoji.get(tax_record.status.value, '')} {tax_record.status.value.upper()}\n"
                
                # Ensure PDF is generated
                try:
                    generate_property_tax_pdf(tax_record)
                except Exception as e:
                    logger.error(f"Failed to pre-generate PDF: {e}")

                # Link to the static PDF file
                pdf_filename = f"property_tax_{tax_record.property_id}.pdf"
                pdf_url = f"http://localhost:8000/pdfs/{pdf_filename}"
                
                response += f"\n📄 *View/Download Receipt:*\n{pdf_url}\n"
                
                conversation_manager.update_state(phone_number, ConversationState.OTHER_ISSUES)
                response += "\nDo you have any other issues? (Reply: Yes/No)"
                return response
            else:
                return get_text("property_not_found", lang, property_id=receipt_no)
        except Exception as e:
            logger.error(f"Error querying property tax: {e}")
            return get_text("error", lang)
        finally:
            db.close()
    
    def _handle_go_back(self, phone_number: str, current_state: ConversationState, lang: str) -> str:
        """Centralized Go Back logic"""
        back_map = {
            ConversationState.WELCOME_SELECTION: ConversationState.LANGUAGE_SELECTION,
            ConversationState.TRACKING_LOGIN_ID: ConversationState.WELCOME_SELECTION,
            ConversationState.LOGIN_NAME: ConversationState.WELCOME_SELECTION,
            ConversationState.LOGIN_MOBILE: ConversationState.LOGIN_NAME,
            ConversationState.LOGIN_AREA_WARD: ConversationState.LOGIN_MOBILE,
            ConversationState.MAIN_MENU: ConversationState.WELCOME_SELECTION,
            ConversationState.CATEGORY_SELECTED: ConversationState.MAIN_MENU,
            ConversationState.PROPERTY_TAX_INPUT: ConversationState.MAIN_MENU,
            ConversationState.SUB_ISSUE_SELECTED: ConversationState.CATEGORY_SELECTED,
            ConversationState.WAITING_IMAGE: ConversationState.SUB_ISSUE_SELECTED,
            ConversationState.WAITING_DESCRIPTION: ConversationState.SUB_ISSUE_SELECTED,
            ConversationState.WAITING_LOCATION: ConversationState.WAITING_IMAGE,
            ConversationState.WAITING_SOLUTION_CONFIRMATION: ConversationState.WAITING_LOCATION,
            ConversationState.WAITING_RESOLUTION_CONFIRMATION: ConversationState.WAITING_SOLUTION_CONFIRMATION,
            ConversationState.OTHER_ISSUES: ConversationState.MAIN_MENU
        }
        
        prev_state = back_map.get(current_state)
        
        if prev_state:
            conversation_manager.update_state(phone_number, prev_state)
            session = conversation_manager.get_session(phone_number)
            return self._get_state_prompt(prev_state, lang, session)
        else:
            return "Cannot go back further. " + get_text("greeting", lang)

    def _get_state_prompt(self, state: ConversationState, lang: str, session: dict):
        """Get the initial prompt for a given state - returns dict for buttons/lists or string for text"""
        if state == ConversationState.LANGUAGE_SELECTION:
            return {
                "type": "buttons",
                "body": "Select Language / भाषा चुनें / ભાષા પસંદ કરો",
                "buttons": [
                    {"type": "reply", "reply": {"id": "1", "title": "English"}},
                    {"type": "reply", "reply": {"id": "2", "title": "हिंदी"}},
                    {"type": "reply", "reply": {"id": "3", "title": "ગુજરાતી"}}
                ]
            }
        elif state == ConversationState.WELCOME_SELECTION:
            welcome_text = "Welcome to VMC Chatbot! 👋" if lang == "en" else ("वीएमसी चैटबॉट में आपका स्वागत है! 👋" if lang == "hi" else "VMC ચેટબોટમાં આપનું સ્વાગત છે! 👋")
            return {
                "type": "buttons",
                "body": welcome_text,
                "buttons": [
                    {"type": "reply", "reply": {"id": "1", "title": "New Complaint" if lang == "en" else ("नई शिकायत" if lang == "hi" else "નવી ફરિયાદ")}},
                    {"type": "reply", "reply": {"id": "2", "title": "Track Status" if lang == "en" else ("स्थिति ट्रैक करें" if lang == "hi" else "સ્થિતિ તપાસો")}},
                    {"type": "reply", "reply": {"id": "0", "title": "🔙 Go Back" if lang == "en" else ("🔙 वापस" if lang == "hi" else "🔙 પાછા")}}
                ]
            }
        elif state == ConversationState.TRACKING_LOGIN_ID:
            return get_text("ask_login_id_track", lang)
        elif state == ConversationState.LOGIN_NAME:
            return get_text("welcome", lang)
        elif state == ConversationState.LOGIN_MOBILE:
            return get_text("ask_mobile", lang, name=session.get("name", "User"))
        elif state == ConversationState.LOGIN_AREA_WARD:
            return get_text("ask_area_ward", lang)
        elif state == ConversationState.MAIN_MENU:
            login_id = session.get("login_id", "N/A")
            menu_intro = f"✅ Login successful!\\n\\nYour Login ID: *{login_id}*"
            if lang == "hi":
                menu_intro = f"✅ लॉगिन सफल!\\n\\nआपका लॉगिन आईडी: *{login_id}*"
            elif lang == "gu":
                menu_intro = f"✅ લોગિન સફળ!\\n\\nતમારું લોગિન આઈડી: *{login_id}*"
            
            return {
                "type": "list",
                "body": menu_intro,
                "list_button": "Select Category" if lang == "en" else ("श्रेणी चुनें" if lang == "hi" else "શ્રેણી પસંદ કરો"),
                "sections": [{
                    "title": "Categories" if lang == "en" else ("श्रेणियाँ" if lang == "hi" else "શ્રેણીઓ"),
                    "rows": [
                        {"id": "1", "title": "Sewage/Potholes" if lang == "en" else ("सीवेज/गड्ढे" if lang == "hi" else "ગટર/ખાડા"), "description": "Roads & Infrastructure"},
                        {"id": "2", "title": "Garbage" if lang == "en" else ("कचरा" if lang == "hi" else "કચરો"), "description": "Cleanliness"},
                        {"id": "3", "title": "Electricity" if lang == "en" else ("बिजली" if lang == "hi" else "વીજળી"), "description": "Power Issues"},
                        {"id": "4", "title": "Property Tax" if lang == "en" else ("संपत्ति कर" if lang == "hi" else "પ્રોપર્ટી ટેક્સ"), "description": "Tax Details"}
                    ]
                }],
                "footer": "Reply 0: Back | Hi: Restart" if lang == "en" else ("0: वापस | Hi: पुनः आरंभ" if lang == "hi" else "0: પાછા | Hi: ફરી શરૂ")
            }
        elif state == ConversationState.CATEGORY_SELECTED:
            category = session.get("current_category")
            sub_issues = get_sub_issues(category)
            category_name = get_category_name(category)
            
            rows = []
            for i, issue in enumerate(sub_issues, 1):
                rows.append({"id": str(i), "title": issue[:24], "description": issue[24:48] if len(issue) > 24 else ""})
            
            return {
                "type": "list",
                "body": f"*{category_name}*",
                "list_button": "Select Issue" if lang == "en" else ("समस्या चुनें" if lang == "hi" else "સમસ્યા પસંદ કરો"),
                "sections": [{
                    "title": "Issues" if lang == "en" else ("समस्याएं" if lang == "hi" else "સમસ્યાઓ"),
                    "rows": rows
                }],
                "footer": "Reply 0: Back | Hi: Main Menu" if lang == "en" else ("0: वापस | Hi: मुख्य मेनू" if lang == "hi" else "0: પાછા | Hi: મુખ્ય મેનૂ")
            }
        elif state == ConversationState.PROPERTY_TAX_INPUT:
            return get_text("ask_property_id", lang)
        elif state == ConversationState.WAITING_IMAGE:
            return get_text("ask_image", lang, issue=session.get("current_sub_issue", "issue"))
        elif state == ConversationState.WAITING_LOCATION:
            return get_text("ask_gps", lang)
        elif state == ConversationState.WAITING_DESCRIPTION:
            return get_text("ask_description", lang)
        elif state == ConversationState.WAITING_SOLUTION_CONFIRMATION:
            sub_issue = session.get("current_sub_issue")
            category = session.get("current_category")
            solution = get_solution(sub_issue, category)
            solution_text = f"📍 Location received.\\n\\n*Suggested Steps:*\\n{solution}\\n\\nHave you completed these?"
            
            return {
                "type": "buttons",
                "body": solution_text,
                "buttons": [
                    {"type": "reply", "reply": {"id": "yes", "title": "✅ Yes" if lang == "en" else ("✅ हाँ" if lang == "hi" else "✅ હા")}},
                    {"type": "reply", "reply": {"id": "no", "title": "❌ No" if lang == "en" else ("❌ नहीं" if lang == "hi" else "❌ ના")}},
                    {"type": "reply", "reply": {"id": "0", "title": "🔙 Back" if lang == "en" else ("🔙 वापस" if lang == "hi" else "🔙 પાછા")}}
                ]
            }
        elif state == ConversationState.WAITING_RESOLUTION_CONFIRMATION:
            return {
                "type": "buttons",
                "body": "Is your issue resolved?" if lang == "en" else ("क्या आपकी समस्या हल हो गई?" if lang == "hi" else "શું તમારી સમસ્યા ઉકેલાઈ ગઈ?"),
                "buttons": [
                    {"type": "reply", "reply": {"id": "yes", "title": "✅ Yes" if lang == "en" else ("✅ हाँ" if lang == "hi" else "✅ હા")}},
                    {"type": "reply", "reply": {"id": "no", "title": "❌ No" if lang == "en" else ("❌ नहीं" if lang == "hi" else "❌ ના")}},
                    {"type": "reply", "reply": {"id": "0", "title": "🔙 Back" if lang == "en" else ("🔙 वापस" if lang == "hi" else "🔙 પાછા")}}
                ]
            }
        elif state == ConversationState.OTHER_ISSUES:
            return {
                "type": "buttons",
                "body": "Any other issues?" if lang == "en" else ("कोई अन्य समस्या?" if lang == "hi" else "અન્ય સમસ્યા?"),
                "buttons": [
                    {"type": "reply", "reply": {"id": "yes", "title": "✅ Yes" if lang == "en" else ("✅ हाँ" if lang == "hi" else "✅ હા")}},
                    {"type": "reply", "reply": {"id": "no", "title": "❌ No" if lang == "en" else ("❌ नहीं" if lang == "hi" else "❌ ના")}},
                    {"type": "reply", "reply": {"id": "hi", "title": "🏠 Main Menu" if lang == "en" else ("🏠 मुख्य मेनू" if lang == "hi" else "🏠 મુખ્ય મેનૂ")}}
                ]
            }
            
        return "Please continue."

    def _handle_other_issues(self, phone_number: str, response: str, lang: str):
        """Handle other issues question"""
        response_lower = response.lower().strip()
        yes_variants = ["yes", "y", "ha", "haan", "हाँ", "હા"]
        no_variants = ["no", "n", "nahi", "na", "नहीं", "ના"]
        
        if response_lower in yes_variants or any(v in response_lower for v in yes_variants):
            conversation_manager.update_state(phone_number, ConversationState.MAIN_MENU)
            # Return translated main menu text (approximate reconstruction to avoid cyclic dep or complex refactor)
            # Ideally calling _handle_login_area_ward's success part or extracting it
            # For now, let's just grab the text for login_success and strip the top part or just use a new key?
            # Keeping it simple: reuse login_success template but we lack login_id variable here easily?
            # Actually we do have it in session.
            session = conversation_manager.get_session(phone_number)
            login_id = session.get("login_id", "N/A")
            return get_text("login_success", lang, login_id=login_id)
            
        elif any(v in response_lower for v in no_variants):
            conversation_manager.update_state(phone_number, ConversationState.TERMINATED)
            return get_text("terminate", lang)
        else:
            return get_text("yes_no_invalid", lang)

