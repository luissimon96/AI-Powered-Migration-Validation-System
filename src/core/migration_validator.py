"""
Main migration validator orchestrating the validation pipeline.

This is the central coordinator that implements the three-stage pipeline:
1. Analysis and Feature Extraction (Source & Target)
2. Semantic Mapping and Comparison
3. Validation Report Generation
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, Optional

from ..analyzers import BaseAnalyzer, CodeAnalyzer, VisualAnalyzer
from ..analyzers.base import AnalyzerError
from ..behavioral.crews import (BehavioralValidationCrew,
                                BehavioralValidationRequest)
from ..comparators.semantic_comparator import SemanticComparator
from ..reporters.validation_reporter import ValidationReporter
from ..services.llm_service import (LLMService, LLMServiceError,
                                    create_llm_service)
from .config import get_validation_config
from .models import (InputType, MigrationValidationRequest, SeverityLevel,
                     TechnologyContext, ValidationResult, ValidationScope,
                     ValidationSession)


class MigrationValidator:
    """
    Main orchestrator for migration validation pipeline.

    Coordinates the three-stage validation process:
    1. Feature extraction from source and target systems
    2. Semantic comparison and discrepancy identification
    3. Report generation with actionable insights
    """

    def __init__(self, llm_client=None):
        """
        Initialize migration validator.

        Args:
            llm_client: Optional LLM service instance for enhanced analysis
        """
        # Initialize LLM service
        if llm_client is None:
            try:
                validation_config = get_validation_config()
                llm_config = validation_config.get_default_llm_config()
                if llm_config:
                    self.llm_service = create_llm_service(
                        provider=llm_config.provider,
                        model=llm_config.model,
                        api_key=llm_config.api_key,
                        max_tokens=llm_config.max_tokens,
                        temperature=llm_config.temperature,
                        timeout=llm_config.timeout,
                    )
                else:
                    self.llm_service = None
            except Exception as e:
                print(f"Failed to initialize LLM service: {e}")
                self.llm_service = None
        else:
            self.llm_service = llm_client

        self.comparator = SemanticComparator(self.llm_service)
        self.reporter = ValidationReporter()
        self._analyzer_cache: Dict[str, BaseAnalyzer] = {}

    async def validate_migration(
        self, request: MigrationValidationRequest
    ) -> ValidationSession:
        """
        Execute complete migration validation pipeline.

        Args:
            request: Migration validation request with all parameters

        Returns:
            Complete validation session with results
        """
        session = ValidationSession(request=request)
        start_time = time.time()

        try:
            session.add_log("Starting migration validation pipeline")

            # Stage 1: Feature Extraction
            session.add_log("Stage 1: Extracting features from source system")
            source_analyzer = self._get_analyzer(
                request.source_technology, request.source_input.type
            )

            session.source_representation = await source_analyzer.analyze(
                request.source_input, request.validation_scope
            )
            session.add_log(
                f"Source analysis complete: {len(session.source_representation.ui_elements)} UI elements, "
                f"{len(session.source_representation.backend_functions)} functions, "
                f"{len(session.source_representation.data_fields)} data fields"
            )

            session.add_log("Stage 1: Extracting features from target system")
            target_analyzer = self._get_analyzer(
                request.target_technology, request.target_input.type
            )

            session.target_representation = await target_analyzer.analyze(
                request.target_input, request.validation_scope
            )
            session.add_log(
                f"Target analysis complete: {len(session.target_representation.ui_elements)} UI elements, "
                f"{len(session.target_representation.backend_functions)} functions, "
                f"{len(session.target_representation.data_fields)} data fields"
            )

            # Stage 2: Semantic Comparison
            session.add_log("Stage 2: Performing semantic comparison")
            discrepancies = await self.comparator.compare(
                session.source_representation,
                session.target_representation,
                request.validation_scope,
            )
            session.add_log(
                f"Comparison complete: {len(discrepancies)} discrepancies found"
            )

            # Stage 3: Result Analysis and Report Generation
            session.add_log(
                "Stage 3: Analyzing results and generating validation outcome"
            )
            execution_time = time.time() - start_time

            session.result = self._analyze_validation_results(
                discrepancies, execution_time
            )

            session.add_log(
                f"Validation complete: {session.result.overall_status} "
                f"with fidelity score {session.result.fidelity_score:.2f}"
            )

            return session

        except Exception as e:
            session.add_log(f"Validation failed with error: {str(e)}")

            # Create error result
            execution_time = time.time() - start_time
            session.result = ValidationResult(
                overall_status="error",
                fidelity_score=0.0,
                summary=f"Validation failed due to error: {str(e)}",
                discrepancies=[],
                execution_time=execution_time,
            )

            raise

    def _get_analyzer(
        self, technology_context: TechnologyContext, input_type: InputType
    ) -> BaseAnalyzer:
        """
        Get appropriate analyzer for technology and input type.

        Args:
            technology_context: Technology context (source or target)
            input_type: Type of input data

        Returns:
            Configured analyzer instance
        """
        cache_key = f"{technology_context.type.value}_{input_type.value}"

        if cache_key in self._analyzer_cache:
            return self._analyzer_cache[cache_key]

        if input_type == InputType.CODE_FILES:
            analyzer = CodeAnalyzer(technology_context)
        elif input_type == InputType.SCREENSHOTS:
            analyzer = VisualAnalyzer(technology_context)
        elif input_type == InputType.HYBRID:
            # For hybrid input, we'll use code analyzer as primary
            # In production, you might want a HybridAnalyzer that combines both
            analyzer = CodeAnalyzer(technology_context)
        else:
            raise AnalyzerError(f"Unsupported input type: {input_type}")

        self._analyzer_cache[cache_key] = analyzer
        return analyzer

    def _analyze_validation_results(
        self, discrepancies, execution_time: float
    ) -> ValidationResult:
        """
        Analyze validation discrepancies and generate final result.

        Args:
            discrepancies: List of validation discrepancies
            execution_time: Pipeline execution time in seconds

        Returns:
            Complete validation result
        """
        # Count discrepancies by severity
        critical_count = sum(
            1 for d in discrepancies if d.severity == SeverityLevel.CRITICAL
        )
        warning_count = sum(
            1 for d in discrepancies if d.severity == SeverityLevel.WARNING
        )
        info_count = sum(1 for d in discrepancies if d.severity == SeverityLevel.INFO)

        # Determine overall status
        if critical_count > 0:
            overall_status = "rejected"
            summary = f"Migration validation failed. Found {critical_count} critical issues that must be resolved."
        elif warning_count > 0:
            overall_status = "approved_with_warnings"
            summary = f"Migration validation passed with {warning_count} warnings requiring review."
        else:
            overall_status = "approved"
            summary = "Migration validation passed successfully with no critical issues found."

        # Calculate fidelity score
        fidelity_score = self._calculate_fidelity_score(
            critical_count, warning_count, info_count
        )

        return ValidationResult(
            overall_status=overall_status,
            fidelity_score=fidelity_score,
            summary=summary,
            discrepancies=discrepancies,
            execution_time=execution_time,
            timestamp=datetime.now(),
        )

    def _calculate_fidelity_score(
        self, critical_count: int, warning_count: int, info_count: int
    ) -> float:
        """
        Calculate fidelity score based on discrepancy counts and severities.

        Args:
            critical_count: Number of critical discrepancies
            warning_count: Number of warning discrepancies
            info_count: Number of info discrepancies

        Returns:
            Fidelity score between 0.0 and 1.0
        """
        # Base score starts at 1.0 (perfect)
        score = 1.0

        # Deduct points based on severity and count
        # Critical issues have major impact
        score -= critical_count * 0.15

        # Warning issues have moderate impact
        score -= warning_count * 0.05

        # Info issues have minimal impact
        score -= info_count * 0.01

        # Apply confidence weighting if available
        # TODO: Incorporate individual discrepancy confidence scores

        # Ensure score stays within bounds
        return max(0.0, min(1.0, score))

    async def generate_report(
        self, session: ValidationSession, format: str = "json"
    ) -> str:
        """
        Generate validation report in specified format.

        Args:
            session: Complete validation session
            format: Report format ('json', 'html', 'markdown')

        Returns:
            Generated report as string
        """
        if not session.result:
            raise ValueError("Validation session must have results to generate report")

        if format.lower() == "html":
            return self.reporter.generate_html_report(
                session.result,
                session.request,
                session.source_representation,
                session.target_representation,
            )
        elif format.lower() == "markdown":
            return self.reporter.generate_markdown_report(
                session.result,
                session.request,
                session.source_representation,
                session.target_representation,
            )
        elif format.lower() == "json":
            return self.reporter.generate_json_report(
                session.result,
                session.request,
                session.source_representation,
                session.target_representation,
            )
        else:
            raise ValueError(f"Unsupported report format: {format}")

    def get_supported_technologies(self) -> Dict[str, Any]:
        """Get information about supported technologies and validation scopes."""
        return {
            "technologies": [
                tech.value
                for tech in TechnologyContext.__annotations__["type"].__args__
            ],
            "validation_scopes": [scope.value for scope in ValidationScope],
            "input_types": [input_type.value for input_type in InputType],
            "capabilities": {
                "code_analysis": [
                    "python",
                    "javascript",
                    "typescript",
                    "java",
                    "csharp",
                    "php",
                    "html",
                ],
                "visual_analysis": ["screenshots", "ui_mockups", "interface_designs"],
                "comparison_features": [
                    "semantic_matching",
                    "fuzzy_element_detection",
                    "business_logic_analysis",
                ],
                "report_formats": ["json", "html", "markdown"],
            },
        }

    async def validate_request(
        self, request: MigrationValidationRequest
    ) -> Dict[str, Any]:
        """
        Validate migration request parameters before processing.

        Args:
            request: Migration validation request

        Returns:
            Validation result with any issues found
        """
        issues = []
        warnings = []

        # Check if technologies are supported
        try:
            source_analyzer = self._get_analyzer(
                request.source_technology, request.source_input.type
            )
            if not source_analyzer.supports_scope(request.validation_scope):
                issues.append(
                    f"Source technology {request.source_technology.type.value} "
                    f"doesn't support validation scope {request.validation_scope.value}"
                )
        except AnalyzerError as e:
            issues.append(f"Source technology not supported: {str(e)}")

        try:
            target_analyzer = self._get_analyzer(
                request.target_technology, request.target_input.type
            )
            if not target_analyzer.supports_scope(request.validation_scope):
                issues.append(
                    f"Target technology {request.target_technology.type.value} "
                    f"doesn't support validation scope {request.validation_scope.value}"
                )
        except AnalyzerError as e:
            issues.append(f"Target technology not supported: {str(e)}")

        # Check input data availability
        if not request.source_input.files and not request.source_input.screenshots:
            issues.append("Source input data is empty")

        if not request.target_input.files and not request.target_input.screenshots:
            issues.append("Target input data is empty")

        # Check file existence
        for file_path in request.source_input.files:
            if not file_path or not file_path.strip():
                issues.append("Empty file path in source input")

        for file_path in request.target_input.files:
            if not file_path or not file_path.strip():
                issues.append("Empty file path in target input")

        # Performance warnings
        total_files = len(request.source_input.files) + len(request.target_input.files)
        total_screenshots = len(request.source_input.screenshots) + len(
            request.target_input.screenshots
        )

        if total_files > 50:
            warnings.append(
                f"Large number of files ({total_files}) may impact processing time"
            )

        if total_screenshots > 10:
            warnings.append(
                f"Large number of screenshots ({total_screenshots}) may impact processing time"
            )

        return {"valid": len(issues) == 0, "issues": issues, "warnings": warnings}
