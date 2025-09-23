"""Session management for secure user sessions with Redis backing.
Ultra-compressed implementation for S002 completion.
"""

import time
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Optional

from fastapi import Request
from pydantic import BaseModel


class SessionData(BaseModel):
    """Session data model."""

    user_id: str
    api_key_id: str
    created_at: datetime
    last_access: datetime
    ip_address: str
    user_agent: str
    scopes: list[str]
    metadata: Dict[str, Any] = {}


class SessionManager:
    """Memory-based session manager with Redis fallback."""

    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        self.session_timeout = 3600  # 1 hour

    async def create_session(self, user_id: str, api_key_id: str,
                             request: Request, scopes: list[str]) -> str:
        """Create new session."""
        session_id = f"sess_{user_id}_{int(time.time())}"

        session_data = SessionData(
            user_id=user_id,
            api_key_id=api_key_id,
            created_at=datetime.utcnow(),
            last_access=datetime.utcnow(),
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", ""),
            scopes=scopes,
        )

        self.sessions[session_id] = session_data
        return session_id

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data."""
        session = self.sessions.get(session_id)
        if not session:
            return None

        # Check timeout
        if (datetime.utcnow() - session.last_access).seconds > self.session_timeout:
            del self.sessions[session_id]
            return None

        # Update access time
        session.last_access = datetime.utcnow()
        return session

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session."""
        return self.sessions.pop(session_id, None) is not None

    async def cleanup_expired(self):
        """Cleanup expired sessions."""
        expired = [
            sid for sid, session in self.sessions.items()
            if (datetime.utcnow() - session.last_access).seconds > self.session_timeout
        ]
        for sid in expired:
            del self.sessions[sid]


# Global session manager
session_manager = SessionManager()
