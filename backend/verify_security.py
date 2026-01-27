from app.services.conversation_router import ConversationRouter
from app.services.conversation_state import conversation_manager, ConversationState
import uuid

def verify_lockout():
    router = ConversationRouter()
    phone = f"SECURE-{uuid.uuid4().hex[:8]}"
    
    print(f"--- Starting Security Test for {phone} ---")
    
    # 1. Start
    router.process_message(phone, "Hi")
    # 2. Select Language (English)
    router.process_message(phone, "1")
    # 3. Select Track Status
    resp = router.process_message(phone, "2")
    print(f"Bot: {resp}\n")
    
    # 4. Provide INCORRECT Login ID (Attempt 1)
    resp = router.process_message(phone, "WRONG-1")
    print(f"User: WRONG-1\nBot: {resp}\n")
    
    # 5. Provide INCORRECT Login ID (Attempt 2)
    resp = router.process_message(phone, "WRONG-2")
    print(f"User: WRONG-2\nBot: {resp}\n")
    
    # 6. Provide INCORRECT Login ID (Attempt 3) - SHould trigger lockout
    resp = router.process_message(phone, "WRONG-3")
    print(f"User: WRONG-3\nBot: {resp}\n")
    
    # 7. Verify state is terminated
    session = conversation_manager.get_session(phone)
    print(f"Final State: {session['state']}")

if __name__ == "__main__":
    verify_lockout()
