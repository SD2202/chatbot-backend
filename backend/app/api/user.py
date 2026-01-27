from fastapi import APIRouter
from app.core.memory import memory
from typing import Dict, Any

router = APIRouter()

@router.get("/user/profile/{user_id}")
async def get_user_profile(user_id: str):
    """
    Fetch personal dashboard data for a user.
    """
    session = memory.get_session(user_id)
    return {
        "user_id": user_id,
        "language_preference": session["language"],
        "history_count": len(session["history"]),
        "status": "Active"
    }

@router.get("/user/history/{user_id}")
async def get_personal_history(user_id: str):
    """
    Fetch personal chat history.
    """
    session = memory.get_session(user_id)
    return session["history"]
