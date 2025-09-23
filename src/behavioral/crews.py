"""
CrewAI-based behavioral validation crews for migration testing.

This module implements the multi-agent behavioral validation system that
distinguishes this platform from other migration tools. It uses CrewAI to
orchestrate specialized agents that test real system behavior.
"""

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from crewai import Agent, Crew, Process, Task

# BaseTool not available in this version, will create custom tool base
# from crewai_tools import BaseTool
from pydantic import BaseModel, Field

from ..core.models import (
    AbstractRepresentation,
    SeverityLevel,
    ValidationDiscrepancy,
    ValidationScope,
)
from ..services.llm_service import LLMService

logger = structlog.get_logger(__name__)


@dataclass
class BehavioralValidationRequest:
    """Request for behavioral validation."""

    source_url: str
    target_url: str
    validation_scenarios: List[str]
    credentials: Optional[Dict[str, str]] = None
    timeout: int = 300
    metadata: Dict[str, Any] = None


@dataclass
class BehavioralValidationResult:
    """Result of behavioral validation."""

    overall_status: str
    fidelity_score: float
    discrepancies: List[ValidationDiscrepancy]
    execution_log: List[str]
    execution_time: float
    timestamp: datetime


class BrowserTool(BaseModel):
    """Advanced browser automation tool using Playwright and browser-use."""

    name: str = "browser_tool"
    description: str = """Advanced browser automation for comprehensive web application testing.

    Supports actions:
    - navigate: Go to URL
    - click: Click element by selector
    - fill: Fill form field
    - submit: Submit form
    - wait: Wait for element or time
    - capture: Take screenshot
    - evaluate: Run JavaScript
    - intelligent: Use AI-powered interaction
    - authenticate: Login with credentials
    - capture_state: Capture page state for comparison
    - scenario: Execute pre-defined scenario

    Example usage:
    - navigate:https://example.com
    - click:button#submit
    - fill:input[name="username"]:john@example.com
    - authenticate:username:password:login_url
    - scenario:login:username:password
    """

    def __init__(self):
        super().__init__()
        self.automation_engine = None
        self.logger = structlog.get_logger("browser_tool")
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure browser automation engine is initialized."""
        if not self._initialized:
            from .browser_automation import BrowserAutomationEngine

            self.automation_engine = BrowserAutomationEngine(
                headless=True,  # Run headless for production
                slow_mo=100,  # Small delay for stability
                timeout=30000,  # 30 second timeout
            )
            success = await self.automation_engine.initialize()
            if not success:
                raise Exception("Failed to initialize browser automation engine")
            self._initialized = True
            self.logger.info("Browser automation engine initialized")

    def _run(self, action: str, target: str = "", data: str = "") -> str:
        """Execute browser action synchronously."""
        try:
            # Create event loop if none exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run async method
            return loop.run_until_complete(self._run_async(action, target, data))

        except Exception as e:
            error_msg = f"Browser action failed: {str(e)}"
            self.logger.error("Browser tool execution failed", action=action, error=str(e))
            return error_msg

    async def _run_async(self, action: str, target: str = "", data: str = "") -> str:
        """Execute browser action asynchronously."""
        await self._ensure_initialized()

        if not self.automation_engine:
            return "Browser automation engine not available"

        # Parse action string (format: action:target:data or action:target)
        action_parts = action.split(":", 2)
        action_type = action_parts[0].lower()
        action_target = action_parts[1] if len(action_parts) > 1 else target
        action_data = action_parts[2] if len(action_parts) > 2 else data

        try:
            from .browser_automation import (
                BrowserAction,
                create_form_submission_scenario,
                create_login_scenario,
            )

            if action_type == "navigate":
                browser_action = BrowserAction(
                    action_type="navigate",
                    target=action_target,
                    description=f"Navigate to {action_target}",
                )
                result = await self.automation_engine.execute_action(browser_action)

            elif action_type == "click":
                browser_action = BrowserAction(
                    action_type="click",
                    target=action_target,
                    description=f"Click element {action_target}",
                )
                result = await self.automation_engine.execute_action(browser_action)

            elif action_type == "fill":
                browser_action = BrowserAction(
                    action_type="fill",
                    target=action_target,
                    value=action_data,
                    description=f"Fill {action_target} with data",
                )
                result = await self.automation_engine.execute_action(browser_action)

            elif action_type == "submit":
                browser_action = BrowserAction(
                    action_type="submit",
                    target=action_target,
                    description=f"Submit form {action_target}",
                )
                result = await self.automation_engine.execute_action(browser_action)

            elif action_type == "wait":
                browser_action = BrowserAction(
                    action_type="wait",
                    target=action_target,
                    value=action_data,
                    description="Wait for element or time",
                )
                result = await self.automation_engine.execute_action(browser_action)

            elif action_type == "capture":
                browser_action = BrowserAction(
                    action_type="capture",
                    target=action_target,
                    description="Capture screenshot",
                )
                result = await self.automation_engine.execute_action(browser_action)

            elif action_type == "evaluate":
                browser_action = BrowserAction(
                    action_type="evaluate",
                    target=action_target,
                    description="Execute JavaScript",
                )
                result = await self.automation_engine.execute_action(browser_action)

            elif action_type == "intelligent":
                browser_action = BrowserAction(
                    action_type="intelligent",
                    target=action_target,
                    description=action_data or "Intelligent browser interaction",
                )
                result = await self.automation_engine.execute_action(browser_action)

            elif action_type == "authenticate":
                # Format: authenticate:username:password:login_url
                parts = [action_target, action_data] + (data.split(":") if data else [])
                if len(parts) >= 3:
                    username, password, login_url = parts[0], parts[1], parts[2]
                    success = await self.automation_engine.authenticate(
                        username=username, password=password, login_url=login_url
                    )
                    return f"Authentication {'successful' if success else 'failed'}"
                else:
                    return "Authentication requires username:password:login_url format"

            elif action_type == "capture_state":
                state = await self.automation_engine.capture_page_state()
                return json.dumps(state, indent=2)

            elif action_type == "scenario":
                # Format: scenario:login:username:password or scenario:form:form_selector:field1=value1,field2=value2
                scenario_type = action_target

                if scenario_type == "login" and action_data:
                    parts = action_data.split(":")
                    if len(parts) >= 3:
                        username, password, login_url = parts[0], parts[1], parts[2]
                        actions = create_login_scenario(username, password, login_url)
                        results = await self.automation_engine.execute_scenario("login", actions)
                        success_count = sum(1 for r in results if r.success)
                        return f"Login scenario executed: {success_count}/{len(results)} actions successful"
                    else:
                        return "Login scenario requires username:password:login_url"

                elif scenario_type == "form" and action_data:
                    parts = action_data.split(":")
                    if len(parts) >= 2:
                        form_selector = parts[0]
                        form_data_str = parts[1]

                        # Parse form data (field1=value1,field2=value2)
                        form_data = {}
                        for pair in form_data_str.split(","):
                            if "=" in pair:
                                key, value = pair.split("=", 1)
                                form_data[key.strip()] = value.strip()

                        actions = create_form_submission_scenario(form_selector, form_data)
                        results = await self.automation_engine.execute_scenario(
                            "form_submission", actions
                        )
                        success_count = sum(1 for r in results if r.success)
                        return f"Form scenario executed: {success_count}/{len(results)} actions successful"
                    else:
                        return "Form scenario requires form_selector:field1=value1,field2=value2"
                else:
                    return f"Unknown scenario type: {scenario_type}"

            elif action_type == "session":
                # Session management
                if action_target == "start":
                    session_id = await self.automation_engine.start_session(
                        action_data or "about:blank"
                    )
                    return f"Started session: {session_id}"
                elif action_target == "end":
                    session = await self.automation_engine.end_session()
                    if session:
                        return f"Ended session {session.session_id}, duration: {session.duration:.1f}s"
                    else:
                        return "No active session to end"
                else:
                    return "Session action requires 'start' or 'end'"

            else:
                return f"Unknown action type: {action_type}"

            # Format result
            if hasattr(result, "success"):
                status = "SUCCESS" if result.success else "FAILED"
                details = ""

                if result.result_data:
                    details = f" - {json.dumps(result.result_data)}"

                if result.error_message:
                    details += f" - Error: {result.error_message}"

                if result.screenshot_path:
                    details += f" - Screenshot: {result.screenshot_path}"

                return f"{action_type.upper()} {status}{details}"
            else:
                return str(result)

        except Exception as e:
            error_msg = f"Action execution failed: {str(e)}"
            self.logger.error(
                "Browser action execution failed", action_type=action_type, error=str(e)
            )
            return error_msg

    async def cleanup(self):
        """Clean up browser resources."""
        if self.automation_engine:
            await self.automation_engine.cleanup()
            self.automation_engine = None
            self._initialized = False

    def __del__(self):
        """Cleanup on destruction."""
        if self._initialized and self.automation_engine:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule cleanup for later if loop is running
                    loop.create_task(self.cleanup())
                else:
                    loop.run_until_complete(self.cleanup())
            except Exception as e:
                logger.debug(
                    f"Cleanup error during destruction: {e}"
                )  # Ignore cleanup errors during destruction


class ValidationScenarioResult(BaseModel):
    """Result of a single validation scenario."""

    scenario_name: str = Field(description="Name of the validation scenario")
    source_behavior: str = Field(description="Observed behavior in source system")
    target_behavior: str = Field(description="Observed behavior in target system")
    match_status: str = Field(
        description="Whether behaviors match: identical, similar, different, error"
    )
    discrepancies: List[str] = Field(description="List of identified discrepancies")
    confidence: float = Field(description="Confidence score for the comparison")


class SourceExplorerAgent:
    """Agent that explores and documents source system behavior."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.browser_tool = BrowserTool()

        self.agent = Agent(
            role="Source System Explorer",
            goal="Thoroughly explore and document the behavior of the source system",
            backstory="""You are an expert QA tester with years of experience in exploring 
            web applications. You have a keen eye for detail and can systematically test 
            user flows, edge cases, and error conditions. Your goal is to create a 
            comprehensive behavioral baseline of the source system.""",
            verbose=True,
            tools=[self.browser_tool],
            llm=self._get_llm_config(),
        )

    def _get_llm_config(self) -> str:
        """Get LLM configuration string for CrewAI."""
        if self.llm_service:
            provider_info = self.llm_service.get_provider_info()
            return f"{provider_info['provider']}/{provider_info['model']}"
        return "openai/gpt-4-turbo-preview"  # fallback

    def create_exploration_task(self, source_url: str, scenarios: List[str]) -> Task:
        """Create task for exploring source system."""
        scenario_list = "\n".join([f"- {scenario}" for scenario in scenarios])

        return Task(
            description=f"""
            Explore the source system at {source_url} and document its behavior using the browser_tool.

            Test these validation scenarios:
            {scenario_list}

            Use the browser_tool to systematically test each scenario:

            1. START SESSION: Use browser_tool with "session:start:{source_url}"
            2. NAVIGATE: Use "navigate:{source_url}" to go to the main page
            3. CAPTURE INITIAL STATE: Use "capture_state" to document page structure

            For each scenario:
            4. NAVIGATE to relevant sections using "navigate:url"
            5. INTERACT with elements using "click:selector", "fill:selector:value", "submit:form_selector"
            6. CAPTURE screenshots using "capture" for visual documentation
            7. CAPTURE page state using "capture_state" after each interaction
            8. TEST ERROR CASES by entering invalid data and documenting responses
            9. WAIT for elements to load using "wait:selector" or "wait::milliseconds"

            For authentication scenarios:
            - Use "authenticate:username:password:login_url" for login testing
            - Or use "scenario:login:username:password:login_url" for complete login flow

            For form scenarios:
            - Use "scenario:form:form_selector:field1=value1,field2=value2" for form testing

            6. END SESSION: Use "session:end" to complete documentation

            Document each browser_tool response and create a comprehensive behavioral log.
            """,
            expected_output="""A comprehensive behavioral log in JSON format containing:
            - Session metadata and timing
            - Detailed step-by-step browser interactions
            - Page states captured at each critical point
            - Screenshot paths for visual verification
            - Error messages and validation behaviors observed
            - Performance metrics and response times
            - Success/failure status for each scenario tested""",
            agent=self.agent,
        )


class TargetExecutorAgent:
    """Agent that replicates actions on target system."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.browser_tool = BrowserTool()

        self.agent = Agent(
            role="Target System Executor",
            goal="Execute the same scenarios on the target system and document results",
            backstory="""You are a meticulous test executor who follows detailed test 
            scripts precisely. You excel at replicating exact user interactions and 
            documenting any differences in system behavior. Your attention to detail 
            ensures that no behavioral differences go unnoticed.""",
            verbose=True,
            tools=[self.browser_tool],
            llm=self._get_llm_config(),
        )

    def _get_llm_config(self) -> str:
        """Get LLM configuration string for CrewAI."""
        if self.llm_service:
            provider_info = self.llm_service.get_provider_info()
            return f"{provider_info['provider']}/{provider_info['model']}"
        return "openai/gpt-4-turbo-preview"

    def create_execution_task(self, target_url: str, source_log: str) -> Task:
        """Create task for executing scenarios on target system."""
        return Task(
            description=f"""
            Using the source system behavioral log as a guide, execute the identical
            scenarios on the target system at {target_url} using the browser_tool.

            Source System Log:
            {source_log}

            Replicate the exact testing approach from the source system:

            1. START SESSION: Use browser_tool with "session:start:{target_url}"
            2. NAVIGATE: Use "navigate:{target_url}" to access the target system
            3. CAPTURE INITIAL STATE: Use "capture_state" to document target page structure

            For each scenario documented in the source log:
            4. REPLICATE the same navigation pattern using "navigate:url"
            5. PERFORM identical interactions using "click:selector", "fill:selector:value", "submit:form_selector"
            6. USE THE SAME selectors and input values when possible
            7. CAPTURE screenshots using "capture" at the same interaction points
            8. CAPTURE page state using "capture_state" after each critical interaction
            9. TEST identical error cases with the same invalid inputs
            10. MEASURE timing using "wait" commands for performance comparison

            For authentication scenarios:
            - Use "authenticate:username:password:login_url" with same credentials as source
            - Or use "scenario:login:username:password:login_url" for login replication

            For form scenarios:
            - Use "scenario:form:form_selector:field1=value1,field2=value2" with identical data

            11. END SESSION: Use "session:end" to complete parallel documentation

            Document all browser_tool responses and create a behavioral log that exactly
            mirrors the source system structure for precise comparison.
            """,
            expected_output="""A parallel behavioral log in JSON format that exactly matches
            the source system log structure, containing:
            - Identical session timing and interaction patterns
            - Same screenshot capture points for visual comparison
            - Parallel page state documentation for structural analysis
            - Identical error case testing results
            - Performance metrics for timing comparison
            - Direct mapping to source system behaviors for validation""",
            agent=self.agent,
        )


class ComparisonJudgeAgent:
    """Agent that compares source and target behaviors."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

        self.agent = Agent(
            role="Behavioral Comparison Judge",
            goal="Analyze and compare system behaviors to identify migration discrepancies",
            backstory="""You are a senior software quality analyst with expertise in 
            migration validation. You excel at identifying subtle differences in system 
            behavior that could impact user experience or business logic. Your analysis 
            is thorough, objective, and actionable.""",
            verbose=True,
            llm=self._get_llm_config(),
        )

    def _get_llm_config(self) -> str:
        """Get LLM configuration string for CrewAI."""
        if self.llm_service:
            provider_info = self.llm_service.get_provider_info()
            return f"{provider_info['provider']}/{provider_info['model']}"
        return "openai/gpt-4-turbo-preview"

    def create_comparison_task(self, source_log: str, target_log: str) -> Task:
        """Create task for comparing behavioral logs."""
        return Task(
            description=f"""
            Perform comprehensive behavioral comparison between source and target systems
            using the detailed browser automation logs.

            Source System Log:
            {source_log}

            Target System Log:
            {target_log}

            Conduct systematic analysis across multiple dimensions:

            1. STRUCTURAL COMPARISON:
            - Compare page states captured at identical interaction points
            - Analyze form structures, field counts, and element types
            - Evaluate navigation patterns and URL structures
            - Check UI element consistency (buttons, inputs, messages)

            2. FUNCTIONAL EQUIVALENCE:
            - Compare scenario execution success rates
            - Analyze identical input -> output patterns
            - Verify business logic consistency
            - Check data processing and validation outcomes

            3. USER EXPERIENCE ANALYSIS:
            - Compare interaction patterns and response times
            - Analyze error message consistency and clarity
            - Evaluate visual consistency using screenshot comparisons
            - Check accessibility and usability patterns

            4. PERFORMANCE METRICS:
            - Compare page load times and response latencies
            - Analyze interaction timing patterns
            - Evaluate system responsiveness under identical conditions

            5. ERROR HANDLING VALIDATION:
            - Compare error case behaviors and messaging
            - Analyze validation rule consistency
            - Check error recovery patterns

            6. AUTHENTICATION & SECURITY:
            - Compare login flows and security measures
            - Analyze session management consistency
            - Check access control patterns

            For each discrepancy identified:
            - Classify severity: CRITICAL (blocks migration), WARNING (needs attention), INFO (minor difference)
            - Quantify business impact (user confusion, workflow disruption, data issues)
            - Provide specific technical recommendations with implementation guidance
            - Assign confidence score (0.0-1.0) based on evidence strength
            - Include screenshot/state references for visual validation

            Calculate overall fidelity score based on:
            - Functional equivalence (40% weight)
            - User experience consistency (30% weight)
            - Error handling accuracy (20% weight)
            - Performance parity (10% weight)
            """,
            expected_output="""A comprehensive behavioral validation report in JSON format:
            {
                "overall_fidelity_score": 0.85,
                "migration_readiness": "approved_with_warnings",
                "executive_summary": "Migration demonstrates high functional equivalence with minor UX differences",
                "category_scores": {
                    "functional_equivalence": 0.92,
                    "user_experience": 0.81,
                    "error_handling": 0.87,
                    "performance": 0.79
                },
                "discrepancies": [
                    {
                        "id": "DISC-001",
                        "type": "error_message_difference",
                        "severity": "warning",
                        "title": "Login error message inconsistency",
                        "description": "Source shows 'Invalid credentials' while target shows 'Login failed'",
                        "business_impact": "Minor user confusion but no functional impact",
                        "recommendation": "Standardize error messaging to match source system",
                        "confidence": 0.95,
                        "evidence": {
                            "source_screenshot": "/path/to/source_error.png",
                            "target_screenshot": "/path/to/target_error.png",
                            "source_state": {...},
                            "target_state": {...}
                        }
                    }
                ],
                "recommendations": [
                    "Update error messaging for consistency",
                    "Performance optimization for login flow"
                ],
                "validation_metadata": {
                    "scenarios_tested": 12,
                    "total_interactions": 156,
                    "screenshots_captured": 24,
                    "execution_time": 180.5
                }
            }""",
            agent=self.agent,
        )


class ReportManagerAgent:
    """Agent that orchestrates the team and generates final reports."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

        self.agent = Agent(
            role="Validation Report Manager",
            goal="Orchestrate the validation process and generate comprehensive reports",
            backstory="""You are a project manager and technical writer with expertise 
            in migration validation. You excel at coordinating teams, synthesizing 
            technical findings, and communicating results clearly to stakeholders.""",
            verbose=True,
            llm=self._get_llm_config(),
        )

    def _get_llm_config(self) -> str:
        """Get LLM configuration string for CrewAI."""
        if self.llm_service:
            provider_info = self.llm_service.get_provider_info()
            return f"{provider_info['provider']}/{provider_info['model']}"
        return "openai/gpt-4-turbo-preview"

    def create_report_task(self, comparison_results: str, metadata: Dict[str, Any]) -> Task:
        """Create task for generating final validation report."""
        return Task(
            description=f"""
            Generate a comprehensive migration validation report based on the 
            behavioral analysis results.
            
            Comparison Results:
            {comparison_results}
            
            Validation Metadata:
            {json.dumps(metadata, indent=2)}
            
            Create a report that includes:
            1. Executive summary with overall validation status
            2. Detailed findings organized by severity
            3. Functional areas analysis (authentication, forms, workflows, etc.)
            4. Business impact assessment
            5. Specific remediation recommendations
            6. Migration readiness assessment
            
            The report should be actionable and provide clear guidance for 
            stakeholders on migration decisions.
            """,
            expected_output="""A comprehensive validation report in JSON format suitable 
            for both technical teams and business stakeholders, with clear recommendations 
            and migration readiness assessment.""",
            agent=self.agent,
        )


class BehavioralValidationCrew:
    """Main crew for behavioral validation of migrated systems."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        """Initialize behavioral validation crew."""
        self.llm_service = llm_service
        self.logger = logger.bind(crew="behavioral_validation")

        # Initialize agents
        self.source_explorer = SourceExplorerAgent(llm_service)
        self.target_executor = TargetExecutorAgent(llm_service)
        self.comparison_judge = ComparisonJudgeAgent(llm_service)
        self.report_manager = ReportManagerAgent(llm_service)

        self.logger.info("Behavioral validation crew initialized")

    async def validate_migration(
        self, request: BehavioralValidationRequest
    ) -> BehavioralValidationResult:
        """
        Execute complete behavioral validation workflow.

        Args:
            request: Behavioral validation request

        Returns:
            Validation results with discrepancies and recommendations
        """
        start_time = datetime.now()
        execution_log = []

        try:
            self.logger.info(
                "Starting behavioral validation",
                source_url=request.source_url,
                target_url=request.target_url,
            )

            # Create tasks
            source_task = self.source_explorer.create_exploration_task(
                request.source_url, request.validation_scenarios
            )

            # Create crew for source exploration
            source_crew = Crew(
                agents=[self.source_explorer.agent],
                tasks=[source_task],
                process=Process.sequential,
                verbose=True,
            )

            execution_log.append("Starting source system exploration")
            source_result = source_crew.kickoff()
            execution_log.append("Source system exploration completed")

            # Create target execution task
            target_task = self.target_executor.create_execution_task(
                request.target_url, str(source_result)
            )

            # Create crew for target execution
            target_crew = Crew(
                agents=[self.target_executor.agent],
                tasks=[target_task],
                process=Process.sequential,
                verbose=True,
            )

            execution_log.append("Starting target system execution")
            target_result = target_crew.kickoff()
            execution_log.append("Target system execution completed")

            # Create comparison task
            comparison_task = self.comparison_judge.create_comparison_task(
                str(source_result), str(target_result)
            )

            # Create crew for comparison
            comparison_crew = Crew(
                agents=[self.comparison_judge.agent],
                tasks=[comparison_task],
                process=Process.sequential,
                verbose=True,
            )

            execution_log.append("Starting behavioral comparison analysis")
            comparison_result = comparison_crew.kickoff()
            execution_log.append("Behavioral comparison analysis completed")

            # Create final report task
            report_task = self.report_manager.create_report_task(
                str(comparison_result), request.metadata or {}
            )

            # Create crew for final report
            report_crew = Crew(
                agents=[self.report_manager.agent],
                tasks=[report_task],
                process=Process.sequential,
                verbose=True,
            )

            execution_log.append("Generating final validation report")
            final_report = report_crew.kickoff()
            execution_log.append("Final validation report completed")

            # Parse results
            results = self._parse_validation_results(str(final_report))

            execution_time = (datetime.now() - start_time).total_seconds()

            # Clean up browser resources
            try:
                await self.cleanup_browser_resources()
                execution_log.append("Browser resources cleaned up")
            except Exception as e:
                self.logger.warning("Browser cleanup failed", error=str(e))
                execution_log.append(f"Browser cleanup warning: {str(e)}")

            self.logger.info(
                "Behavioral validation completed successfully",
                execution_time=execution_time,
                discrepancies_found=len(results.get("discrepancies", [])),
            )

            return BehavioralValidationResult(
                overall_status=results.get("overall_status", "completed"),
                fidelity_score=results.get("fidelity_score", 0.0),
                discrepancies=results.get("discrepancies", []),
                execution_log=execution_log,
                execution_time=execution_time,
                timestamp=datetime.now(),
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error("Behavioral validation failed", error=str(e))

            # Attempt cleanup even on failure
            try:
                await self.cleanup_browser_resources()
                execution_log.append("Browser resources cleaned up after error")
            except Exception as cleanup_error:
                self.logger.warning("Browser cleanup failed after error", error=str(cleanup_error))
                execution_log.append(f"Browser cleanup error: {str(cleanup_error)}")

            return BehavioralValidationResult(
                overall_status="error",
                fidelity_score=0.0,
                discrepancies=[
                    ValidationDiscrepancy(
                        type="execution_error",
                        severity=SeverityLevel.CRITICAL,
                        description=f"Behavioral validation failed: {str(e)}",
                        recommendation="Review system configuration and retry validation",
                    )
                ],
                execution_log=execution_log + [f"Error: {str(e)}"],
                execution_time=execution_time,
                timestamp=datetime.now(),
            )

    def _parse_validation_results(self, report_content: str) -> Dict[str, Any]:
        """Parse final validation report content."""
        try:
            # Try to parse as JSON
            if report_content.strip().startswith("{"):
                parsed_results = json.loads(report_content)

                # Convert discrepancy dictionaries to ValidationDiscrepancy objects
                if "discrepancies" in parsed_results and isinstance(
                    parsed_results["discrepancies"], list
                ):
                    validated_discrepancies = []
                    for disc_data in parsed_results["discrepancies"]:
                        if isinstance(disc_data, dict):
                            try:
                                # Handle severity conversion
                                severity = disc_data.get("severity", "info")
                                if isinstance(severity, str):
                                    severity = SeverityLevel(severity.lower())
                                elif hasattr(severity, "value"):
                                    severity = SeverityLevel(severity.value.lower())

                                discrepancy = ValidationDiscrepancy(
                                    type=disc_data.get("type", "unknown"),
                                    severity=severity,
                                    description=disc_data.get("description", "No description"),
                                    source_element=disc_data.get("source_element"),
                                    target_element=disc_data.get("target_element"),
                                    recommendation=disc_data.get("recommendation"),
                                    confidence=float(disc_data.get("confidence", 1.0)),
                                )
                                validated_discrepancies.append(discrepancy)
                            except (ValueError, KeyError) as e:
                                self.logger.warning(
                                    "Invalid discrepancy data",
                                    error=str(e),
                                    data=disc_data,
                                )
                                # Create a fallback discrepancy
                                validated_discrepancies.append(
                                    ValidationDiscrepancy(
                                        type="parsing_error",
                                        severity=SeverityLevel.WARNING,
                                        description=f"Failed to parse discrepancy: {str(e)}",
                                        recommendation="Manual review required",
                                    )
                                )

                    parsed_results["discrepancies"] = validated_discrepancies

                return parsed_results

            # Fallback parsing for non-JSON content
            return {
                "overall_status": "completed",
                "fidelity_score": 0.8,  # Default conservative score
                "discrepancies": [],
                "raw_content": report_content,
            }

        except json.JSONDecodeError as e:
            self.logger.warning(
                "Failed to parse validation results as JSON",
                error=str(e),
                content_preview=report_content[:200],
            )
            return {
                "overall_status": "completed_with_parsing_issues",
                "fidelity_score": 0.5,
                "discrepancies": [
                    ValidationDiscrepancy(
                        type="parsing_error",
                        severity=SeverityLevel.WARNING,
                        description=f"Could not parse validation results: {str(e)}",
                        recommendation="Manual review of raw results recommended",
                    )
                ],
                "raw_content": report_content,
            }

        except Exception as e:
            self.logger.error("Unexpected error parsing validation results", error=str(e))
            return {
                "overall_status": "error",
                "fidelity_score": 0.0,
                "discrepancies": [
                    ValidationDiscrepancy(
                        type="unexpected_error",
                        severity=SeverityLevel.CRITICAL,
                        description=f"Unexpected error during result parsing: {str(e)}",
                        recommendation="Contact system administrator",
                    )
                ],
                "raw_content": report_content,
            }

    async def cleanup_browser_resources(self):
        """Clean up browser automation resources after validation."""
        try:
            # Clean up browser tools in all agents
            agents_with_browsers = [self.source_explorer, self.target_executor]

            for agent in agents_with_browsers:
                if hasattr(agent, "browser_tool") and hasattr(agent.browser_tool, "cleanup"):
                    await agent.browser_tool.cleanup()
                    self.logger.info(
                        "Cleaned up browser resources for agent",
                        agent=agent.__class__.__name__,
                    )

        except Exception as e:
            self.logger.warning("Error during browser cleanup", error=str(e))


# Factory function for easy crew creation
def create_behavioral_validation_crew(
    llm_service: Optional[LLMService] = None,
) -> BehavioralValidationCrew:
    """Create behavioral validation crew with proper configuration."""
    return BehavioralValidationCrew(llm_service)
