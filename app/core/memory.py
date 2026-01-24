from typing import Dict, List, Any
import time

class SimpleMemory:
    def __init__(self, expiry_seconds: int = 3600):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.expiry_seconds = expiry_seconds

    def get_session(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                "history": [],
                "last_active": time.time(),
                "language": None
            }
        
        # Check for expiry
        session = self.sessions[user_id]
        if time.time() - session["last_active"] > self.expiry_seconds:
            session["history"] = []
            session["language"] = None
        
        session["last_active"] = time.time()
        return session

    def update_language(self, user_id: str, language: str):
        session = self.get_session(user_id)
        session["language"] = language

    def add_message(self, user_id: str, role: str, content: str):
        session = self.get_session(user_id)
        session["history"].append({"role": role, "content": content})
        # Keep history manageable
        if len(session["history"]) > 10:
            session["history"].pop(0)

memory = SimpleMemory()
