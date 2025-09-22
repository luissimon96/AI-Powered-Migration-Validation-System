"""
Browser automation module for AI-Powered Migration Validation System.

This module provides robust browser automation capabilities using Playwright
and browser-use for intelligent web interaction and behavioral validation.
"""

import asyncio
import json
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import structlog

try:
    from browser_use.browser import Browser as BrowserUseAgent
    from browser_use.controller import Controller
    from playwright.async_api import Browser, BrowserContext, Page, async_playwright
except ImportError:
    # Graceful fallback for environments without browser dependencies
    async_playwright = None
    Browser = None
    BrowserContext = None
    Page = None
    BrowserUseAgent = None
    Controller = None

from ..core.models import SeverityLevel, ValidationDiscrepancy

logger = structlog.get_logger(__name__)


@dataclass
class BrowserAction:
    """Represents a browser action to execute."""

    action_type: str  # navigate, click, fill, submit, wait, capture, evaluate
    target: str = ""  # CSS selector, URL, or JavaScript code
    value: str = ""  # Value to input or additional parameters
    timeout: int = 10000  # Timeout in milliseconds
    description: str = ""  # Human-readable description
    wait_for: Optional[str] = None  # Element to wait for after action


@dataclass
class BrowserActionResult:
    """Result of a browser action execution."""

    success: bool
    action: BrowserAction
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    execution_time: float = 0.0
    page_url: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class BrowserSession:
    """Represents a browser automation session."""

    session_id: str
    url: str
    actions: List[BrowserAction]
    results: List[BrowserActionResult]
    metadata: Dict[str, Any]
    start_time: datetime
    end_time: Optional[datetime] = None

    @property
    def duration(self) -> float:
        """Calculate session duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


class BrowserAutomationEngine:
    """
    Advanced browser automation engine using Playwright and browser-use.

    Provides intelligent browser control for migration validation scenarios
    including authentication, form interactions, and behavioral capture.
    """

    def __init__(self, headless: bool = True, slow_mo: int = 0, timeout: int = 30000):
        """
        Initialize browser automation engine.

        Args:
            headless: Run browser in headless mode
            slow_mo: Slow down operations by milliseconds
            timeout: Default timeout for operations
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.default_timeout = timeout
        self.playwright = None
        self.browser = None
        self.context = None
        self.current_page = None
        self.browser_use_agent = None
        self.logger = logger.bind(component="browser_automation")

        # Session management
        self.current_session: Optional[BrowserSession] = None
        self.screenshot_dir = (
            Path(tempfile.gettempdir()) / "browser_automation_screenshots"
        )
        self.screenshot_dir.mkdir(exist_ok=True)

    async def initialize(self, browser_type: str = "chromium") -> bool:
        """
        Initialize browser automation components.

        Args:
            browser_type: Browser type (chromium, firefox, webkit)

        Returns:
            True if initialization successful
        """
        if not async_playwright:
            self.logger.error("Playwright not available - browser automation disabled")
            return False

        try:
            self.playwright = await async_playwright().start()

            # Launch browser
            if browser_type == "chromium":
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    slow_mo=self.slow_mo,
                    args=[
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                    ],
                )
            elif browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(
                    headless=self.headless, slow_mo=self.slow_mo
                )
            elif browser_type == "webkit":
                self.browser = await self.playwright.webkit.launch(
                    headless=self.headless, slow_mo=self.slow_mo
                )
            else:
                raise ValueError(f"Unsupported browser type: {browser_type}")

            # Create context with additional options
            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True,
                java_script_enabled=True,
                accept_downloads=True,
                record_video_dir=None,  # Can be enabled for debugging
                record_har_path=None,  # Can be enabled for network analysis
            )

            # Set default timeouts
            self.context.set_default_timeout(self.default_timeout)
            self.context.set_default_navigation_timeout(self.default_timeout)

            # Create initial page
            self.current_page = await self.context.new_page()

            # Initialize browser-use agent if available
            if BrowserUseAgent and Controller:
                try:
                    self.browser_use_agent = BrowserUseAgent(
                        controller=Controller(),
                        config={"headless": self.headless, "slow_mo": self.slow_mo},
                    )
                    self.logger.info("Browser-use agent initialized successfully")
                except Exception as e:
                    self.logger.warning(
                        "Failed to initialize browser-use agent", error=str(e)
                    )
                    self.browser_use_agent = None

            self.logger.info(
                "Browser automation engine initialized successfully",
                browser_type=browser_type,
                headless=self.headless,
            )
            return True

        except Exception as e:
            self.logger.error("Failed to initialize browser automation", error=str(e))
            await self.cleanup()
            return False

    async def start_session(
        self, url: str, session_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new browser automation session.

        Args:
            url: Starting URL for the session
            session_metadata: Additional metadata for the session

        Returns:
            Session ID
        """
        session_id = f"session_{int(time.time())}_{id(self)}"

        self.current_session = BrowserSession(
            session_id=session_id,
            url=url,
            actions=[],
            results=[],
            metadata=session_metadata or {},
            start_time=datetime.now(),
        )

        self.logger.info("Started browser session", session_id=session_id, url=url)
        return session_id

    async def end_session(self) -> Optional[BrowserSession]:
        """
        End the current browser automation session.

        Returns:
            Completed session data
        """
        if not self.current_session:
            return None

        self.current_session.end_time = datetime.now()
        session = self.current_session
        self.current_session = None

        self.logger.info(
            "Ended browser session",
            session_id=session.session_id,
            duration=session.duration,
            actions_count=len(session.actions),
        )
        return session

    async def execute_action(self, action: BrowserAction) -> BrowserActionResult:
        """
        Execute a single browser action.

        Args:
            action: Browser action to execute

        Returns:
            Action execution result
        """
        start_time = time.time()
        result = BrowserActionResult(success=False, action=action, execution_time=0.0)

        if not self.current_page:
            result.error_message = "No active browser page"
            return result

        try:
            self.logger.info(
                "Executing browser action",
                action_type=action.action_type,
                target=action.target,
                description=action.description,
            )

            # Record action in session
            if self.current_session:
                self.current_session.actions.append(action)

            # Execute action based on type
            if action.action_type == "navigate":
                await self._execute_navigate(action, result)
            elif action.action_type == "click":
                await self._execute_click(action, result)
            elif action.action_type == "fill":
                await self._execute_fill(action, result)
            elif action.action_type == "submit":
                await self._execute_submit(action, result)
            elif action.action_type == "wait":
                await self._execute_wait(action, result)
            elif action.action_type == "capture":
                await self._execute_capture(action, result)
            elif action.action_type == "evaluate":
                await self._execute_evaluate(action, result)
            elif action.action_type == "intelligent":
                await self._execute_intelligent(action, result)
            else:
                result.error_message = f"Unknown action type: {action.action_type}"
                return result

            # Wait for specified element after action
            if action.wait_for and result.success:
                try:
                    await self.current_page.wait_for_selector(
                        action.wait_for, timeout=action.timeout
                    )
                except Exception as e:
                    self.logger.warning(
                        "Wait for element failed", element=action.wait_for, error=str(e)
                    )

            result.page_url = self.current_page.url
            result.success = True

        except Exception as e:
            result.error_message = str(e)
            self.logger.error(
                "Browser action failed", action_type=action.action_type, error=str(e)
            )

        finally:
            result.execution_time = time.time() - start_time

            # Record result in session
            if self.current_session:
                self.current_session.results.append(result)

        return result

    async def _execute_navigate(
        self, action: BrowserAction, result: BrowserActionResult
    ):
        """Execute navigation action."""
        response = await self.current_page.goto(action.target, timeout=action.timeout)
        result.result_data = {
            "status": response.status if response else None,
            "url": self.current_page.url,
        }

    async def _execute_click(self, action: BrowserAction, result: BrowserActionResult):
        """Execute click action."""
        element = await self.current_page.wait_for_selector(
            action.target, timeout=action.timeout
        )
        await element.click()
        result.result_data = {"clicked_element": action.target}

    async def _execute_fill(self, action: BrowserAction, result: BrowserActionResult):
        """Execute fill action."""
        await self.current_page.fill(action.target, action.value)
        result.result_data = {
            "filled_element": action.target,
            "value_length": len(action.value),
        }

    async def _execute_submit(self, action: BrowserAction, result: BrowserActionResult):
        """Execute form submission."""
        if action.target:
            # Submit specific form
            form = await self.current_page.wait_for_selector(
                action.target, timeout=action.timeout
            )
            await form.submit()
        else:
            # Submit by pressing Enter on the page
            await self.current_page.keyboard.press("Enter")

        result.result_data = {"submitted_form": action.target or "default"}

    async def _execute_wait(self, action: BrowserAction, result: BrowserActionResult):
        """Execute wait action."""
        if action.target:
            # Wait for specific selector
            await self.current_page.wait_for_selector(
                action.target, timeout=action.timeout
            )
            result.result_data = {"waited_for": action.target}
        else:
            # Wait for specified time
            wait_time = int(action.value) if action.value.isdigit() else 1000
            await asyncio.sleep(wait_time / 1000)
            result.result_data = {"waited_ms": wait_time}

    async def _execute_capture(
        self, action: BrowserAction, result: BrowserActionResult
    ):
        """Execute screenshot capture."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_name = f"capture_{timestamp}.png"
        screenshot_path = self.screenshot_dir / screenshot_name

        if action.target:
            # Capture specific element
            element = await self.current_page.wait_for_selector(
                action.target, timeout=action.timeout
            )
            await element.screenshot(path=str(screenshot_path))
        else:
            # Capture full page
            await self.current_page.screenshot(
                path=str(screenshot_path), full_page=True
            )

        result.screenshot_path = str(screenshot_path)
        result.result_data = {
            "screenshot_path": str(screenshot_path),
            "element": action.target or "full_page",
        }

    async def _execute_evaluate(
        self, action: BrowserAction, result: BrowserActionResult
    ):
        """Execute JavaScript evaluation."""
        eval_result = await self.current_page.evaluate(action.target)
        result.result_data = {"javascript": action.target, "result": eval_result}

    async def _execute_intelligent(
        self, action: BrowserAction, result: BrowserActionResult
    ):
        """Execute intelligent action using browser-use."""
        if not self.browser_use_agent:
            raise Exception("Browser-use agent not available")

        try:
            # Use browser-use for intelligent interaction
            intelligent_result = await self.browser_use_agent.execute_task(
                action.description or action.target, page=self.current_page
            )

            result.result_data = {
                "task": action.description or action.target,
                "intelligent_result": intelligent_result,
            }

        except Exception as e:
            # Fallback to basic interaction if browser-use fails
            self.logger.warning(
                "Intelligent action failed, falling back to basic interaction",
                error=str(e),
            )
            await self._execute_click(action, result)

    async def execute_scenario(
        self, scenario_name: str, actions: List[BrowserAction]
    ) -> List[BrowserActionResult]:
        """
        Execute a complete behavioral scenario.

        Args:
            scenario_name: Name of the scenario
            actions: List of actions to execute

        Returns:
            List of action results
        """
        self.logger.info(
            "Executing behavioral scenario",
            scenario=scenario_name,
            actions_count=len(actions),
        )

        results = []

        for i, action in enumerate(actions):
            self.logger.debug(
                "Executing action",
                scenario=scenario_name,
                action_index=i,
                action_type=action.action_type,
            )

            result = await self.execute_action(action)
            results.append(result)

            # Stop execution if critical action fails
            if not result.success and action.action_type in ["navigate", "intelligent"]:
                self.logger.error(
                    "Critical action failed, stopping scenario",
                    scenario=scenario_name,
                    failed_action=action.action_type,
                )
                break

            # Small delay between actions for stability
            await asyncio.sleep(0.5)

        success_count = sum(1 for r in results if r.success)
        self.logger.info(
            "Scenario execution completed",
            scenario=scenario_name,
            total_actions=len(actions),
            successful_actions=success_count,
        )

        return results

    async def authenticate(
        self,
        username: str,
        password: str,
        login_url: Optional[str] = None,
        username_selector: str = 'input[name="username"], input[name="email"], input[type="email"]',
        password_selector: str = 'input[name="password"], input[type="password"]',
        submit_selector: str = 'button[type="submit"], input[type="submit"]',
    ) -> bool:
        """
        Perform authentication on the current page.

        Args:
            username: Username or email
            password: Password
            login_url: Optional URL to navigate to for login
            username_selector: CSS selector for username field
            password_selector: CSS selector for password field
            submit_selector: CSS selector for submit button

        Returns:
            True if authentication appears successful
        """
        try:
            # Navigate to login page if specified
            if login_url:
                await self.current_page.goto(login_url)

            # Fill username
            await self.current_page.fill(username_selector, username)
            await asyncio.sleep(0.5)

            # Fill password
            await self.current_page.fill(password_selector, password)
            await asyncio.sleep(0.5)

            # Submit form
            await self.current_page.click(submit_selector)

            # Wait for navigation or response
            try:
                await self.current_page.wait_for_load_state(
                    "networkidle", timeout=10000
                )
            except:
                pass  # Continue even if network idle timeout

            # Check for common success indicators
            current_url = self.current_page.url
            page_content = await self.current_page.content()

            # Simple heuristics for authentication success
            success_indicators = [
                "dashboard" in current_url.lower(),
                "home" in current_url.lower(),
                "welcome" in page_content.lower(),
                "logout" in page_content.lower(),
                "profile" in page_content.lower(),
            ]

            # Check for error indicators
            error_indicators = [
                "error" in page_content.lower(),
                "invalid" in page_content.lower(),
                "incorrect" in page_content.lower(),
                "failed" in page_content.lower(),
            ]

            has_success = any(success_indicators)
            has_errors = any(error_indicators)

            # Return true if we have success indicators and no error indicators
            authentication_success = has_success and not has_errors

            self.logger.info(
                "Authentication attempt completed",
                success=authentication_success,
                current_url=current_url,
            )

            return authentication_success

        except Exception as e:
            self.logger.error("Authentication failed", error=str(e))
            return False

    async def capture_page_state(self) -> Dict[str, Any]:
        """
        Capture comprehensive page state for comparison.

        Returns:
            Dictionary containing page state information
        """
        if not self.current_page:
            return {}

        try:
            # Capture basic page information
            state = {
                "url": self.current_page.url,
                "title": await self.current_page.title(),
                "timestamp": datetime.now().isoformat(),
            }

            # Capture form elements
            forms = await self.current_page.evaluate(
                """
                () => {
                    const forms = Array.from(document.forms);
                    return forms.map(form => ({
                        action: form.action,
                        method: form.method,
                        elements: Array.from(form.elements).map(el => ({
                            type: el.type,
                            name: el.name,
                            value: el.value,
                            required: el.required,
                            placeholder: el.placeholder
                        }))
                    }));
                }
            """
            )
            state["forms"] = forms

            # Capture visible text
            text_content = await self.current_page.evaluate(
                """
                () => document.body.innerText
            """
            )
            state["text_content"] = text_content[:1000]  # Limit size

            # Capture error/success messages
            messages = await self.current_page.evaluate(
                """
                () => {
                    const selectors = [
                        '.error', '.success', '.warning', '.info',
                        '[class*="error"]', '[class*="success"]',
                        '[role="alert"]', '.alert'
                    ];
                    const messages = [];
                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            if (el.textContent.trim()) {
                                messages.push({
                                    selector: selector,
                                    text: el.textContent.trim(),
                                    className: el.className
                                });
                            }
                        });
                    });
                    return messages;
                }
            """
            )
            state["messages"] = messages

            # Capture page metrics
            metrics = await self.current_page.evaluate(
                """
                () => ({
                    loadTime: performance.timing.loadEventEnd - performance.timing.navigationStart,
                    domContentLoaded: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart,
                    forms: document.forms.length,
                    inputs: document.querySelectorAll('input').length,
                    buttons: document.querySelectorAll('button').length,
                    links: document.querySelectorAll('a').length
                })
            """
            )
            state["metrics"] = metrics

            return state

        except Exception as e:
            self.logger.error("Failed to capture page state", error=str(e))
            return {"error": str(e)}

    async def compare_page_states(
        self, state1: Dict[str, Any], state2: Dict[str, Any]
    ) -> List[ValidationDiscrepancy]:
        """
        Compare two page states and identify discrepancies.

        Args:
            state1: First page state (source system)
            state2: Second page state (target system)

        Returns:
            List of validation discrepancies
        """
        discrepancies = []

        try:
            # Compare URLs (structural differences)
            if state1.get("url") != state2.get("url"):
                # This is expected for different systems, log but don't flag as error
                pass

            # Compare page titles
            title1 = state1.get("title", "")
            title2 = state2.get("title", "")
            if title1 != title2:
                discrepancies.append(
                    ValidationDiscrepancy(
                        type="title_mismatch",
                        severity=SeverityLevel.INFO,
                        description=f"Page titles differ: '{title1}' vs '{title2}'",
                        source_element=title1,
                        target_element=title2,
                        recommendation="Review if title differences are intentional",
                    )
                )

            # Compare form structures
            forms1 = state1.get("forms", [])
            forms2 = state2.get("forms", [])

            if len(forms1) != len(forms2):
                discrepancies.append(
                    ValidationDiscrepancy(
                        type="form_count_mismatch",
                        severity=SeverityLevel.WARNING,
                        description=f"Different number of forms: {len(forms1)} vs {len(forms2)}",
                        recommendation="Verify all forms were migrated correctly",
                    )
                )

            # Compare form elements (simplified)
            for i, (form1, form2) in enumerate(zip(forms1, forms2)):
                elements1 = form1.get("elements", [])
                elements2 = form2.get("elements", [])

                if len(elements1) != len(elements2):
                    discrepancies.append(
                        ValidationDiscrepancy(
                            type="form_elements_mismatch",
                            severity=SeverityLevel.WARNING,
                            description=f"Form {i} has different element count: {len(elements1)} vs {len(elements2)}",
                            recommendation="Check form field migration",
                        )
                    )

            # Compare messages (errors, success, warnings)
            messages1 = state1.get("messages", [])
            messages2 = state2.get("messages", [])

            # Extract message texts for comparison
            texts1 = {msg["text"] for msg in messages1}
            texts2 = {msg["text"] for msg in messages2}

            only_in_source = texts1 - texts2
            only_in_target = texts2 - texts1

            for msg in only_in_source:
                discrepancies.append(
                    ValidationDiscrepancy(
                        type="missing_message",
                        severity=SeverityLevel.WARNING,
                        description=f"Message only in source: '{msg}'",
                        source_element=msg,
                        recommendation="Check if message logic was migrated",
                    )
                )

            for msg in only_in_target:
                discrepancies.append(
                    ValidationDiscrepancy(
                        type="additional_message",
                        severity=SeverityLevel.INFO,
                        description=f"Additional message in target: '{msg}'",
                        target_element=msg,
                        recommendation="Verify if additional message is intentional",
                    )
                )

            # Compare page metrics
            metrics1 = state1.get("metrics", {})
            metrics2 = state2.get("metrics", {})

            for metric in ["forms", "inputs", "buttons", "links"]:
                val1 = metrics1.get(metric, 0)
                val2 = metrics2.get(metric, 0)

                if val1 != val2:
                    severity = (
                        SeverityLevel.WARNING
                        if metric in ["forms", "inputs"]
                        else SeverityLevel.INFO
                    )
                    discrepancies.append(
                        ValidationDiscrepancy(
                            type=f"{metric}_count_difference",
                            severity=severity,
                            description=f"Different {metric} count: {val1} vs {val2}",
                            recommendation=f"Review {metric} migration",
                        )
                    )

        except Exception as e:
            self.logger.error("Failed to compare page states", error=str(e))
            discrepancies.append(
                ValidationDiscrepancy(
                    type="comparison_error",
                    severity=SeverityLevel.CRITICAL,
                    description=f"Failed to compare page states: {str(e)}",
                    recommendation="Manual verification required",
                )
            )

        return discrepancies

    async def cleanup(self):
        """Clean up browser automation resources."""
        try:
            if self.current_page:
                await self.current_page.close()
                self.current_page = None

            if self.context:
                await self.context.close()
                self.context = None

            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            self.logger.info("Browser automation resources cleaned up")

        except Exception as e:
            self.logger.error("Error during cleanup", error=str(e))

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()


def create_login_scenario(
    username: str, password: str, login_url: str
) -> List[BrowserAction]:
    """
    Create a standard login scenario.

    Args:
        username: Username or email
        password: Password
        login_url: Login page URL

    Returns:
        List of browser actions for login scenario
    """
    return [
        BrowserAction(
            action_type="navigate",
            target=login_url,
            description="Navigate to login page",
        ),
        BrowserAction(
            action_type="fill",
            target='input[name="username"], input[name="email"], input[type="email"]',
            value=username,
            description="Fill username field",
        ),
        BrowserAction(
            action_type="fill",
            target='input[name="password"], input[type="password"]',
            value=password,
            description="Fill password field",
        ),
        BrowserAction(
            action_type="click",
            target='button[type="submit"], input[type="submit"]',
            description="Click login button",
            wait_for="body",  # Wait for page to load after login
        ),
        BrowserAction(
            action_type="wait", value="2000", description="Wait for login to complete"
        ),
        BrowserAction(action_type="capture", description="Capture post-login state"),
    ]


def create_form_submission_scenario(
    form_selector: str, form_data: Dict[str, str]
) -> List[BrowserAction]:
    """
    Create a form submission scenario.

    Args:
        form_selector: CSS selector for the form
        form_data: Dictionary of field names to values

    Returns:
        List of browser actions for form submission
    """
    actions = []

    # Fill each form field
    for field_name, field_value in form_data.items():
        actions.append(
            BrowserAction(
                action_type="fill",
                target=f'{form_selector} input[name="{field_name}"], {form_selector} textarea[name="{field_name}"], {form_selector} select[name="{field_name}"]',
                value=field_value,
                description=f"Fill {field_name} field",
            )
        )

    # Submit form
    actions.append(
        BrowserAction(
            action_type="submit",
            target=form_selector,
            description="Submit form",
            wait_for="body",
        )
    )

    # Capture result
    actions.append(
        BrowserAction(
            action_type="capture", description="Capture form submission result"
        )
    )

    return actions


def create_comprehensive_validation_scenario(
    url: str, credentials: Optional[Dict[str, str]] = None
) -> List[BrowserAction]:
    """
    Create a comprehensive validation scenario for a web application.

    Args:
        url: Base URL of the application
        credentials: Optional login credentials

    Returns:
        List of browser actions for comprehensive testing
    """
    actions = []

    # Initial page load and capture
    actions.extend(
        [
            BrowserAction(
                action_type="navigate",
                target=url,
                description="Navigate to application homepage",
            ),
            BrowserAction(action_type="capture", description="Capture homepage state"),
            BrowserAction(
                action_type="wait",
                value="2000",
                description="Wait for page to fully load",
            ),
        ]
    )

    # Authentication if credentials provided
    if credentials and "username" in credentials and "password" in credentials:
        login_url = credentials.get("login_url", url + "/login")
        actions.extend(
            create_login_scenario(
                credentials["username"], credentials["password"], login_url
            )
        )

    # Common navigation and interaction tests
    actions.extend(
        [
            # Test common form interactions
            BrowserAction(
                action_type="evaluate",
                target="document.querySelectorAll('form').length",
                description="Count forms on page",
            ),
            BrowserAction(
                action_type="evaluate",
                target="document.querySelectorAll('input').length",
                description="Count input elements",
            ),
            BrowserAction(
                action_type="evaluate",
                target="document.querySelectorAll('button').length",
                description="Count buttons",
            ),
            # Test error handling (submit empty forms)
            BrowserAction(
                action_type="evaluate",
                target="""
            (() => {
                const forms = document.querySelectorAll('form');
                if (forms.length > 0) {
                    const submitBtn = forms[0].querySelector('button[type="submit"], input[type="submit"]');
                    if (submitBtn) {
                        submitBtn.click();
                        return 'Triggered form submission';
                    }
                }
                return 'No submittable forms found';
            })()
            """,
                description="Test form submission without data",
            ),
            BrowserAction(
                action_type="wait", value="2000", description="Wait for error response"
            ),
            BrowserAction(action_type="capture", description="Capture error state"),
        ]
    )

    return actions


async def execute_migration_validation_workflow(
    source_url: str,
    target_url: str,
    scenarios: List[str],
    credentials: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Execute complete migration validation workflow using browser automation.

    Args:
        source_url: Source system URL
        target_url: Target system URL
        scenarios: List of validation scenarios
        credentials: Optional authentication credentials

    Returns:
        Comprehensive validation results
    """
    logger = structlog.get_logger("migration_validation_workflow")
    results = {
        "source_results": {},
        "target_results": {},
        "comparison": {},
        "discrepancies": [],
        "overall_score": 0.0,
    }

    try:
        # Test source system
        logger.info("Starting source system validation", url=source_url)
        async with BrowserAutomationEngine() as source_engine:
            await source_engine.start_session(source_url, {"system": "source"})

            # Execute comprehensive scenario
            source_actions = create_comprehensive_validation_scenario(
                source_url, credentials
            )
            source_results = await source_engine.execute_scenario(
                "comprehensive_validation", source_actions
            )

            # Capture final state
            source_state = await source_engine.capture_page_state()
            results["source_results"] = {
                "actions": [asdict(action) for action in source_actions],
                "results": [asdict(result) for result in source_results],
                "final_state": source_state,
                "session": asdict(await source_engine.end_session()),
            }

        # Test target system
        logger.info("Starting target system validation", url=target_url)
        async with BrowserAutomationEngine() as target_engine:
            await target_engine.start_session(target_url, {"system": "target"})

            # Execute same scenario
            target_actions = create_comprehensive_validation_scenario(
                target_url, credentials
            )
            target_results = await target_engine.execute_scenario(
                "comprehensive_validation", target_actions
            )

            # Capture final state
            target_state = await target_engine.capture_page_state()
            results["target_results"] = {
                "actions": [asdict(action) for action in target_actions],
                "results": [asdict(result) for result in target_results],
                "final_state": target_state,
                "session": asdict(await target_engine.end_session()),
            }

            # Compare states
            discrepancies = await target_engine.compare_page_states(
                source_state, target_state
            )
            results["discrepancies"] = [asdict(disc) for disc in discrepancies]

        # Calculate overall score
        total_actions = len(source_results)
        successful_source = sum(1 for r in source_results if r.success)
        successful_target = sum(1 for r in target_results if r.success)

        functional_score = (
            min(successful_source, successful_target) / total_actions
            if total_actions > 0
            else 0
        )
        discrepancy_penalty = (
            len([d for d in discrepancies if d.severity.value == "critical"]) * 0.2
        )
        results["overall_score"] = max(0, functional_score - discrepancy_penalty)

        results["comparison"] = {
            "functional_score": functional_score,
            "source_success_rate": (
                successful_source / total_actions if total_actions > 0 else 0
            ),
            "target_success_rate": (
                successful_target / total_actions if total_actions > 0 else 0
            ),
            "critical_discrepancies": len(
                [d for d in discrepancies if d.severity.value == "critical"]
            ),
            "total_discrepancies": len(discrepancies),
        }

        logger.info(
            "Migration validation completed",
            overall_score=results["overall_score"],
            discrepancies=len(discrepancies),
        )

    except Exception as e:
        logger.error("Migration validation failed", error=str(e))
        results["error"] = str(e)

    return results
