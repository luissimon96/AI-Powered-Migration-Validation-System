"""
Unit tests for BrowserAutomationEngine core functionality.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.behavioral.browser_automation import (
    BrowserAction, BrowserActionResult, BrowserAutomationEngine,
    BrowserSession, create_comprehensive_validation_scenario,
    create_form_submission_scenario, create_login_scenario)
from src.core.models import SeverityLevel, ValidationDiscrepancy


@pytest.mark.unit
class TestBrowserAction:
    """Test BrowserAction dataclass functionality."""

    def test_browser_action_creation(self):
        """Test creating a browser action."""
        action = BrowserAction(
            action_type="navigate",
            target="https://example.com",
            value="",
            timeout=10000,
            description="Navigate to example site",
            wait_for="body",
        )

        assert action.action_type == "navigate"
        assert action.target == "https://example.com"
        assert action.timeout == 10000
        assert action.description == "Navigate to example site"
        assert action.wait_for == "body"

    def test_browser_action_defaults(self):
        """Test browser action with default values."""
        action = BrowserAction(action_type="click")

        assert action.action_type == "click"
        assert action.target == ""
        assert action.value == ""
        assert action.timeout == 10000
        assert action.description == ""
        assert action.wait_for is None


@pytest.mark.unit
class TestBrowserActionResult:
    """Test BrowserActionResult dataclass functionality."""

    def test_browser_action_result_creation(self):
        """Test creating a browser action result."""
        action = BrowserAction(action_type="click", target="#button")

        result = BrowserActionResult(
            success=True,
            action=action,
            result_data={"clicked": True},
            execution_time=1.5,
        )

        assert result.success is True
        assert result.action == action
        assert result.result_data["clicked"] is True
        assert result.execution_time == 1.5
        assert result.timestamp is not None

    def test_browser_action_result_timestamp_auto_set(self):
        """Test that timestamp is automatically set."""
        action = BrowserAction(action_type="fill")
        result = BrowserActionResult(success=True, action=action)

        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)


@pytest.mark.unit
class TestBrowserSession:
    """Test BrowserSession dataclass functionality."""

    def test_browser_session_creation(self):
        """Test creating a browser session."""
        session = BrowserSession(
            session_id="test-session-123",
            url="https://example.com",
            actions=[],
            results=[],
            metadata={"test": True},
            start_time=datetime.now(),
        )

        assert session.session_id == "test-session-123"
        assert session.url == "https://example.com"
        assert session.actions == []
        assert session.results == []
        assert session.metadata["test"] is True
        assert session.end_time is None

    def test_browser_session_duration_calculation(self):
        """Test session duration calculation."""
        start_time = datetime.now()
        session = BrowserSession(
            session_id="test",
            url="https://example.com",
            actions=[],
            results=[],
            metadata={},
            start_time=start_time,
        )

        # Duration should be very small (just created)
        assert session.duration >= 0
        assert session.duration < 1.0  # Less than 1 second

        # Test with end time set
        import time

        time.sleep(0.1)  # Wait a bit
        session.end_time = datetime.now()
        assert session.duration >= 0.1


@pytest.mark.unit
class TestBrowserAutomationEngine:
    """Test BrowserAutomationEngine core functionality."""

    def test_engine_initialization_config(self):
        """Test engine initialization with configuration."""
        engine = BrowserAutomationEngine(headless=False, slow_mo=100, timeout=30000)

        assert engine.headless is False
        assert engine.slow_mo == 100
        assert engine.default_timeout == 30000
        assert engine.playwright is None
        assert engine.browser is None
        assert engine.current_page is None

    def test_engine_default_configuration(self):
        """Test engine with default configuration."""
        engine = BrowserAutomationEngine()

        assert engine.headless is True
        assert engine.slow_mo == 0
        assert engine.default_timeout == 30000
        assert engine.screenshot_dir.exists()

    @pytest.mark.asyncio
    async def test_engine_initialization_no_playwright(self):
        """Test engine initialization when Playwright is not available."""
        with patch("src.behavioral.browser_automation.async_playwright", None):
            engine = BrowserAutomationEngine()
            success = await engine.initialize()

            assert success is False

    @pytest.mark.asyncio
    async def test_session_management(self):
        """Test session start and end functionality."""
        engine = BrowserAutomationEngine()

        # Test starting session
        session_id = await engine.start_session("https://example.com", {"test": True})

        assert session_id is not None
        assert engine.current_session is not None
        assert engine.current_session.session_id == session_id
        assert engine.current_session.url == "https://example.com"
        assert engine.current_session.metadata["test"] is True

        # Test ending session
        ended_session = await engine.end_session()

        assert ended_session is not None
        assert ended_session.session_id == session_id
        assert ended_session.end_time is not None
        assert engine.current_session is None

    @pytest.mark.asyncio
    async def test_session_end_without_active_session(self):
        """Test ending session when no session is active."""
        engine = BrowserAutomationEngine()

        ended_session = await engine.end_session()
        assert ended_session is None

    @pytest.mark.asyncio
    async def test_execute_action_no_page(self):
        """Test executing action when no page is available."""
        engine = BrowserAutomationEngine()
        action = BrowserAction(action_type="navigate", target="https://example.com")

        result = await engine.execute_action(action)

        assert result.success is False
        assert "No active browser page" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_action_unknown_type(self):
        """Test executing action with unknown type."""
        engine = BrowserAutomationEngine()
        engine.current_page = AsyncMock()  # Mock page

        action = BrowserAction(action_type="unknown_action")
        result = await engine.execute_action(action)

        assert result.success is False
        assert "Unknown action type" in result.error_message

    @pytest.mark.asyncio
    async def test_capture_page_state_no_page(self):
        """Test capturing page state when no page is available."""
        engine = BrowserAutomationEngine()

        state = await engine.capture_page_state()
        assert state == {}

    @pytest.mark.asyncio
    async def test_capture_page_state_with_error(self):
        """Test capturing page state when an error occurs."""
        engine = BrowserAutomationEngine()
        mock_page = AsyncMock()
        mock_page.url = "https://example.com"
        mock_page.title.side_effect = Exception("Page access error")
        engine.current_page = mock_page

        state = await engine.capture_page_state()
        assert "error" in state
        assert "Page access error" in state["error"]

    @pytest.mark.asyncio
    async def test_compare_page_states_basic(self):
        """Test basic page state comparison."""
        engine = BrowserAutomationEngine()

        state1 = {
            "title": "Source Page",
            "forms": [{"elements": []}],
            "messages": [{"text": "Welcome"}],
            "metrics": {"forms": 1, "inputs": 2},
        }

        state2 = {
            "title": "Target Page",
            "forms": [{"elements": []}],
            "messages": [{"text": "Welcome"}],
            "metrics": {"forms": 1, "inputs": 3},  # Different input count
        }

        discrepancies = await engine.compare_page_states(state1, state2)

        assert len(discrepancies) >= 2  # Title and input count differences

        # Check for title mismatch
        title_discrepancy = any(disc.type == "title_mismatch" for disc in discrepancies)
        assert title_discrepancy

        # Check for input count difference
        input_discrepancy = any(
            "inputs_count_difference" in disc.type for disc in discrepancies
        )
        assert input_discrepancy

    @pytest.mark.asyncio
    async def test_compare_page_states_form_mismatch(self):
        """Test page state comparison with form count mismatch."""
        engine = BrowserAutomationEngine()

        state1 = {"forms": [{"elements": []}, {"elements": []}]}  # 2 forms
        state2 = {"forms": [{"elements": []}]}  # 1 form

        discrepancies = await engine.compare_page_states(state1, state2)

        form_mismatch = any(
            disc.type == "form_count_mismatch" for disc in discrepancies
        )
        assert form_mismatch

    @pytest.mark.asyncio
    async def test_compare_page_states_message_differences(self):
        """Test page state comparison with message differences."""
        engine = BrowserAutomationEngine()

        state1 = {"messages": [{"text": "Success message"}, {"text": "Common message"}]}
        state2 = {
            "messages": [
                {"text": "Different success message"},
                {"text": "Common message"},
            ]
        }

        discrepancies = await engine.compare_page_states(state1, state2)

        # Should find missing and additional messages
        missing_msg = any(disc.type == "missing_message" for disc in discrepancies)
        additional_msg = any(
            disc.type == "additional_message" for disc in discrepancies
        )

        assert missing_msg or additional_msg

    @pytest.mark.asyncio
    async def test_compare_page_states_with_exception(self):
        """Test page state comparison when an exception occurs."""
        engine = BrowserAutomationEngine()

        # Provide invalid state data to trigger exception
        state1 = {"forms": "invalid_data"}  # Should be list
        state2 = {"forms": []}

        discrepancies = await engine.compare_page_states(state1, state2)

        # Should contain error discrepancy
        assert len(discrepancies) == 1
        assert discrepancies[0].type == "comparison_error"
        assert discrepancies[0].severity == SeverityLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_cleanup_resources(self):
        """Test cleanup of browser resources."""
        engine = BrowserAutomationEngine()

        # Mock browser components
        engine.current_page = AsyncMock()
        engine.context = AsyncMock()
        engine.browser = AsyncMock()
        engine.playwright = AsyncMock()

        await engine.cleanup()

        # Verify cleanup was called
        engine.current_page.close.assert_called_once()
        engine.context.close.assert_called_once()
        engine.browser.close.assert_called_once()
        engine.playwright.stop.assert_called_once()

        # Verify references are cleared
        assert engine.current_page is None
        assert engine.context is None
        assert engine.browser is None
        assert engine.playwright is None

    @pytest.mark.asyncio
    async def test_cleanup_with_exceptions(self):
        """Test cleanup when exceptions occur."""
        engine = BrowserAutomationEngine()

        # Mock browser components that raise exceptions
        mock_page = AsyncMock()
        mock_page.close.side_effect = Exception("Close error")
        engine.current_page = mock_page

        # Should not raise exception
        await engine.cleanup()

        # References should still be cleared
        assert engine.current_page is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using engine as async context manager."""
        with patch("src.behavioral.browser_automation.async_playwright", None):
            async with BrowserAutomationEngine() as engine:
                assert isinstance(engine, BrowserAutomationEngine)
                # Engine should attempt initialization but fail gracefully


@pytest.mark.unit
class TestScenarioCreation:
    """Test scenario creation functions."""

    def test_create_login_scenario(self):
        """Test creating login scenario."""
        actions = create_login_scenario(
            username="testuser",
            password="testpass123",
            login_url="https://example.com/login",
        )

        assert (
            len(actions) == 6
        )  # navigate, fill username, fill password, click, wait, capture

        # Check navigation action
        nav_action = actions[0]
        assert nav_action.action_type == "navigate"
        assert nav_action.target == "https://example.com/login"

        # Check username fill action
        username_action = actions[1]
        assert username_action.action_type == "fill"
        assert username_action.value == "testuser"

        # Check password fill action
        password_action = actions[2]
        assert password_action.action_type == "fill"
        assert password_action.value == "testpass123"

        # Check submit action
        submit_action = actions[3]
        assert submit_action.action_type == "click"

        # Check wait action
        wait_action = actions[4]
        assert wait_action.action_type == "wait"

        # Check capture action
        capture_action = actions[5]
        assert capture_action.action_type == "capture"

    def test_create_form_submission_scenario(self):
        """Test creating form submission scenario."""
        form_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "message": "Test message",
        }

        actions = create_form_submission_scenario("#contact-form", form_data)

        # Should have fill actions for each field + submit + capture
        assert len(actions) == len(form_data) + 2

        # Check fill actions
        fill_actions = [a for a in actions if a.action_type == "fill"]
        assert len(fill_actions) == len(form_data)

        # Check form data values are present
        fill_values = [a.value for a in fill_actions]
        assert "John Doe" in fill_values
        assert "john@example.com" in fill_values
        assert "555-1234" in fill_values
        assert "Test message" in fill_values

        # Check submit action
        submit_actions = [a for a in actions if a.action_type == "submit"]
        assert len(submit_actions) == 1
        assert submit_actions[0].target == "#contact-form"

        # Check capture action
        capture_actions = [a for a in actions if a.action_type == "capture"]
        assert len(capture_actions) == 1

    def test_create_form_submission_scenario_empty_data(self):
        """Test creating form submission scenario with empty data."""
        actions = create_form_submission_scenario("#form", {})

        # Should have submit + capture actions only
        assert len(actions) == 2
        assert actions[0].action_type == "submit"
        assert actions[1].action_type == "capture"

    def test_create_comprehensive_validation_scenario_basic(self):
        """Test creating comprehensive validation scenario without credentials."""
        actions = create_comprehensive_validation_scenario("https://example.com")

        assert len(actions) >= 3  # At least navigate, capture, wait

        # Check initial navigation
        nav_action = actions[0]
        assert nav_action.action_type == "navigate"
        assert nav_action.target == "https://example.com"

        # Check initial capture
        capture_actions = [a for a in actions if a.action_type == "capture"]
        assert len(capture_actions) >= 1

        # Check evaluation actions
        eval_actions = [a for a in actions if a.action_type == "evaluate"]
        assert len(eval_actions) >= 3  # Count forms, inputs, buttons

    def test_create_comprehensive_validation_scenario_with_credentials(self):
        """Test creating comprehensive validation scenario with credentials."""
        credentials = {
            "username": "testuser",
            "password": "testpass",
            "login_url": "https://example.com/login",
        }

        actions = create_comprehensive_validation_scenario(
            "https://example.com", credentials
        )

        # Should include login scenario actions
        assert len(actions) > 10  # Basic actions + login actions

        # Check for login-related actions
        nav_actions = [a for a in actions if a.action_type == "navigate"]
        login_nav = any("login" in action.target.lower() for action in nav_actions)
        assert login_nav

        # Check for fill actions (login credentials)
        fill_actions = [a for a in actions if a.action_type == "fill"]
        fill_values = [a.value for a in fill_actions]
        assert "testuser" in fill_values
        assert "testpass" in fill_values

    def test_create_comprehensive_validation_scenario_custom_login_url(self):
        """Test comprehensive scenario with custom login URL."""
        credentials = {
            "username": "user",
            "password": "pass",
            # No login_url provided
        }

        base_url = "https://myapp.com"
        actions = create_comprehensive_validation_scenario(base_url, credentials)

        # Should default to base_url + '/login'
        nav_actions = [a for a in actions if a.action_type == "navigate"]
        login_nav_found = any(
            "myapp.com/login" in action.target for action in nav_actions
        )
        assert login_nav_found
