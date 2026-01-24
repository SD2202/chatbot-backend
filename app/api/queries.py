from fastapi import APIRouter
from app.core.memory import memory
from typing import List, Dict

router = APIRouter()

@router.get("/admin/queries")
async def get_all_queries():
    """
    Fetch all chatbot queries and session logs for the Admin dashboard.
    """
    all_sessions = []
    for user_id, data in memory.sessions.items():
        all_sessions.append({
            "user_id": user_id,
            "last_active": data["last_active"],
            "language": data["language"],
            "message_count": len(data["history"]),
            "recent_messages": data["history"][-5:] if data["history"] else []
        })
    return sorted(all_sessions, key=lambda x: x["last_active"], reverse=True)

@router.get("/admin/queries/{user_id}")
async def get_user_query_history(user_id: str):
    """
    Fetch full chat history for a specific user.
    """
    session = memory.get_session(user_id)
    return session["history"]
