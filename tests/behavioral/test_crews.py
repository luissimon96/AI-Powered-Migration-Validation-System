"""
Tests for CrewAI behavioral validation system.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.behavioral.crews import (
    BehavioralValidationCrew,
    BehavioralValidationRequest,
    ComparisonJudgeAgent,
    ReportManagerAgent,
    SourceExplorerAgent,
    TargetExecutorAgent,
    create_behavioral_validation_crew,
)


@pytest.mark.behavioral
class TestBehavioralValidationRequest:
    """Test behavioral validation request model."""

    def test_request_creation(self):
        """Test creating behavioral validation request."""
        request = BehavioralValidationRequest(
            source_url="http://legacy.test/app",
            target_url="http://new.test/app",
            validation_scenarios=["login", "signup", "password_reset"],
            credentials={"username": "test", "password": "test123"},
            timeout=300,
            metadata={"environment": "staging"},
        )

        assert request.source_url == "http://legacy.test/app"
        assert request.target_url == "http://new.test/app"
        assert len(request.validation_scenarios) == 3
        assert request.credentials["username"] == "test"
        assert request.timeout == 300
        assert request.metadata["environment"] == "staging"


@pytest.mark.behavioral
class TestBehavioralValidationAgents:
    """Test individual agents in behavioral validation."""

    def test_source_explorer_agent_creation(self, mock_llm_service):
        """Test source explorer agent creation."""
        agent = SourceExplorerAgent(mock_llm_service)

        assert agent.llm_service == mock_llm_service
        assert agent.agent is not None
        assert "Source System Explorer" in agent.agent.role
        assert agent.browser_tool is not None

    def test_target_executor_agent_creation(self, mock_llm_service):
        """Test target executor agent creation."""
        agent = TargetExecutorAgent(mock_llm_service)

        assert agent.llm_service == mock_llm_service
        assert agent.agent is not None
        assert "Target System Executor" in agent.agent.role
        assert agent.browser_tool is not None

    def test_comparison_judge_agent_creation(self, mock_llm_service):
        """Test comparison judge agent creation."""
        agent = ComparisonJudgeAgent(mock_llm_service)

        assert agent.llm_service == mock_llm_service
        assert agent.agent is not None
        assert "Behavioral Comparison Judge" in agent.agent.role

    def test_report_manager_agent_creation(self, mock_llm_service):
        """Test report manager agent creation."""
        agent = ReportManagerAgent(mock_llm_service)

        assert agent.llm_service == mock_llm_service
        assert agent.agent is not None
        assert "Validation Report Manager" in agent.agent.role

    def test_source_explorer_task_creation(self, mock_llm_service):
        """Test source explorer task creation."""
        agent = SourceExplorerAgent(mock_llm_service)

        scenarios = ["login_flow", "data_entry", "error_handling"]
        task = agent.create_exploration_task("http://source.test", scenarios)

        assert task is not None
        assert "http://source.test" in task.description
        assert "login_flow" in task.description
        assert "data_entry" in task.description
        assert "error_handling" in task.description
        assert task.agent == agent.agent

    def test_target_executor_task_creation(self, mock_llm_service):
        """Test target executor task creation."""
        agent = TargetExecutorAgent(mock_llm_service)

        source_log = '{"scenario": "login", "steps": ["navigate", "fill_form", "submit"]}'
        task = agent.create_execution_task("http://target.test", source_log)

        assert task is not None
        assert "http://target.test" in task.description
        assert "login" in task.description
        assert task.agent == agent.agent

    def test_comparison_judge_task_creation(self, mock_llm_service):
        """Test comparison judge task creation."""
        agent = ComparisonJudgeAgent(mock_llm_service)

        source_log = '{"scenario": "login", "result": "success"}'
        target_log = '{"scenario": "login", "result": "success"}'
        task = agent.create_comparison_task(source_log, target_log)

        assert task is not None
        assert "login" in task.description
        assert task.agent == agent.agent

    def test_report_manager_task_creation(self, mock_llm_service):
        """Test report manager task creation."""
        agent = ReportManagerAgent(mock_llm_service)

        comparison_results = '{"similarity": 0.95, "discrepancies": []}'
        metadata = {"environment": "test"}
        task = agent.create_report_task(comparison_results, metadata)

        assert task is not None
        assert "similarity" in task.description
        assert "environment" in task.description
        assert task.agent == agent.agent


@pytest.mark.behavioral
@pytest.mark.asyncio
class TestBehavioralValidationCrew:
    """Test behavioral validation crew integration."""

    def test_crew_initialization(self, mock_llm_service):
        """Test crew initialization."""
        crew = BehavioralValidationCrew(mock_llm_service)

        assert crew.llm_service == mock_llm_service
        assert crew.source_explorer is not None
        assert crew.target_executor is not None
        assert crew.comparison_judge is not None
        assert crew.report_manager is not None

    def test_crew_initialization_without_llm(self):
        """Test crew initialization without LLM service."""
        crew = BehavioralValidationCrew(llm_service=None)

        assert crew.llm_service is None
        assert crew.source_explorer is not None
        assert crew.target_executor is not None
        assert crew.comparison_judge is not None
        assert crew.report_manager is not None

    @patch("src.behavioral.crews.Crew")
    async def test_validate_migration_success(self, mock_crew_class, mock_llm_service):
        """Test successful migration validation."""
        # Mock crew execution results
        mock_crew_instance = MagicMock()
        mock_crew_class.return_value = mock_crew_instance

        # Mock different results for each crew stage
        mock_crew_instance.kickoff.side_effect = [
            '{"source_exploration": "completed", "scenarios_tested": 3}',  # source exploration
            '{"target_execution": "completed", "scenarios_replicated": 3}',  # target execution
            '{"comparison": "completed", "discrepancies": [], "similarity": 0.95}',  # comparison
            '{"overall_status": "approved", "fidelity_score": 0.95, "discrepancies": []}',  # final report
        ]

        crew = BehavioralValidationCrew(mock_llm_service)

        request = BehavioralValidationRequest(
            source_url="http://source.test",
            target_url="http://target.test",
            validation_scenarios=["login", "signup", "reset_password"],
        )

        result = await crew.validate_migration(request)

        assert result.overall_status == "approved"
        assert result.fidelity_score == 0.95
        assert len(result.discrepancies) == 0
        assert len(result.execution_log) > 0
        assert result.execution_time > 0

        # Verify crew was called multiple times (for each stage)
        assert mock_crew_instance.kickoff.call_count == 4

    @patch("src.behavioral.crews.Crew")
    async def test_validate_migration_with_errors(self, mock_crew_class, mock_llm_service):
        """Test migration validation with errors."""
        # Mock crew execution with error
        mock_crew_instance = MagicMock()
        mock_crew_class.return_value = mock_crew_instance
        mock_crew_instance.kickoff.side_effect = Exception("Browser automation failed")

        crew = BehavioralValidationCrew(mock_llm_service)

        request = BehavioralValidationRequest(
            source_url="http://source.test",
            target_url="http://target.test",
            validation_scenarios=["login"],
        )

        result = await crew.validate_migration(request)

        assert result.overall_status == "error"
        assert result.fidelity_score == 0.0
        assert len(result.discrepancies) == 1
        assert result.discrepancies[0].severity.value == "critical"
        assert "Browser automation failed" in result.discrepancies[0].description

    def test_parse_validation_results_json(self, mock_llm_service):
        """Test parsing valid JSON results."""
        crew = BehavioralValidationCrew(mock_llm_service)

        json_content = (
            '{"overall_status": "approved", "fidelity_score": 0.92, "discrepancies": []}'
        )
        result = crew._parse_validation_results(json_content)

        assert result["overall_status"] == "approved"
        assert result["fidelity_score"] == 0.92
        assert result["discrepancies"] == []

    def test_parse_validation_results_invalid_json(self, mock_llm_service):
        """Test parsing invalid JSON results."""
        crew = BehavioralValidationCrew(mock_llm_service)

        invalid_content = "This is not JSON content"
        result = crew._parse_validation_results(invalid_content)

        assert result["overall_status"] == "completed_with_parsing_issues"
        assert result["fidelity_score"] == 0.5
        assert len(result["discrepancies"]) == 1
        assert result["raw_content"] == invalid_content


@pytest.mark.behavioral
class TestBehavioralValidationFactory:
    """Test behavioral validation factory functions."""

    def test_create_behavioral_validation_crew(self, mock_llm_service):
        """Test factory function for creating crew."""
        crew = create_behavioral_validation_crew(mock_llm_service)

        assert isinstance(crew, BehavioralValidationCrew)
        assert crew.llm_service == mock_llm_service

    def test_create_behavioral_validation_crew_without_llm(self):
        """Test factory function without LLM service."""
        crew = create_behavioral_validation_crew()

        assert isinstance(crew, BehavioralValidationCrew)
        assert crew.llm_service is None
