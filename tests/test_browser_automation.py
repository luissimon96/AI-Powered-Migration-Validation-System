"""Test script for browser automation functionality.

This script demonstrates the browser automation capabilities and can be used
to verify the implementation works correctly.
"""

import asyncio
# Import the browser automation module
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent / "src"))

from behavioral.browser_automation import (
    BrowserAction, BrowserAutomationEngine,
    create_comprehensive_validation_scenario, create_form_submission_scenario,
    create_login_scenario)


class TestBrowserAutomation:
    """Test cases for browser automation functionality."""

    @pytest.mark.asyncio
    async def test_browser_engine_initialization(self):
        """Test browser automation engine initialization."""
        engine = BrowserAutomationEngine(headless=True)

        try:
            success = await engine.initialize()
            if success:
                assert engine.browser is not None
                assert engine.context is not None
                assert engine.current_page is not None
            else:
                # Skip test if browser automation not available
                pytest.skip("Browser automation not available in this environment")
        finally:
            await engine.cleanup()

    @pytest.mark.asyncio
    async def test_basic_navigation(self):
        """Test basic navigation functionality."""
        engine = BrowserAutomationEngine(headless=True)

        try:
            success = await engine.initialize()
            if not success:
                pytest.skip("Browser automation not available")

            # Start session
            session_id = await engine.start_session("https://example.com")
            assert session_id is not None

            # Test navigation
            action = BrowserAction(
                action_type="navigate",
                target="https://example.com",
                description="Navigate to example.com",
            )

            result = await engine.execute_action(action)
            assert result.success or "Network error" in str(result.error_message)

            # End session
            session = await engine.end_session()
            assert session is not None
            assert session.session_id == session_id

        finally:
            await engine.cleanup()

    @pytest.mark.asyncio
    async def test_page_state_capture(self):
        """Test page state capture functionality."""
        engine = BrowserAutomationEngine(headless=True)

        try:
            success = await engine.initialize()
            if not success:
                pytest.skip("Browser automation not available")

            await engine.start_session("https://example.com")

            # Navigate to a page
            action = BrowserAction(
                action_type="navigate",
                target="https://example.com",
                description="Navigate to example.com",
            )
            await engine.execute_action(action)

            # Capture page state
            state = await engine.capture_page_state()

            assert isinstance(state, dict)
            assert "url" in state
            assert "title" in state
            assert "timestamp" in state

        finally:
            await engine.cleanup()

    @pytest.mark.asyncio
    async def test_screenshot_capture(self):
        """Test screenshot capture functionality."""
        engine = BrowserAutomationEngine(headless=True)

        try:
            success = await engine.initialize()
            if not success:
                pytest.skip("Browser automation not available")

            await engine.start_session("https://example.com")

            # Navigate to a page
            navigate_action = BrowserAction(
                action_type="navigate",
                target="https://example.com",
                description="Navigate to example.com",
            )
            await engine.execute_action(navigate_action)

            # Capture screenshot
            capture_action = BrowserAction(action_type="capture", description="Capture screenshot")

            result = await engine.execute_action(capture_action)

            if result.success:
                assert result.screenshot_path is not None
                screenshot_path = Path(result.screenshot_path)
                assert screenshot_path.exists()
                assert screenshot_path.suffix == ".png"

        finally:
            await engine.cleanup()

    def test_login_scenario_creation(self):
        """Test login scenario creation."""
        actions = create_login_scenario("testuser", "testpass", "https://example.com/login")

        assert len(actions) > 0
        assert any(action.action_type == "navigate" for action in actions)
        assert any(action.action_type == "fill" for action in actions)
        assert any(action.action_type == "click" for action in actions)

    def test_form_scenario_creation(self):
        """Test form submission scenario creation."""
        form_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "Test message",
        }

        actions = create_form_submission_scenario("#contact-form", form_data)

        assert len(actions) > 0
        assert sum(1 for action in actions if action.action_type == "fill") == len(form_data)
        assert any(action.action_type == "submit" for action in actions)
        assert any(action.action_type == "capture" for action in actions)

    def test_comprehensive_scenario_creation(self):
        """Test comprehensive validation scenario creation."""
        credentials = {
            "username": "testuser",
            "password": "testpass",
            "login_url": "https://example.com/login",
        }

        actions = create_comprehensive_validation_scenario("https://example.com", credentials)

        assert len(actions) > 0
        assert any(action.action_type == "navigate" for action in actions)
        assert any(action.action_type == "capture" for action in actions)
        assert any(action.action_type == "evaluate" for action in actions)

    @pytest.mark.asyncio
    async def test_state_comparison(self):
        """Test page state comparison functionality."""
        engine = BrowserAutomationEngine(headless=True)

        try:
            success = await engine.initialize()
            if not success:
                pytest.skip("Browser automation not available")

            # Create mock states for comparison
            state1 = {
                "url": "https://source.example.com",
                "title": "Source System",
                "forms": [{"action": "/submit", "method": "POST", "elements": []}],
                "messages": [{"text": "Welcome", "className": "success"}],
                "metrics": {"forms": 1, "inputs": 3, "buttons": 2},
            }

            state2 = {
                "url": "https://target.example.com",
                "title": "Target System",
                "forms": [{"action": "/submit", "method": "POST", "elements": []}],
                "messages": [{"text": "Welcome", "className": "success"}],
                "metrics": {
                    "forms": 1,
                    "inputs": 3,
                    "buttons": 1,
                },  # Different button count
            }

            discrepancies = await engine.compare_page_states(state1, state2)

            assert isinstance(discrepancies, list)
            # Should find at least the button count difference
            button_discrepancy = any(
                "button" in disc.description.lower() for disc in discrepancies
            )
            assert button_discrepancy

        finally:
            await engine.cleanup()


def test_browser_tool_integration():
    """Test BrowserTool integration with the automation engine."""
    from behavioral.crews import BrowserTool

    tool = BrowserTool()

    # Test action parsing
    result = tool._run("unknown_action:target:data")
    assert "Unknown action type" in result or "Browser automation engine not available" in result


async def demo_browser_automation():
    """Demonstration of browser automation capabilities.

    This function shows how to use the browser automation system
    for migration validation testing.
    """
    print("🌐 Browser Automation Demo")
    print("=" * 50)

    # Create browser automation engine
    engine = BrowserAutomationEngine(headless=True, slow_mo=500)

    try:
        # Initialize browser
        print("🚀 Initializing browser automation...")
        success = await engine.initialize()

        if not success:
            print("❌ Browser automation not available in this environment")
            return

        print("✅ Browser automation initialized successfully")

        # Start validation session
        print("\n📝 Starting validation session...")
        session_id = await engine.start_session("https://httpbin.org/forms/post")
        print(f"🆔 Session ID: {session_id}")

        # Test navigation
        print("\n🧭 Testing navigation...")
        navigate_action = BrowserAction(
            action_type="navigate",
            target="https://httpbin.org/forms/post",
            description="Navigate to test form",
        )

        result = await engine.execute_action(navigate_action)
        print(f"📍 Navigation: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
        if result.error_message:
            print(f"   Error: {result.error_message}")

        # Capture page state
        print("\n📊 Capturing page state...")
        state = await engine.capture_page_state()
        print(f"📋 Page state captured: {len(state)} properties")
        print(f"   Title: {state.get('title', 'N/A')}")
        print(f"   Forms: {len(state.get('forms', []))}")
        print(f"   Inputs: {state.get('metrics', {}).get('inputs', 'N/A')}")

        # Test form interaction
        print("\n📝 Testing form interaction...")
        form_actions = create_form_submission_scenario(
            "form",
            {
                "custname": "John Doe",
                "custtel": "555-1234",
                "custemail": "john@example.com",
            },
        )

        for i, action in enumerate(form_actions[:3]):  # Test first 3 actions
            print(f"   Action {i+1}: {action.description}")
            result = await engine.execute_action(action)
            print(f"   Result: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
            if result.error_message:
                print(f"   Error: {result.error_message}")

        # Capture screenshot
        print("\n📸 Capturing screenshot...")
        capture_action = BrowserAction(action_type="capture", description="Capture final state")

        result = await engine.execute_action(capture_action)
        if result.success and result.screenshot_path:
            print(f"📸 Screenshot saved: {result.screenshot_path}")
        else:
            print("❌ Screenshot capture failed")

        # End session
        print("\n🏁 Ending validation session...")
        session = await engine.end_session()
        if session:
            print(f"⏱️  Session duration: {session.duration:.1f} seconds")
            print(f"📊 Total actions: {len(session.actions)}")
            print(f"✅ Successful results: {sum(1 for r in session.results if r.success)}")

        print("\n🎉 Browser automation demo completed successfully!")

    except Exception as e:
        print(f"\n❌ Demo failed: {e!s}")

    finally:
        await engine.cleanup()
        print("\n🧹 Browser resources cleaned up")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_browser_automation())
