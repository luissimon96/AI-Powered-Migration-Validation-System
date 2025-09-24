"""Prompt template management system for LLM-based analysis.

Provides structured prompts for different types of analysis tasks including
code comparison, UI analysis, and business logic validation.
"""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class AnalysisType(Enum):
    """Types of analysis that can be performed."""

    CODE_SEMANTIC_SIMILARITY = "code_semantic_similarity"
    UI_ELEMENT_EXTRACTION = "ui_element_extraction"
    UI_RELATIONSHIP_ANALYSIS = "ui_relationship_analysis"
    BUSINESS_LOGIC_VALIDATION = "business_logic_validation"
    API_COMPARISON = "api_comparison"
    DATA_STRUCTURE_ANALYSIS = "data_structure_analysis"
    MIGRATION_FIDELITY = "migration_fidelity"
    VISUAL_SCREENSHOT_ANALYSIS = "visual_screenshot_analysis"


@dataclass
class PromptTemplate:
    """Represents a structured prompt template."""

    analysis_type: AnalysisType
    system_prompt: str
    user_prompt_template: str
    expected_response_format: dict[str, Any]
    confidence_factors: list[str]
    fallback_response: dict[str, Any]


class PromptTemplateManager:
    """Manages prompt templates for different analysis tasks."""

    def __init__(self):
        """Initialize with predefined templates."""
        self.templates = self._create_default_templates()

    def get_template(self, analysis_type: AnalysisType) -> PromptTemplate:
        """Get template for specific analysis type."""
        return self.templates[analysis_type]

    def format_prompt(
        self,
        analysis_type: AnalysisType,
        context: dict[str, Any],
    ) -> tuple[str, str]:
        """Format system and user prompts with context data."""
        template = self.get_template(analysis_type)

        # Format user prompt with context
        user_prompt = template.user_prompt_template.format(**context)

        return template.system_prompt, user_prompt

    def get_expected_format(self, analysis_type: AnalysisType) -> dict[str, Any]:
        """Get expected response format for analysis type."""
        return self.templates[analysis_type].expected_response_format

    def get_fallback_response(self, analysis_type: AnalysisType) -> dict[str, Any]:
        """Get fallback response for when LLM analysis fails."""
        return self.templates[analysis_type].fallback_response

    def _create_default_templates(self) -> dict[AnalysisType, PromptTemplate]:
        """Create default prompt templates."""
        templates = {}

        # Code Semantic Similarity Template
        templates[AnalysisType.CODE_SEMANTIC_SIMILARITY] = PromptTemplate(
            analysis_type=AnalysisType.CODE_SEMANTIC_SIMILARITY,
            system_prompt="""You are an expert code analysis AI specializing in migration validation.

Your task is to analyze two code snippets (source and target) and determine:
1. Semantic similarity score (0.0 to 1.0)
2. Functional equivalence assessment
3. Key differences and potential issues
4. Business logic preservation
5. Data flow analysis
6. Error handling comparison

Focus on the INTENT and BEHAVIOR of the code, not just syntax.
Consider edge cases, error handling, and business logic preservation.

Respond ONLY in valid JSON format.""",
            user_prompt_template="""Analyze these code snippets for semantic similarity:

SOURCE CODE:
```{source_language}
{source_code}
```

TARGET CODE:
```{target_language}
{target_code}
```

MIGRATION CONTEXT: {context}

Provide detailed analysis in the specified JSON format. Focus on functional equivalence and business logic preservation.""",
            expected_response_format={
                "similarity_score": "float (0.0-1.0)",
                "functionally_equivalent": "boolean",
                "confidence": "float (0.0-1.0)",
                "key_differences": ["string"],
                "potential_issues": ["string"],
                "business_logic_preserved": "boolean",
                "data_flow_preserved": "boolean",
                "error_handling_equivalent": "boolean",
                "performance_considerations": ["string"],
                "recommendations": ["string"],
            },
            confidence_factors=[
                "Code structure similarity",
                "Variable naming consistency",
                "Logic flow preservation",
                "Error handling completeness",
                "Business rule implementation",
            ],
            fallback_response={
                "similarity_score": 0.5,
                "functionally_equivalent": False,
                "confidence": 0.3,
                "key_differences": ["Analysis failed - could not parse response"],
                "potential_issues": ["LLM response parsing error"],
                "business_logic_preserved": False,
                "data_flow_preserved": False,
                "error_handling_equivalent": False,
                "performance_considerations": ["Manual review required"],
                "recommendations": ["Manual code review required"],
            },
        )

        # UI Element Extraction Template
        templates[AnalysisType.UI_ELEMENT_EXTRACTION] = PromptTemplate(
            analysis_type=AnalysisType.UI_ELEMENT_EXTRACTION,
            system_prompt="""You are a UI/UX expert analyzing interface screenshots.

Extract all visible interface elements from the provided screenshot.
Identify interactive elements, text, images, form controls, navigation elements, and layout components.

Pay special attention to:
1. Form elements (inputs, buttons, selects)
2. Navigation components (menus, tabs, breadcrumbs)
3. Data display elements (tables, lists, cards)
4. Interactive elements (buttons, links, controls)
5. Text elements (labels, headings, content)

Respond ONLY in valid JSON format with precise element descriptions.""",
            user_prompt_template="""Analyze this UI screenshot and extract all visible interface elements.

{additional_context}

Identify the purpose and type of each element, providing stable IDs and accurate positioning information.""",
            expected_response_format={
                "elements": [
                    {
                        "type": "string (button, input, label, image, text, table, etc.)",
                        "text": "string or null",
                        "id": "string (descriptive stable ID)",
                        "position": {
                            "x": "int",
                            "y": "int",
                            "width": "int",
                            "height": "int",
                        },
                        "attributes": {
                            "interactive": "boolean",
                            "form_element": "boolean",
                            "navigation": "boolean",
                            "placeholder": "string or null",
                            "validation_required": "boolean",
                        },
                    }
                ],
                "layout_structure": {
                    "header_elements": ["string"],
                    "main_content_elements": ["string"],
                    "sidebar_elements": ["string"],
                    "footer_elements": ["string"],
                },
                "accessibility_notes": ["string"],
                "confidence": "float (0.0-1.0)",
            },
            confidence_factors=[
                "Element visibility clarity",
                "Text readability",
                "UI pattern recognition",
                "Interactive element identification",
            ],
            fallback_response={
                "elements": [],
                "layout_structure": {
                    "header_elements": [],
                    "main_content_elements": [],
                    "sidebar_elements": [],
                    "footer_elements": [],
                },
                "accessibility_notes": ["Manual analysis required"],
                "confidence": 0.1,
            },
        )

        # UI Relationship Analysis Template
        templates[AnalysisType.UI_RELATIONSHIP_ANALYSIS] = PromptTemplate(
            analysis_type=AnalysisType.UI_RELATIONSHIP_ANALYSIS,
            system_prompt="""You are a UI/UX analyst specializing in element relationships and user workflows.

Analyze the relationships between UI elements including:
1. Form field groupings and validation dependencies
2. Navigation flow and hierarchy
3. Interactive element relationships (buttons to forms, etc.)
4. Data display relationships (labels to inputs, headers to tables)
5. Conditional visibility and state dependencies
6. User workflow patterns

Focus on how elements work together to create cohesive user experiences.

Respond ONLY in valid JSON format.""",
            user_prompt_template="""Analyze the relationships between these UI elements:

ELEMENTS:
{elements_json}

SCREEN CONTEXT: {screen_context}

Identify element relationships, user workflows, and interaction patterns.""",
            expected_response_format={
                "element_relationships": [
                    {
                        "source_element_id": "string",
                        "target_element_id": "string",
                        "relationship_type": "string (parent_child, form_validation, navigation, data_binding)",
                        "description": "string",
                    }
                ],
                "user_workflows": [
                    {
                        "workflow_name": "string",
                        "steps": ["string"],
                        "critical_path": "boolean",
                    }
                ],
                "form_groups": [
                    {
                        "group_name": "string",
                        "elements": ["string"],
                        "validation_rules": ["string"],
                    }
                ],
                "navigation_structure": {
                    "primary_navigation": ["string"],
                    "secondary_navigation": ["string"],
                    "breadcrumbs": ["string"],
                },
                "interaction_patterns": ["string"],
                "confidence": "float (0.0-1.0)",
            },
            confidence_factors=[
                "Element naming consistency",
                "Standard UI pattern recognition",
                "Form structure clarity",
                "Navigation pattern identification",
            ],
            fallback_response={
                "element_relationships": [],
                "user_workflows": [],
                "form_groups": [],
                "navigation_structure": {
                    "primary_navigation": [],
                    "secondary_navigation": [],
                    "breadcrumbs": [],
                },
                "interaction_patterns": [],
                "confidence": 0.2,
            },
        )

        # Business Logic Validation Template
        templates[AnalysisType.BUSINESS_LOGIC_VALIDATION] = PromptTemplate(
            analysis_type=AnalysisType.BUSINESS_LOGIC_VALIDATION,
            system_prompt="""You are a business analyst and software architect expert.

Analyze business logic preservation in system migration by comparing:
1. Function signatures and parameters
2. Business rules and constraints
3. Data validation logic
4. Error handling patterns
5. Workflow preservation
6. Decision logic and branching
7. Business process integrity

Focus on identifying critical business logic that must be preserved during migration.

Respond ONLY in valid JSON format.""",
            user_prompt_template="""Validate business logic preservation in this migration:

DOMAIN CONTEXT: {domain_context}

SOURCE FUNCTIONS:
{source_functions_json}

TARGET FUNCTIONS:
{target_functions_json}

Analyze business logic preservation and identify critical discrepancies.""",
            expected_response_format={
                "business_logic_preserved": "boolean",
                "critical_discrepancies": [
                    {
                        "function_name": "string",
                        "discrepancy_type": "string",
                        "severity": "string (critical, warning, info)",
                        "description": "string",
                        "business_impact": "string",
                    }
                ],
                "validation_gaps": ["string"],
                "workflow_integrity": {
                    "preserved": "boolean",
                    "missing_steps": ["string"],
                    "modified_steps": ["string"],
                },
                "data_consistency": {
                    "validation_rules_preserved": "boolean",
                    "constraint_changes": ["string"],
                },
                "risk_assessment": "string (low, medium, high, critical)",
                "recommendations": ["string"],
                "confidence": "float (0.0-1.0)",
            },
            confidence_factors=[
                "Function mapping clarity",
                "Business rule documentation",
                "Validation logic completeness",
                "Error handling coverage",
            ],
            fallback_response={
                "business_logic_preserved": False,
                "critical_discrepancies": [
                    {
                        "function_name": "unknown",
                        "discrepancy_type": "analysis_failed",
                        "severity": "critical",
                        "description": "Analysis failed",
                        "business_impact": "unknown",
                    }
                ],
                "validation_gaps": ["Manual review required"],
                "workflow_integrity": {
                    "preserved": False,
                    "missing_steps": ["unknown"],
                    "modified_steps": ["unknown"],
                },
                "data_consistency": {
                    "validation_rules_preserved": False,
                    "constraint_changes": ["unknown"],
                },
                "risk_assessment": "critical",
                "recommendations": [
                    "Comprehensive manual business logic review required"
                ],
                "confidence": 0.1,
            },
        )

        # Migration Fidelity Template
        templates[AnalysisType.MIGRATION_FIDELITY] = PromptTemplate(
            analysis_type=AnalysisType.MIGRATION_FIDELITY,
            system_prompt="""You are a migration validation expert analyzing overall system fidelity.

Assess the overall fidelity of a migration by analyzing:
1. Feature completeness
2. Functional equivalence
3. User experience preservation
4. Data integrity
5. Performance characteristics
6. Security posture
7. Integration points

Provide a comprehensive assessment with actionable recommendations.

Respond ONLY in valid JSON format.""",
            user_prompt_template="""Assess overall migration fidelity:

SOURCE SYSTEM ANALYSIS:
{source_analysis_json}

TARGET SYSTEM ANALYSIS:
{target_analysis_json}

VALIDATION SCOPE: {validation_scope}

IDENTIFIED DISCREPANCIES:
{discrepancies_json}

Provide comprehensive fidelity assessment and recommendations.""",
            expected_response_format={
                "overall_fidelity_score": "float (0.0-1.0)",
                "migration_status": "string (approved, approved_with_warnings, requires_fixes, rejected)",
                "feature_completeness": {
                    "score": "float (0.0-1.0)",
                    "missing_features": ["string"],
                    "additional_features": ["string"],
                },
                "functional_equivalence": {
                    "score": "float (0.0-1.0)",
                    "critical_differences": ["string"],
                },
                "user_experience": {
                    "score": "float (0.0-1.0)",
                    "ux_issues": ["string"],
                },
                "data_integrity": {
                    "score": "float (0.0-1.0)",
                    "integrity_risks": ["string"],
                },
                "risk_summary": {
                    "critical_issues": "int",
                    "warnings": "int",
                    "info_items": "int",
                    "highest_risk_area": "string",
                },
                "recommendations": [
                    {
                        "priority": "string (high, medium, low)",
                        "category": "string",
                        "description": "string",
                        "estimated_effort": "string",
                    }
                ],
                "confidence": "float (0.0-1.0)",
            },
            confidence_factors=[
                "Analysis completeness",
                "Data quality",
                "Pattern recognition accuracy",
                "Cross-validation consistency",
            ],
            fallback_response={
                "overall_fidelity_score": 0.5,
                "migration_status": "requires_manual_review",
                "feature_completeness": {
                    "score": 0.5,
                    "missing_features": ["unknown"],
                    "additional_features": ["unknown"],
                },
                "functional_equivalence": {
                    "score": 0.5,
                    "critical_differences": ["unknown"],
                },
                "user_experience": {
                    "score": 0.5,
                    "ux_issues": ["unknown"],
                },
                "data_integrity": {
                    "score": 0.5,
                    "integrity_risks": ["unknown"],
                },
                "risk_summary": {
                    "critical_issues": 0,
                    "warnings": 1,
                    "info_items": 0,
                    "highest_risk_area": "analysis_incomplete",
                },
                "recommendations": [
                    {
                        "priority": "high",
                        "category": "analysis",
                        "description": "Manual review required due to analysis failure",
                        "estimated_effort": "unknown",
                    }
                ],
                "confidence": 0.2,
            },
        )

        return templates

    def add_custom_template(self, template: PromptTemplate):
        """Add a custom template to the manager."""
        self.templates[template.analysis_type] = template

    def validate_response_format(
        self,
        analysis_type: AnalysisType,
        response: dict[str, Any],
    ) -> bool:
        """Validate that a response matches the expected format."""
        expected = self.get_expected_format(analysis_type)

        # Basic validation - check if all required keys are present
        for key in expected:
            if key not in response:
                return False

        return True

    def enhance_context(
        self,
        base_context: dict[str, Any],
        analysis_type: AnalysisType,
    ) -> dict[str, Any]:
        """Enhance context with analysis-type specific information."""
        template = self.get_template(analysis_type)

        enhanced = base_context.copy()
        enhanced["confidence_factors"] = template.confidence_factors
        enhanced["expected_format"] = json.dumps(
            template.expected_response_format, indent=2
        )

        return enhanced


# Global instance for easy access
prompt_manager = PromptTemplateManager()
