from app.services.conversation_router import ConversationRouter
from app.services.conversation_state import conversation_manager, ConversationState
from app.db.database import SessionLocal
from app.db.models import User
import uuid

def verify_tracking():
    router = ConversationRouter()
    phone = f"TEST-{uuid.uuid4().hex[:8]}"
    
    print(f"--- Starting Test for {phone} ---")
    
    # 1. Start
    resp = router.process_message(phone, "Hi")
    print(f"User: Hi\nBot: {resp}\n")
    
    # 2. Select Language (English)
    resp = router.process_message(phone, "1")
    print(f"User: 1\nBot: {resp}\n")
    
    # 3. Select Track Status
    resp = router.process_message(phone, "2")
    print(f"User: 2\nBot: {resp}\n")
    
    # Get a valid login ID from DB
    db = SessionLocal()
    valid_user = db.query(User).first()
    db.close()
    
    if not valid_user:
        print("No users in DB to test with!")
        return

    test_login_id = valid_user.login_id
    print(f"Using Login ID: {test_login_id}")

    # 4. Provide Login ID
    resp = router.process_message(phone, test_login_id)
    print(f"User: {test_login_id}\nBot: {resp}\n")
    
    # 5. Say Yes to continue
    resp = router.process_message(phone, "Yes")
    print(f"User: Yes\nBot: {resp}\n")

if __name__ == "__main__":
    verify_tracking()
