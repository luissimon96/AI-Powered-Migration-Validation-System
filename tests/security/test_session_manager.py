"""Unit tests for session manager module.
Ultra-compressed test implementation for T001 completion.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from src.security.session_manager import SessionData, SessionManager, session_manager


class TestSessionData:
    """Test SessionData model."""

    def test_session_data_creation(self):
        """Test SessionData model creation."""
        data = SessionData(
            user_id="user123",
            api_key_id="key456",
            created_at=datetime.utcnow(),
            last_access=datetime.utcnow(),
            ip_address="192.168.1.1",
            user_agent="test-agent",
            scopes=["read", "write"],
        )

        assert data.user_id == "user123"
        assert data.api_key_id == "key456"
        assert len(data.scopes) == 2
        assert data.metadata == {}


class TestSessionManager:
    """Test SessionManager class."""

    @pytest.fixture
    def manager(self):
        """Fresh session manager for each test."""
        return SessionManager()

    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request."""
        request = Mock()
        request.client.host = "192.168.1.1"
        request.headers = {"user-agent": "test-browser"}
        return request

    @pytest.mark.asyncio
    async def test_create_session(self, manager, mock_request):
        """Test session creation."""
        session_id = await manager.create_session(
            user_id="user123",
            api_key_id="key456",
            request=mock_request,
            scopes=["read", "write"],
        )

        assert session_id.startswith("sess_user123_")
        assert session_id in manager.sessions

        session = manager.sessions[session_id]
        assert session.user_id == "user123"
        assert session.ip_address == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_valid_session(self, manager, mock_request):
        """Test getting valid session."""
        # Create session
        session_id = await manager.create_session(
            "user123",
            "key456",
            mock_request,
            ["read"],
        )

        # Get session
        session = await manager.get_session(session_id)
        assert session is not None
        assert session.user_id == "user123"

    @pytest.mark.asyncio
    async def test_get_invalid_session(self, manager):
        """Test getting non-existent session."""
        session = await manager.get_session("invalid_id")
        assert session is None

    @pytest.mark.asyncio
    async def test_session_timeout(self, manager, mock_request):
        """Test session timeout behavior."""
        # Create session
        session_id = await manager.create_session(
            "user123",
            "key456",
            mock_request,
            ["read"],
        )

        # Simulate timeout
        session_data = manager.sessions[session_id]
        session_data.last_access = datetime.utcnow() - timedelta(hours=2)

        # Should return None and remove session
        result = await manager.get_session(session_id)
        assert result is None
        assert session_id not in manager.sessions

    @pytest.mark.asyncio
    async def test_invalidate_session(self, manager, mock_request):
        """Test session invalidation."""
        # Create session
        session_id = await manager.create_session(
            "user123",
            "key456",
            mock_request,
            ["read"],
        )

        # Invalidate
        result = await manager.invalidate_session(session_id)
        assert result is True
        assert session_id not in manager.sessions

        # Second invalidation should return False
        result = await manager.invalidate_session(session_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_access_time_update(self, manager, mock_request):
        """Test last access time updates."""
        session_id = await manager.create_session(
            "user123",
            "key456",
            mock_request,
            ["read"],
        )

        original_time = manager.sessions[session_id].last_access

        # Small delay
        await asyncio.sleep(0.01)

        # Access session
        session = await manager.get_session(session_id)
        updated_time = session.last_access

        assert updated_time > original_time

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, manager, mock_request):
        """Test expired session cleanup."""
        # Create multiple sessions
        session1 = await manager.create_session("user1", "key1", mock_request, ["read"])
        session2 = await manager.create_session("user2", "key2", mock_request, ["read"])

        # Expire first session
        manager.sessions[session1].last_access = datetime.utcnow() - timedelta(hours=2)

        await manager.cleanup_expired()

        assert session1 not in manager.sessions
        assert session2 in manager.sessions

    def test_session_timeout_configuration(self, manager):
        """Test session timeout configuration."""
        assert manager.session_timeout == 3600  # 1 hour default

    @pytest.mark.asyncio
    async def test_multiple_sessions_same_user(self, manager, mock_request):
        """Test multiple sessions for same user."""
        session1 = await manager.create_session(
            "user123", "key1", mock_request, ["read"]
        )
        session2 = await manager.create_session(
            "user123", "key2", mock_request, ["write"]
        )

        assert session1 != session2
        assert len(manager.sessions) == 2

        data1 = await manager.get_session(session1)
        data2 = await manager.get_session(session2)

        assert data1.api_key_id == "key1"
        assert data2.api_key_id == "key2"


class TestGlobalSessionManager:
    """Test global session manager instance."""

    def test_global_instance_exists(self):
        """Test global session manager exists."""
        assert session_manager is not None
        assert isinstance(session_manager, SessionManager)

    @pytest.mark.asyncio
    async def test_global_instance_functionality(self):
        """Test global instance basic functionality."""
        # Use mock request
        request = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "pytest"}

        session_id = await session_manager.create_session(
            "test_user",
            "test_key",
            request,
            ["test"],
        )

        assert session_id is not None

        # Cleanup
        await session_manager.invalidate_session(session_id)


# Import asyncio for sleep function
