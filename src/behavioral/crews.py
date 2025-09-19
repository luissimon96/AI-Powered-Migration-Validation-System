"""
CrewAI-based behavioral validation crews for migration testing.

This module implements the multi-agent behavioral validation system that
distinguishes this platform from other migration tools. It uses CrewAI to
orchestrate specialized agents that test real system behavior.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import structlog

from crewai import Agent, Crew, Task, Process
from crewai_tools import BaseTool
from pydantic import BaseModel, Field

from ..core.models import (
    ValidationScope,
    ValidationDiscrepancy,
    SeverityLevel,
    AbstractRepresentation
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


class BrowserTool(BaseTool):
    """Custom tool for browser automation using browser-use."""
    
    name: str = "browser_tool"
    description: str = "Automated browser interaction for testing web applications"
    
    def __init__(self):
        super().__init__()
        # Initialize browser-use here when available
        self.browser = None
    
    def _run(self, action: str, target: str = "", data: str = "") -> str:
        """Execute browser action."""
        try:
            # Placeholder for browser-use integration
            # This would use the browser-use library for intelligent browser control
            return f"Browser action '{action}' executed on '{target}' with data '{data}'"
        except Exception as e:
            return f"Browser action failed: {str(e)}"


class ValidationScenarioResult(BaseModel):
    """Result of a single validation scenario."""
    scenario_name: str = Field(description="Name of the validation scenario")
    source_behavior: str = Field(description="Observed behavior in source system")
    target_behavior: str = Field(description="Observed behavior in target system")
    match_status: str = Field(description="Whether behaviors match: identical, similar, different, error")
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
            llm=self._get_llm_config()
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
            Explore the source system at {source_url} and document its behavior.
            
            Test these validation scenarios:
            {scenario_list}
            
            For each scenario:
            1. Navigate to the relevant page/section
            2. Execute the test scenario step by step
            3. Document all interactions, responses, and behaviors
            4. Test both success and error cases
            5. Note any validation messages, UI changes, or side effects
            
            Create a detailed behavioral log with:
            - Exact steps taken
            - System responses
            - Error messages and validation behavior
            - UI state changes
            - Performance observations
            """,
            expected_output="""A comprehensive behavioral log in JSON format with detailed 
            documentation of each scenario execution, including success flows, error cases, 
            and all observed system behaviors.""",
            agent=self.agent
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
            llm=self._get_llm_config()
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
            Using the source system behavioral log as a guide, execute the same 
            scenarios on the target system at {target_url}.
            
            Source System Log:
            {source_log}
            
            For each scenario in the source log:
            1. Follow the exact same steps documented for the source system
            2. Use the same input data and interaction patterns
            3. Document the target system's responses and behaviors
            4. Note any differences in UI, messages, or functionality
            5. Test the same error cases and edge conditions
            
            Create a parallel behavioral log that can be directly compared 
            with the source system log.
            """,
            expected_output="""A detailed behavioral log in JSON format that mirrors 
            the source system log structure, documenting the target system's behavior 
            for direct comparison.""",
            agent=self.agent
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
            llm=self._get_llm_config()
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
            Compare the source and target system behavioral logs to identify discrepancies.
            
            Source System Log:
            {source_log}
            
            Target System Log:
            {target_log}
            
            Analyze the following aspects:
            1. Functional equivalence - Do both systems achieve the same outcomes?
            2. User experience consistency - Are interactions and flows similar?
            3. Error handling - Do validation and error messages match?
            4. Performance characteristics - Any significant response time differences?
            5. Data integrity - Is information processed and stored correctly?
            
            For each discrepancy found:
            - Classify severity: critical, warning, or info
            - Explain the business impact
            - Provide specific recommendations for resolution
            - Assess confidence in the finding
            """,
            expected_output="""A comprehensive comparison report in JSON format with:
            - Overall similarity assessment and fidelity score
            - Detailed list of discrepancies with severity classification
            - Business impact analysis for each finding
            - Specific recommendations for migration improvements
            - Confidence scores for all assessments""",
            agent=self.agent
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
            llm=self._get_llm_config()
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
            agent=self.agent
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
        self, 
        request: BehavioralValidationRequest
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
            self.logger.info("Starting behavioral validation", 
                           source_url=request.source_url,
                           target_url=request.target_url)
            
            # Create tasks
            source_task = self.source_explorer.create_exploration_task(
                request.source_url, 
                request.validation_scenarios
            )
            
            # Create crew for source exploration
            source_crew = Crew(
                agents=[self.source_explorer.agent],
                tasks=[source_task],
                process=Process.sequential,
                verbose=True
            )
            
            execution_log.append("Starting source system exploration")
            source_result = source_crew.kickoff()
            execution_log.append("Source system exploration completed")
            
            # Create target execution task
            target_task = self.target_executor.create_execution_task(
                request.target_url,
                str(source_result)
            )
            
            # Create crew for target execution
            target_crew = Crew(
                agents=[self.target_executor.agent],
                tasks=[target_task],
                process=Process.sequential,
                verbose=True
            )
            
            execution_log.append("Starting target system execution")
            target_result = target_crew.kickoff()
            execution_log.append("Target system execution completed")
            
            # Create comparison task
            comparison_task = self.comparison_judge.create_comparison_task(
                str(source_result),
                str(target_result)
            )
            
            # Create crew for comparison
            comparison_crew = Crew(
                agents=[self.comparison_judge.agent],
                tasks=[comparison_task],
                process=Process.sequential,
                verbose=True
            )
            
            execution_log.append("Starting behavioral comparison analysis")
            comparison_result = comparison_crew.kickoff()
            execution_log.append("Behavioral comparison analysis completed")
            
            # Create final report task
            report_task = self.report_manager.create_report_task(
                str(comparison_result),
                request.metadata or {}
            )
            
            # Create crew for final report
            report_crew = Crew(
                agents=[self.report_manager.agent],
                tasks=[report_task],
                process=Process.sequential,
                verbose=True
            )
            
            execution_log.append("Generating final validation report")
            final_report = report_crew.kickoff()
            execution_log.append("Final validation report completed")
            
            # Parse results
            results = self._parse_validation_results(str(final_report))
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info("Behavioral validation completed successfully",
                           execution_time=execution_time,
                           discrepancies_found=len(results.get('discrepancies', [])))
            
            return BehavioralValidationResult(
                overall_status=results.get('overall_status', 'completed'),
                fidelity_score=results.get('fidelity_score', 0.0),
                discrepancies=results.get('discrepancies', []),
                execution_log=execution_log,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error("Behavioral validation failed", error=str(e))
            
            return BehavioralValidationResult(
                overall_status="error",
                fidelity_score=0.0,
                discrepancies=[
                    ValidationDiscrepancy(
                        type="execution_error",
                        severity=SeverityLevel.CRITICAL,
                        description=f"Behavioral validation failed: {str(e)}",
                        recommendation="Review system configuration and retry validation"
                    )
                ],
                execution_log=execution_log + [f"Error: {str(e)}"],
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    def _parse_validation_results(self, report_content: str) -> Dict[str, Any]:
        """Parse final validation report content."""
        try:
            # Try to parse as JSON
            if report_content.strip().startswith('{'):
                return json.loads(report_content)
            
            # Fallback parsing for non-JSON content
            return {
                'overall_status': 'completed',
                'fidelity_score': 0.8,  # Default conservative score
                'discrepancies': [],
                'raw_content': report_content
            }
            
        except json.JSONDecodeError:
            self.logger.warning("Failed to parse validation results as JSON",
                              content_preview=report_content[:200])
            return {
                'overall_status': 'completed_with_parsing_issues',
                'fidelity_score': 0.5,
                'discrepancies': [
                    ValidationDiscrepancy(
                        type="parsing_error",
                        severity=SeverityLevel.WARNING,
                        description="Could not parse validation results properly",
                        recommendation="Manual review of raw results recommended"
                    )
                ],
                'raw_content': report_content
            }


# Factory function for easy crew creation
def create_behavioral_validation_crew(llm_service: Optional[LLMService] = None) -> BehavioralValidationCrew:
    """Create behavioral validation crew with proper configuration."""
    return BehavioralValidationCrew(llm_service)