from typing import Optional, Dict
from app.services.conversation_state import ConversationState, conversation_manager
from app.services.complaint_templates import (
    get_category_name, get_sub_issues, get_solution, is_other_option
)
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
    
    def process_message(self, phone_number: str, message_text: str, image_url: Optional[str] = None) -> str:
        """Process incoming message and return response"""
        session = conversation_manager.get_session(phone_number)
        state = ConversationState(session["state"])
        
        # Handle image uploads
        if image_url:
            return self._handle_image_upload(phone_number, image_url, state)
        
        # Route based on state
        if state == ConversationState.LOGIN:
            return self._handle_login_start(phone_number)
        elif state == ConversationState.LOGIN_NAME:
            return self._handle_login_name(phone_number, message_text)
        elif state == ConversationState.LOGIN_MOBILE:
            return self._handle_login_mobile(phone_number, message_text)
        elif state == ConversationState.LOGIN_AREA:
            return self._handle_login_area(phone_number, message_text)
        elif state == ConversationState.LOGIN_WARD:
            return self._handle_login_ward(phone_number, message_text)
        elif state == ConversationState.MAIN_MENU:
            return self._handle_main_menu(phone_number, message_text)
        elif state == ConversationState.CATEGORY_SELECTED:
            return self._handle_category_selection(phone_number, message_text)
        elif state == ConversationState.SUB_ISSUE_SELECTED:
            return self._handle_sub_issue_selection(phone_number, message_text)
        elif state == ConversationState.WAITING_DESCRIPTION:
            return self._handle_description(phone_number, message_text)
        elif state == ConversationState.WAITING_SOLUTION_CONFIRMATION:
            return self._handle_solution_confirmation(phone_number, message_text)
        elif state == ConversationState.WAITING_RESOLUTION_CONFIRMATION:
            return self._handle_resolution_confirmation(phone_number, message_text)
        elif state == ConversationState.PROPERTY_TAX_INPUT:
            return self._handle_property_tax_input(phone_number, message_text)
        elif state == ConversationState.OTHER_ISSUES:
            return self._handle_other_issues(phone_number, message_text)
        else:
            return "Invalid state. Please start over by sending 'Hi'."
    
    def _handle_login_start(self, phone_number: str) -> str:
        """Start login flow"""
        conversation_manager.update_state(phone_number, ConversationState.LOGIN_NAME)
        return "Welcome to VMC Chatbot! 👋\n\nPlease provide your name:"
    
    def _handle_login_name(self, phone_number: str, name: str) -> str:
        """Handle name input"""
        conversation_manager.set_user_data(phone_number, name=name)
        conversation_manager.update_state(phone_number, ConversationState.LOGIN_MOBILE)
        return f"Thank you, {name}! Please provide your mobile number:"
    
    def _handle_login_mobile(self, phone_number: str, mobile: str) -> str:
        """Handle mobile input"""
        conversation_manager.set_user_data(phone_number, mobile=mobile)
        conversation_manager.update_state(phone_number, ConversationState.LOGIN_AREA)
        return "Please provide your area:"
    
    def _handle_login_area(self, phone_number: str, area: str) -> str:
        """Handle area input"""
        conversation_manager.set_user_data(phone_number, area=area)
        conversation_manager.update_state(phone_number, ConversationState.LOGIN_WARD)
        return "Please provide your ward number:"
    
    def _handle_login_ward(self, phone_number: str, ward: str) -> str:
        """Handle ward input and complete login"""
        session = conversation_manager.get_session(phone_number)
        login_id = conversation_manager.generate_login_id()
        
        # Save user to database
        db = self._get_db()
        try:
            user = User(
                login_id=login_id,
                name=session["name"],
                mobile=session["mobile"],
                area=session["area"],
                ward_number=ward
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            conversation_manager.set_user_data(
                phone_number,
                user_id=user.id,
                login_id=login_id,
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
            return f"✅ Login successful!\n\nYour Login ID: {login_id}\n\nPlease select an option:\n\n1️⃣ Sewage/Potholes/Roads\n2️⃣ Garbage/Cleanliness\n3️⃣ Electricity Issues\n4️⃣ Property Tax Details\n\nReply with 1, 2, 3, or 4"
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            db.rollback()
            return "Error during login. Please try again."
        finally:
            db.close()
    
    def _handle_main_menu(self, phone_number: str, choice: str) -> str:
        """Handle main menu selection"""
        choice = choice.strip()
        session = conversation_manager.get_session(phone_number)
        
        if choice == "1":
            conversation_manager.set_user_data(phone_number, current_category="sewage_potholes_roads")
            conversation_manager.update_state(phone_number, ConversationState.CATEGORY_SELECTED)
            sub_issues = get_sub_issues("sewage_potholes_roads")
            return self._format_sub_issues_menu(sub_issues, "Sewage/Potholes/Roads")
        elif choice == "2":
            conversation_manager.set_user_data(phone_number, current_category="garbage_cleanliness")
            conversation_manager.update_state(phone_number, ConversationState.CATEGORY_SELECTED)
            sub_issues = get_sub_issues("garbage_cleanliness")
            return self._format_sub_issues_menu(sub_issues, "Garbage/Cleanliness")
        elif choice == "3":
            conversation_manager.set_user_data(phone_number, current_category="electricity_issues")
            conversation_manager.update_state(phone_number, ConversationState.CATEGORY_SELECTED)
            sub_issues = get_sub_issues("electricity_issues")
            return self._format_sub_issues_menu(sub_issues, "Electricity Issues")
        elif choice == "4":
            conversation_manager.update_state(phone_number, ConversationState.PROPERTY_TAX_INPUT)
            return "Please provide your Property ID:"
        else:
            return "Invalid choice. Please reply with 1, 2, 3, or 4"
    
    def _format_sub_issues_menu(self, sub_issues: list, category_name: str) -> str:
        """Format sub-issues menu"""
        menu = f"Select an issue under {category_name}:\n\n"
        for i, issue in enumerate(sub_issues, 1):
            menu += f"{i}️⃣ {issue}\n"
        return menu
    
    def _handle_category_selection(self, phone_number: str, choice: str) -> str:
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
                    return "Please describe your issue in detail:"
                else:
                    conversation_manager.update_state(phone_number, ConversationState.WAITING_IMAGE)
                    return f"Issue selected: {selected_issue}\n\nPlease upload an image for verification:"
            else:
                return f"Invalid choice. Please select 1-{len(sub_issues)}"
        except ValueError:
            return "Please reply with a number"
    
    def _handle_sub_issue_selection(self, phone_number: str, message: str) -> str:
        """This should not be called as state transitions to WAITING_IMAGE"""
        return "Please upload an image"
    
    def _handle_image_upload(self, phone_number: str, image_url: str, state: ConversationState) -> str:
        """Handle image upload"""
        session = conversation_manager.get_session(phone_number)
        conversation_manager.set_user_data(phone_number, image_url=image_url)
        
        if state == ConversationState.WAITING_IMAGE:
            sub_issue = session["current_sub_issue"]
            category = session["current_category"]
            solution = get_solution(sub_issue, category)
            
            conversation_manager.update_state(phone_number, ConversationState.WAITING_SOLUTION_CONFIRMATION)
            return f"✅ Image received!\n\nHere are the suggested steps:\n\n{solution}\n\nHave you completed these steps? (Reply: Yes/No)"
        
        return "Image received. Processing..."
    
    def _handle_description(self, phone_number: str, description: str) -> str:
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
            
            return "We will look after it. Thank you."
        except Exception as e:
            logger.error(f"Error saving complaint: {e}")
            db.rollback()
            return "Error saving complaint. Please try again."
        finally:
            db.close()
    
    def _handle_solution_confirmation(self, phone_number: str, response: str) -> str:
        """Handle solution completion confirmation"""
        response_lower = response.lower().strip()
        
        if response_lower in ["yes", "y"]:
            conversation_manager.update_state(phone_number, ConversationState.WAITING_RESOLUTION_CONFIRMATION)
            return "Is your issue resolved now? (Reply: Yes/No)"
        elif response_lower in ["no", "n"]:
            return self._save_complaint_as_pending(phone_number)
        else:
            return "Please reply with Yes or No"
    
    def _handle_resolution_confirmation(self, phone_number: str, response: str) -> str:
        """Handle resolution confirmation"""
        response_lower = response.lower().strip()
        
        if response_lower in ["yes", "y"]:
            return self._mark_complaint_resolved(phone_number)
        elif response_lower in ["no", "n"]:
            return self._save_complaint_as_pending(phone_number)
        else:
            return "Please reply with Yes or No"
    
    def _save_complaint_as_pending(self, phone_number: str) -> str:
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
            db.add(complaint)
            db.commit()
            
            conversation_manager.set_user_data(phone_number, complaint_id=complaint_id)
            conversation_manager.update_state(phone_number, ConversationState.OTHER_ISSUES)
            
            return "Our team will handle it. Thank you for reporting.\n\nDo you have any other issues? (Reply: Yes/No)"
        except Exception as e:
            logger.error(f"Error saving complaint: {e}")
            db.rollback()
            return "Error saving complaint. Please try again."
        finally:
            db.close()
    
    def _mark_complaint_resolved(self, phone_number: str) -> str:
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
            
            return "✅ Great! Your complaint has been marked as resolved.\n\nDo you have any other issues? (Reply: Yes/No)"
        except Exception as e:
            logger.error(f"Error saving complaint: {e}")
            db.rollback()
            return "Error saving complaint. Please try again."
        finally:
            db.close()
    
    def _handle_property_tax_input(self, phone_number: str, property_id: str) -> str:
        """Handle property tax query"""
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
                
                response = f"Property Tax Details:\n\n"
                response += f"Property ID: {tax_record.property_id}\n"
                response += f"Owner: {tax_record.owner_name}\n"
                response += f"Address: {tax_record.address}\n"
                response += f"Amount: ₹{tax_record.amount}\n"
                response += f"Year: {tax_record.year}\n"
                response += f"Status: {status_emoji.get(tax_record.status.value, '')} {tax_record.status.value.upper()}\n"
                
                if tax_record.receipt_no:
                    response += f"Receipt No: {tax_record.receipt_no}\n"
                if tax_record.bill_no:
                    response += f"Bill No: {tax_record.bill_no}\n"
                
                # Generate PDF link (will be implemented in PDF service)
                pdf_url = f"/api/property-tax/pdf/{property_id}"
                response += f"\n📄 PDF: {pdf_url}\n"
                
                conversation_manager.update_state(phone_number, ConversationState.OTHER_ISSUES)
                response += "\nDo you have any other issues? (Reply: Yes/No)"
                return response
            else:
                return f"Property ID '{property_id}' not found. Please check and try again."
        except Exception as e:
            logger.error(f"Error querying property tax: {e}")
            return "Error retrieving property tax information. Please try again."
        finally:
            db.close()
    
    def _handle_other_issues(self, phone_number: str, response: str) -> str:
        """Handle other issues question"""
        response_lower = response.lower().strip()
        
        if response_lower in ["yes", "y"]:
            conversation_manager.update_state(phone_number, ConversationState.MAIN_MENU)
            return "Please select an option:\n\n1️⃣ Sewage/Potholes/Roads\n2️⃣ Garbage/Cleanliness\n3️⃣ Electricity Issues\n4️⃣ Property Tax Details\n\nReply with 1, 2, 3, or 4"
        elif response_lower in ["no", "n"]:
            conversation_manager.update_state(phone_number, ConversationState.TERMINATED)
            return "Thank you for contacting us. This chat will be terminated."
        else:
            return "Please reply with Yes or No"
