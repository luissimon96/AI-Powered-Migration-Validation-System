"""
Validation reporter for generating user-friendly migration validation reports.

Transforms validation results into structured reports with executive summaries,
detailed findings, and actionable recommendations.
"""

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..behavioral.crews import BehavioralValidationResult
from ..core.models import (
    AbstractRepresentation,
    MigrationValidationRequest,
    SeverityLevel,
    ValidationDiscrepancy,
    ValidationResult,
)


class ValidationReporter:
    """Generates comprehensive validation reports."""

    def __init__(self):
        """Initialize validation reporter."""
        self.severity_colors = {
            SeverityLevel.CRITICAL: "#FF4444",
            SeverityLevel.WARNING: "#FFA500",
            SeverityLevel.INFO: "#4444FF",
        }

        self.severity_icons = {
            SeverityLevel.CRITICAL: "🔴",
            SeverityLevel.WARNING: "🟡",
            SeverityLevel.INFO: "🔵",
        }

        # Default weights for unified scoring
        self.default_weights = {"static": 0.6, "behavioral": 0.4}

    def generate_report(
        self,
        validation_result: ValidationResult,
        request: MigrationValidationRequest,
        source_representation: Optional[AbstractRepresentation] = None,
        target_representation: Optional[AbstractRepresentation] = None,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive validation report.

        Args:
            validation_result: Validation results with discrepancies
            request: Original validation request
            source_representation: Source system representation
            target_representation: Target system representation

        Returns:
            Comprehensive report dictionary
        """
        report = {
            "metadata": self._generate_report_metadata(request, validation_result),
            "executive_summary": self._generate_executive_summary(validation_result),
            "fidelity_assessment": self._generate_fidelity_assessment(
                validation_result
            ),
            "detailed_findings": self._generate_detailed_findings(
                validation_result.discrepancies
            ),
            "recommendations": self._generate_recommendations(
                validation_result.discrepancies
            ),
            "technical_details": self._generate_technical_details(
                request, source_representation, target_representation
            ),
            "appendix": self._generate_appendix(validation_result),
        }

        return report

    def generate_html_report(
        self,
        validation_result: ValidationResult,
        request: MigrationValidationRequest,
        source_representation: Optional[AbstractRepresentation] = None,
        target_representation: Optional[AbstractRepresentation] = None,
    ) -> str:
        """Generate HTML version of the validation report."""
        report_data = self.generate_report(
            validation_result, request, source_representation, target_representation
        )

        html_content = self._render_html_template(report_data)
        return html_content

    def generate_json_report(
        self,
        validation_result: ValidationResult,
        request: MigrationValidationRequest,
        source_representation: Optional[AbstractRepresentation] = None,
        target_representation: Optional[AbstractRepresentation] = None,
    ) -> str:
        """Generate JSON version of the validation report."""
        report_data = self.generate_report(
            validation_result, request, source_representation, target_representation
        )

        return json.dumps(report_data, indent=2, default=str)

    def generate_markdown_report(
        self,
        validation_result: ValidationResult,
        request: MigrationValidationRequest,
        source_representation: Optional[AbstractRepresentation] = None,
        target_representation: Optional[AbstractRepresentation] = None,
    ) -> str:
        """Generate Markdown version of the validation report."""
        report_data = self.generate_report(
            validation_result, request, source_representation, target_representation
        )

        markdown_content = self._render_markdown_template(report_data)
        return markdown_content

    def generate_unified_report(
        self,
        static_result: Optional[ValidationResult] = None,
        behavioral_result: Optional[BehavioralValidationResult] = None,
        request: Optional[MigrationValidationRequest] = None,
        source_representation: Optional[AbstractRepresentation] = None,
        target_representation: Optional[AbstractRepresentation] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Generate unified report combining static and behavioral validation results.

        Args:
            static_result: Static validation results (optional)
            behavioral_result: Behavioral validation results (optional)
            request: Original validation request (optional)
            source_representation: Source system representation (optional)
            target_representation: Target system representation (optional)
            weights: Custom weights for scoring (defaults: static=0.6, behavioral=0.4)

        Returns:
            Comprehensive unified report dictionary

        Raises:
            ValueError: If both results are None
        """
        if static_result is None and behavioral_result is None:
            raise ValueError(
                "At least one validation result (static or behavioral) must be provided"
            )

        # Use provided weights or defaults
        scoring_weights = weights or self.default_weights

        # Generate unified fidelity score and status
        unified_fidelity = self._calculate_unified_fidelity_score(
            static_result, behavioral_result, scoring_weights
        )
        unified_status = self._determine_unified_status(
            static_result, behavioral_result, unified_fidelity
        )

        # Combine discrepancies from both sources
        combined_discrepancies = self._merge_discrepancies(
            static_result, behavioral_result
        )

        # Build unified report
        report = {
            "metadata": self._generate_unified_metadata(
                static_result, behavioral_result, request, scoring_weights
            ),
            "executive_summary": self._generate_unified_executive_summary(
                static_result,
                behavioral_result,
                unified_status,
                unified_fidelity,
                combined_discrepancies,
            ),
            "fidelity_assessment": self._generate_unified_fidelity_assessment(
                static_result, behavioral_result, unified_fidelity, scoring_weights
            ),
            "detailed_findings": self._generate_unified_detailed_findings(
                combined_discrepancies
            ),
            "recommendations": self._generate_unified_recommendations(
                static_result, behavioral_result, combined_discrepancies
            ),
            "validation_breakdown": self._generate_validation_breakdown(
                static_result, behavioral_result, scoring_weights
            ),
            "technical_details": self._generate_unified_technical_details(
                static_result,
                behavioral_result,
                request,
                source_representation,
                target_representation,
            ),
            "appendix": self._generate_unified_appendix(),
        }

        return report

    def generate_unified_html_report(
        self,
        static_result: Optional[ValidationResult] = None,
        behavioral_result: Optional[BehavioralValidationResult] = None,
        request: Optional[MigrationValidationRequest] = None,
        source_representation: Optional[AbstractRepresentation] = None,
        target_representation: Optional[AbstractRepresentation] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> str:
        """Generate HTML version of the unified validation report."""
        report_data = self.generate_unified_report(
            static_result,
            behavioral_result,
            request,
            source_representation,
            target_representation,
            weights,
        )

        html_content = self._render_unified_html_template(report_data)
        return html_content

    def generate_unified_json_report(
        self,
        static_result: Optional[ValidationResult] = None,
        behavioral_result: Optional[BehavioralValidationResult] = None,
        request: Optional[MigrationValidationRequest] = None,
        source_representation: Optional[AbstractRepresentation] = None,
        target_representation: Optional[AbstractRepresentation] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> str:
        """Generate JSON version of the unified validation report."""
        report_data = self.generate_unified_report(
            static_result,
            behavioral_result,
            request,
            source_representation,
            target_representation,
            weights,
        )

        return json.dumps(report_data, indent=2, default=str)

    def generate_unified_markdown_report(
        self,
        static_result: Optional[ValidationResult] = None,
        behavioral_result: Optional[BehavioralValidationResult] = None,
        request: Optional[MigrationValidationRequest] = None,
        source_representation: Optional[AbstractRepresentation] = None,
        target_representation: Optional[AbstractRepresentation] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> str:
        """Generate Markdown version of the unified validation report."""
        report_data = self.generate_unified_report(
            static_result,
            behavioral_result,
            request,
            source_representation,
            target_representation,
            weights,
        )

        markdown_content = self._render_unified_markdown_template(report_data)
        return markdown_content

    def _generate_report_metadata(
        self, request: MigrationValidationRequest, result: ValidationResult
    ) -> Dict[str, Any]:
        """Generate report metadata section."""
        return {
            "report_id": f"validation_{request.request_id}",
            "generated_at": datetime.now().isoformat(),
            "request_details": {
                "request_id": request.request_id,
                "created_at": request.created_at.isoformat(),
                "source_technology": {
                    "type": request.source_technology.type.value,
                    "version": request.source_technology.version,
                },
                "target_technology": {
                    "type": request.target_technology.type.value,
                    "version": request.target_technology.version,
                },
                "validation_scope": request.validation_scope.value,
            },
            "execution_details": {
                "execution_time": result.execution_time,
                "timestamp": result.timestamp.isoformat(),
            },
        }

    def _generate_executive_summary(self, result: ValidationResult) -> Dict[str, Any]:
        """Generate executive summary section."""
        discrepancy_counts = self._count_discrepancies_by_severity(result.discrepancies)

        # Determine overall status description
        status_descriptions = {
            "approved": "✅ Migration validation PASSED. The target system successfully preserves all critical functionality from the source system.",
            "approved_with_warnings": f"⚠️ Migration validation PASSED WITH WARNINGS. The target system preserves core functionality but has {discrepancy_counts['warning']} items requiring attention.",
            "rejected": f"❌ Migration validation FAILED. Critical issues were found that prevent approval of the migration.",
        }

        return {
            "overall_status": result.overall_status,
            "status_description": status_descriptions.get(
                result.overall_status, "Unknown status"
            ),
            "fidelity_score": result.fidelity_score,
            "fidelity_percentage": f"{result.fidelity_score * 100:.1f}%",
            "summary": result.summary,
            "discrepancy_counts": discrepancy_counts,
            "key_findings": self._extract_key_findings(
                result.discrepancies[:3]
            ),  # Top 3 findings
        }

    def _generate_fidelity_assessment(self, result: ValidationResult) -> Dict[str, Any]:
        """Generate fidelity assessment section."""
        score = result.fidelity_score

        # Determine score category and explanation
        if score >= 0.95:
            category = "Excellent"
            explanation = (
                "The migration achieved exceptional fidelity with minimal differences."
            )
        elif score >= 0.85:
            category = "Good"
            explanation = "The migration achieved good fidelity with minor differences that don't impact core functionality."
        elif score >= 0.75:
            category = "Acceptable"
            explanation = "The migration achieved acceptable fidelity but has some differences requiring review."
        elif score >= 0.60:
            category = "Poor"
            explanation = "The migration has significant differences that may impact functionality."
        else:
            category = "Failed"
            explanation = (
                "The migration has critical differences that prevent approval."
            )

        return {
            "score": score,
            "percentage": f"{score * 100:.1f}%",
            "category": category,
            "explanation": explanation,
            "benchmark": {
                "excellent": "95%+ (Minimal differences)",
                "good": "85-94% (Minor differences)",
                "acceptable": "75-84% (Some differences)",
                "poor": "60-74% (Significant differences)",
                "failed": "<60% (Critical differences)",
            },
        }

    def _generate_detailed_findings(
        self, discrepancies: List[ValidationDiscrepancy]
    ) -> Dict[str, Any]:
        """Generate detailed findings section."""
        findings_by_severity = {"critical": [], "warning": [], "info": []}

        for discrepancy in discrepancies:
            severity_key = discrepancy.severity.value
            finding = {
                "type": discrepancy.type,
                "description": discrepancy.description,
                "source_element": discrepancy.source_element,
                "target_element": discrepancy.target_element,
                "recommendation": discrepancy.recommendation,
                "confidence": discrepancy.confidence,
                "icon": self.severity_icons[discrepancy.severity],
            }
            findings_by_severity[severity_key].append(finding)

        return {
            "total_findings": len(discrepancies),
            "by_severity": findings_by_severity,
            "summary_counts": self._count_discrepancies_by_severity(discrepancies),
        }

    def _generate_recommendations(
        self, discrepancies: List[ValidationDiscrepancy]
    ) -> Dict[str, Any]:
        """Generate recommendations section."""
        recommendations = {
            "immediate_actions": [],
            "review_items": [],
            "enhancements": [],
        }

        for discrepancy in discrepancies:
            if discrepancy.recommendation:
                recommendation_item = {
                    "priority": discrepancy.severity.value,
                    "description": discrepancy.recommendation,
                    "related_finding": discrepancy.description,
                    "confidence": discrepancy.confidence,
                }

                if discrepancy.severity == SeverityLevel.CRITICAL:
                    recommendations["immediate_actions"].append(recommendation_item)
                elif discrepancy.severity == SeverityLevel.WARNING:
                    recommendations["review_items"].append(recommendation_item)
                else:
                    recommendations["enhancements"].append(recommendation_item)

        # Add general recommendations
        recommendations["general"] = self._generate_general_recommendations(
            discrepancies
        )

        return recommendations

    def _generate_technical_details(
        self,
        request: MigrationValidationRequest,
        source_representation: Optional[AbstractRepresentation],
        target_representation: Optional[AbstractRepresentation],
    ) -> Dict[str, Any]:
        """Generate technical details section."""
        details = {
            "migration_context": {
                "source_technology": request.source_technology.type.value,
                "target_technology": request.target_technology.type.value,
                "validation_scope": request.validation_scope.value,
            },
            "analysis_coverage": {},
        }

        if source_representation:
            details["source_analysis"] = {
                "ui_elements_count": len(source_representation.ui_elements),
                "backend_functions_count": len(source_representation.backend_functions),
                "data_fields_count": len(source_representation.data_fields),
                "api_endpoints_count": len(source_representation.api_endpoints),
            }

        if target_representation:
            details["target_analysis"] = {
                "ui_elements_count": len(target_representation.ui_elements),
                "backend_functions_count": len(target_representation.backend_functions),
                "data_fields_count": len(target_representation.data_fields),
                "api_endpoints_count": len(target_representation.api_endpoints),
            }

        return details

    def _generate_appendix(self, result: ValidationResult) -> Dict[str, Any]:
        """Generate appendix section."""
        return {
            "methodology": {
                "analysis_approach": "Semantic comparison using AI-powered feature extraction and LLM-based validation",
                "comparison_techniques": [
                    "Abstract syntax tree analysis for code files",
                    "Computer vision for UI screenshots",
                    "Semantic similarity matching for elements",
                    "Rule-based validation for data structures",
                ],
            },
            "confidence_interpretation": {
                "high": "90-100% (Very reliable finding)",
                "medium": "70-89% (Likely accurate, review recommended)",
                "low": "50-69% (Requires manual verification)",
            },
            "severity_definitions": {
                "critical": "Issues that break functionality or cause data loss",
                "warning": "Issues that may impact usability or maintenance",
                "info": "Differences that don't impact functionality but may be of interest",
            },
        }

    def _count_discrepancies_by_severity(
        self, discrepancies: List[ValidationDiscrepancy]
    ) -> Dict[str, int]:
        """Count discrepancies by severity level."""
        counts = {"critical": 0, "warning": 0, "info": 0}

        for discrepancy in discrepancies:
            counts[discrepancy.severity.value] += 1

        return counts

    def _extract_key_findings(
        self, top_discrepancies: List[ValidationDiscrepancy]
    ) -> List[str]:
        """Extract key findings from top discrepancies."""
        return [disc.description for disc in top_discrepancies]

    def _generate_general_recommendations(
        self, discrepancies: List[ValidationDiscrepancy]
    ) -> List[str]:
        """Generate general recommendations based on discrepancy patterns."""
        recommendations = []

        counts = self._count_discrepancies_by_severity(discrepancies)

        if counts["critical"] > 0:
            recommendations.append(
                "Address all critical issues before proceeding with migration deployment"
            )

        if counts["warning"] > 3:
            recommendations.append(
                "Consider additional testing to verify that warning-level differences don't impact user experience"
            )

        if counts["info"] > 5:
            recommendations.append(
                "Document all identified differences for future reference and maintenance"
            )

        # Pattern-based recommendations
        types = [disc.type for disc in discrepancies]
        if types.count("missing_field") > 2:
            recommendations.append(
                "Review data mapping to ensure all necessary fields are migrated"
            )

        if types.count("function_renamed") > 2:
            recommendations.append(
                "Update documentation to reflect function name changes"
            )

        return recommendations

    def _calculate_unified_fidelity_score(
        self,
        static_result: Optional[ValidationResult],
        behavioral_result: Optional[BehavioralValidationResult],
        weights: Dict[str, float],
    ) -> float:
        """Calculate weighted unified fidelity score."""
        total_weight = 0
        weighted_score = 0

        if static_result is not None:
            weighted_score += static_result.fidelity_score * weights.get("static", 0.6)
            total_weight += weights.get("static", 0.6)

        if behavioral_result is not None:
            weighted_score += behavioral_result.fidelity_score * weights.get(
                "behavioral", 0.4
            )
            total_weight += weights.get("behavioral", 0.4)

        return weighted_score / total_weight if total_weight > 0 else 0.0

    def _determine_unified_status(
        self,
        static_result: Optional[ValidationResult],
        behavioral_result: Optional[BehavioralValidationResult],
        unified_fidelity: float,
    ) -> str:
        """Determine overall unified status based on individual results and fidelity."""
        statuses = []

        if static_result is not None:
            statuses.append(static_result.overall_status)
        if behavioral_result is not None:
            statuses.append(behavioral_result.overall_status)

        # If any result is rejected, unified is rejected
        if "rejected" in statuses or any("error" in status for status in statuses):
            return "rejected"

        # If any result has warnings, unified has warnings
        if any("warning" in status for status in statuses):
            return "approved_with_warnings"

        # If fidelity score is too low, reject
        if unified_fidelity < 0.60:
            return "rejected"
        elif unified_fidelity < 0.85:
            return "approved_with_warnings"
        else:
            return "approved"

    def _merge_discrepancies(
        self,
        static_result: Optional[ValidationResult],
        behavioral_result: Optional[BehavioralValidationResult],
    ) -> List[ValidationDiscrepancy]:
        """Merge discrepancies from both validation types."""
        combined_discrepancies = []

        if static_result is not None:
            # Add static discrepancies with source tagging
            for disc in static_result.discrepancies:
                # Create a copy with source context
                static_disc = ValidationDiscrepancy(
                    type=f"static_{disc.type}",
                    severity=disc.severity,
                    description=f"[Static Analysis] {disc.description}",
                    source_element=disc.source_element,
                    target_element=disc.target_element,
                    recommendation=disc.recommendation,
                    confidence=disc.confidence,
                )
                combined_discrepancies.append(static_disc)

        if behavioral_result is not None:
            # Add behavioral discrepancies with source tagging
            for disc in behavioral_result.discrepancies:
                # Create a copy with source context
                behavioral_disc = ValidationDiscrepancy(
                    type=f"behavioral_{disc.type}",
                    severity=disc.severity,
                    description=f"[Behavioral Testing] {disc.description}",
                    source_element=disc.source_element,
                    target_element=disc.target_element,
                    recommendation=disc.recommendation,
                    confidence=disc.confidence,
                )
                combined_discrepancies.append(behavioral_disc)

        # Sort by severity (critical first) then confidence (highest first)
        severity_order = {
            SeverityLevel.CRITICAL: 0,
            SeverityLevel.WARNING: 1,
            SeverityLevel.INFO: 2,
        }
        combined_discrepancies.sort(
            key=lambda x: (severity_order[x.severity], -x.confidence)
        )

        return combined_discrepancies

    def _generate_unified_metadata(
        self,
        static_result: Optional[ValidationResult],
        behavioral_result: Optional[BehavioralValidationResult],
        request: Optional[MigrationValidationRequest],
        weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """Generate unified metadata section."""
        metadata = {
            "report_id": f"unified_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "validation_types": {
                "static_analysis": static_result is not None,
                "behavioral_testing": behavioral_result is not None,
            },
            "scoring_weights": weights,
        }

        if request:
            metadata["request_details"] = {
                "request_id": request.request_id,
                "created_at": request.created_at.isoformat(),
                "source_technology": {
                    "type": request.source_technology.type.value,
                    "version": request.source_technology.version,
                },
                "target_technology": {
                    "type": request.target_technology.type.value,
                    "version": request.target_technology.version,
                },
                "validation_scope": request.validation_scope.value,
            }

        # Execution details
        execution_details = {}
        if static_result:
            execution_details["static_execution_time"] = static_result.execution_time
            execution_details["static_timestamp"] = static_result.timestamp.isoformat()
        if behavioral_result:
            execution_details["behavioral_execution_time"] = (
                behavioral_result.execution_time
            )
            execution_details["behavioral_timestamp"] = (
                behavioral_result.timestamp.isoformat()
            )

        metadata["execution_details"] = execution_details

        return metadata

    def _generate_unified_executive_summary(
        self,
        static_result: Optional[ValidationResult],
        behavioral_result: Optional[BehavioralValidationResult],
        unified_status: str,
        unified_fidelity: float,
        combined_discrepancies: List[ValidationDiscrepancy],
    ) -> Dict[str, Any]:
        """Generate unified executive summary section."""
        discrepancy_counts = self._count_discrepancies_by_severity(
            combined_discrepancies
        )

        # Generate comprehensive status description
        validation_types = []
        if static_result is not None:
            validation_types.append("static analysis")
        if behavioral_result is not None:
            validation_types.append("behavioral testing")

        validation_type_text = " and ".join(validation_types)

        status_descriptions = {
            "approved": f"✅ Migration validation PASSED. The target system successfully preserves all critical functionality based on {validation_type_text}.",
            "approved_with_warnings": f"⚠️ Migration validation PASSED WITH WARNINGS. The target system preserves core functionality but has {discrepancy_counts['critical'] + discrepancy_counts['warning']} items requiring attention identified through {validation_type_text}.",
            "rejected": f"❌ Migration validation FAILED. Critical issues were found through {validation_type_text} that prevent approval of the migration.",
        }

        # Generate comprehensive summary
        summary_parts = []
        if static_result:
            summary_parts.append(f"Static analysis: {static_result.summary}")
        if behavioral_result:
            if hasattr(behavioral_result, "summary"):
                summary_parts.append(f"Behavioral testing: {behavioral_result.summary}")
            else:
                summary_parts.append(
                    f"Behavioral testing completed with {len(behavioral_result.discrepancies)} findings"
                )

        unified_summary = " | ".join(summary_parts)

        return {
            "overall_status": unified_status,
            "status_description": status_descriptions.get(
                unified_status, "Unknown status"
            ),
            "fidelity_score": unified_fidelity,
            "fidelity_percentage": f"{unified_fidelity * 100:.1f}%",
            "validation_types": validation_types,
            "summary": unified_summary,
            "discrepancy_counts": discrepancy_counts,
            "key_findings": self._extract_key_findings(
                combined_discrepancies[:5]
            ),  # Top 5 findings
        }

    def _generate_unified_fidelity_assessment(
        self,
        static_result: Optional[ValidationResult],
        behavioral_result: Optional[BehavioralValidationResult],
        unified_fidelity: float,
        weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """Generate unified fidelity assessment section."""
        # Determine unified score category
        if unified_fidelity >= 0.95:
            category = "Excellent"
            explanation = "The migration achieved exceptional fidelity with minimal differences across all validation types."
        elif unified_fidelity >= 0.85:
            category = "Good"
            explanation = "The migration achieved good fidelity with minor differences that don't impact core functionality."
        elif unified_fidelity >= 0.75:
            category = "Acceptable"
            explanation = "The migration achieved acceptable fidelity but has some differences requiring review."
        elif unified_fidelity >= 0.60:
            category = "Poor"
            explanation = "The migration has significant differences that may impact functionality."
        else:
            category = "Failed"
            explanation = (
                "The migration has critical differences that prevent approval."
            )

        # Component scores
        component_scores = {}
        if static_result is not None:
            component_scores["static_analysis"] = {
                "score": static_result.fidelity_score,
                "percentage": f"{static_result.fidelity_score * 100:.1f}%",
                "weight": weights.get("static", 0.6),
            }
        if behavioral_result is not None:
            component_scores["behavioral_testing"] = {
                "score": behavioral_result.fidelity_score,
                "percentage": f"{behavioral_result.fidelity_score * 100:.1f}%",
                "weight": weights.get("behavioral", 0.4),
            }

        return {
            "unified_score": unified_fidelity,
            "percentage": f"{unified_fidelity * 100:.1f}%",
            "category": category,
            "explanation": explanation,
            "component_scores": component_scores,
            "scoring_methodology": f"Weighted average: Static ({weights.get('static', 0.6)*100:.0f}%) + Behavioral ({weights.get('behavioral', 0.4)*100:.0f}%)",
            "benchmark": {
                "excellent": "95%+ (Minimal differences)",
                "good": "85-94% (Minor differences)",
                "acceptable": "75-84% (Some differences)",
                "poor": "60-74% (Significant differences)",
                "failed": "<60% (Critical differences)",
            },
        }

    def _generate_unified_detailed_findings(
        self, combined_discrepancies: List[ValidationDiscrepancy]
    ) -> Dict[str, Any]:
        """Generate unified detailed findings section."""
        findings_by_severity = {"critical": [], "warning": [], "info": []}

        findings_by_type = {"static": [], "behavioral": []}

        for discrepancy in combined_discrepancies:
            severity_key = discrepancy.severity.value
            finding = {
                "type": discrepancy.type,
                "description": discrepancy.description,
                "source_element": discrepancy.source_element,
                "target_element": discrepancy.target_element,
                "recommendation": discrepancy.recommendation,
                "confidence": discrepancy.confidence,
                "icon": self.severity_icons[discrepancy.severity],
                "validation_source": (
                    "static" if discrepancy.type.startswith("static_") else "behavioral"
                ),
            }
            findings_by_severity[severity_key].append(finding)

            # Also categorize by validation type
            if discrepancy.type.startswith("static_"):
                findings_by_type["static"].append(finding)
            else:
                findings_by_type["behavioral"].append(finding)

        return {
            "total_findings": len(combined_discrepancies),
            "by_severity": findings_by_severity,
            "by_validation_type": findings_by_type,
            "summary_counts": self._count_discrepancies_by_severity(
                combined_discrepancies
            ),
        }

    def _generate_unified_recommendations(
        self,
        static_result: Optional[ValidationResult],
        behavioral_result: Optional[BehavioralValidationResult],
        combined_discrepancies: List[ValidationDiscrepancy],
    ) -> Dict[str, Any]:
        """Generate unified recommendations section."""
        recommendations = {
            "immediate_actions": [],
            "review_items": [],
            "enhancements": [],
            "static_specific": [],
            "behavioral_specific": [],
        }

        # Process combined discrepancies
        for discrepancy in combined_discrepancies:
            if discrepancy.recommendation:
                recommendation_item = {
                    "priority": discrepancy.severity.value,
                    "description": discrepancy.recommendation,
                    "related_finding": discrepancy.description,
                    "confidence": discrepancy.confidence,
                    "validation_source": (
                        "static"
                        if discrepancy.type.startswith("static_")
                        else "behavioral"
                    ),
                }

                if discrepancy.severity == SeverityLevel.CRITICAL:
                    recommendations["immediate_actions"].append(recommendation_item)
                elif discrepancy.severity == SeverityLevel.WARNING:
                    recommendations["review_items"].append(recommendation_item)
                else:
                    recommendations["enhancements"].append(recommendation_item)

                # Also categorize by validation type
                if discrepancy.type.startswith("static_"):
                    recommendations["static_specific"].append(recommendation_item)
                else:
                    recommendations["behavioral_specific"].append(recommendation_item)

        # Add unified recommendations
        recommendations["unified"] = self._generate_unified_general_recommendations(
            static_result, behavioral_result, combined_discrepancies
        )

        return recommendations

    def _generate_validation_breakdown(
        self,
        static_result: Optional[ValidationResult],
        behavioral_result: Optional[BehavioralValidationResult],
        weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """Generate detailed breakdown of validation components."""
        breakdown = {
            "validation_types_executed": [],
            "execution_timeline": [],
            "performance_metrics": {},
        }

        if static_result is not None:
            breakdown["validation_types_executed"].append("static_analysis")
            breakdown["static_analysis"] = {
                "status": static_result.overall_status,
                "fidelity_score": static_result.fidelity_score,
                "discrepancy_count": len(static_result.discrepancies),
                "execution_time": static_result.execution_time,
                "weight_in_unified_score": weights.get("static", 0.6),
                "summary": static_result.summary,
            }

            if static_result.execution_time:
                breakdown["performance_metrics"][
                    "static_execution_time"
                ] = static_result.execution_time

            breakdown["execution_timeline"].append(
                {
                    "phase": "Static Analysis",
                    "timestamp": static_result.timestamp.isoformat(),
                    "duration": static_result.execution_time,
                }
            )

        if behavioral_result is not None:
            breakdown["validation_types_executed"].append("behavioral_testing")
            breakdown["behavioral_testing"] = {
                "status": behavioral_result.overall_status,
                "fidelity_score": behavioral_result.fidelity_score,
                "discrepancy_count": len(behavioral_result.discrepancies),
                "execution_time": behavioral_result.execution_time,
                "weight_in_unified_score": weights.get("behavioral", 0.4),
                "execution_log_entries": len(behavioral_result.execution_log),
            }

            if behavioral_result.execution_time:
                breakdown["performance_metrics"][
                    "behavioral_execution_time"
                ] = behavioral_result.execution_time

            breakdown["execution_timeline"].append(
                {
                    "phase": "Behavioral Testing",
                    "timestamp": behavioral_result.timestamp.isoformat(),
                    "duration": behavioral_result.execution_time,
                }
            )

        # Calculate total execution time
        total_time = 0
        if static_result and static_result.execution_time:
            total_time += static_result.execution_time
        if behavioral_result and behavioral_result.execution_time:
            total_time += behavioral_result.execution_time

        breakdown["performance_metrics"]["total_execution_time"] = total_time

        return breakdown

    def _generate_unified_technical_details(
        self,
        static_result: Optional[ValidationResult],
        behavioral_result: Optional[BehavioralValidationResult],
        request: Optional[MigrationValidationRequest],
        source_representation: Optional[AbstractRepresentation],
        target_representation: Optional[AbstractRepresentation],
    ) -> Dict[str, Any]:
        """Generate unified technical details section."""
        details = {}

        if request:
            details["migration_context"] = {
                "source_technology": request.source_technology.type.value,
                "target_technology": request.target_technology.type.value,
                "validation_scope": request.validation_scope.value,
            }

        # Static analysis details
        if static_result and (source_representation or target_representation):
            details["static_analysis_coverage"] = {}
            if source_representation:
                details["static_analysis_coverage"]["source_analysis"] = {
                    "ui_elements_count": len(source_representation.ui_elements),
                    "backend_functions_count": len(
                        source_representation.backend_functions
                    ),
                    "data_fields_count": len(source_representation.data_fields),
                    "api_endpoints_count": len(source_representation.api_endpoints),
                }

            if target_representation:
                details["static_analysis_coverage"]["target_analysis"] = {
                    "ui_elements_count": len(target_representation.ui_elements),
                    "backend_functions_count": len(
                        target_representation.backend_functions
                    ),
                    "data_fields_count": len(target_representation.data_fields),
                    "api_endpoints_count": len(target_representation.api_endpoints),
                }

        # Behavioral testing details
        if behavioral_result:
            details["behavioral_testing_coverage"] = {
                "execution_log_entries": len(behavioral_result.execution_log),
                "testing_approach": "Multi-agent behavioral validation using browser automation",
                "validation_agents": [
                    "Source System Explorer",
                    "Target System Executor",
                    "Behavioral Comparison Judge",
                    "Report Manager",
                ],
            }

        return details

    def _generate_unified_appendix(self) -> Dict[str, Any]:
        """Generate unified appendix section."""
        return {
            "methodology": {
                "unified_approach": "Hybrid validation combining static analysis and behavioral testing",
                "static_analysis": "Semantic comparison using AI-powered feature extraction and LLM-based validation",
                "behavioral_testing": "Multi-agent browser automation testing real user workflows",
                "scoring_methodology": "Weighted combination of static and behavioral fidelity scores",
            },
            "validation_types": {
                "static_analysis": {
                    "description": "Code-level analysis comparing source and target implementations",
                    "techniques": [
                        "Abstract syntax tree analysis for code files",
                        "Computer vision for UI screenshots",
                        "Semantic similarity matching for elements",
                        "Rule-based validation for data structures",
                    ],
                },
                "behavioral_testing": {
                    "description": "End-to-end testing of actual system behavior and user workflows",
                    "techniques": [
                        "Browser automation using Playwright",
                        "AI-powered interaction testing",
                        "Visual comparison of UI states",
                        "Performance and response time analysis",
                    ],
                },
            },
            "confidence_interpretation": {
                "high": "90-100% (Very reliable finding)",
                "medium": "70-89% (Likely accurate, review recommended)",
                "low": "50-69% (Requires manual verification)",
            },
            "severity_definitions": {
                "critical": "Issues that break functionality or cause data loss",
                "warning": "Issues that may impact usability or maintenance",
                "info": "Differences that don't impact functionality but may be of interest",
            },
        }

    def _generate_unified_general_recommendations(
        self,
        static_result: Optional[ValidationResult],
        behavioral_result: Optional[BehavioralValidationResult],
        combined_discrepancies: List[ValidationDiscrepancy],
    ) -> List[str]:
        """Generate general recommendations for unified validation."""
        recommendations = []

        counts = self._count_discrepancies_by_severity(combined_discrepancies)

        # Critical issues
        if counts["critical"] > 0:
            recommendations.append(
                "Address all critical issues before proceeding with migration deployment"
            )

        # High number of warnings
        if counts["warning"] > 5:
            recommendations.append(
                "Consider additional validation cycles to address the high number of warnings"
            )

        # Static vs behavioral discrepancy patterns
        static_discrepancies = [
            d for d in combined_discrepancies if d.type.startswith("static_")
        ]
        behavioral_discrepancies = [
            d for d in combined_discrepancies if d.type.startswith("behavioral_")
        ]

        if len(static_discrepancies) > 0 and len(behavioral_discrepancies) == 0:
            recommendations.append(
                "Consider adding behavioral testing to validate real-world usage scenarios"
            )
        elif len(behavioral_discrepancies) > 0 and len(static_discrepancies) == 0:
            recommendations.append(
                "Consider adding static analysis to catch structural and code-level issues"
            )

        # Performance recommendations
        if static_result and behavioral_result:
            if (static_result.execution_time or 0) + (
                behavioral_result.execution_time or 0
            ) > 300:  # 5 minutes
                recommendations.append(
                    "Consider optimizing validation process for better performance in CI/CD pipelines"
                )

        # Documentation recommendations
        if counts["info"] > 3:
            recommendations.append(
                "Document all identified differences for future reference and maintenance"
            )

        return recommendations

    def _render_unified_html_template(self, report_data: Dict[str, Any]) -> str:
        """Render HTML template for unified report."""
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Unified Migration Validation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .summary {{ background: #e8f5e8; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .critical {{ color: #cc0000; }}
                .warning {{ color: #ff6600; }}
                .info {{ color: #0066cc; }}
                .finding {{ margin: 10px 0; padding: 10px; border-left: 3px solid #ccc; }}
                .score {{ font-size: 24px; font-weight: bold; }}
                .validation-breakdown {{ background: #f9f9f9; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .static-badge {{ background: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; }}
                .behavioral-badge {{ background: #2196F3; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; }}
                .component-score {{ display: inline-block; margin: 10px; padding: 10px; background: #f0f0f0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔄 Unified Migration Validation Report</h1>
                <p>Report ID: {report_data['metadata']['report_id']}</p>
                <p>Generated: {report_data['metadata']['generated_at']}</p>
                <p>Validation Types: {', '.join(report_data['executive_summary']['validation_types']).title()}</p>
            </div>

            <div class="summary">
                <h2>Executive Summary</h2>
                <p class="score">Unified Fidelity Score: {report_data['executive_summary']['fidelity_percentage']}</p>
                <p>{report_data['executive_summary']['status_description']}</p>
                <p>{report_data['executive_summary']['summary']}</p>
            </div>

            <div class="validation-breakdown">
                <h2>Validation Breakdown</h2>
                {self._render_validation_breakdown_html(report_data['validation_breakdown'])}
            </div>

            <h2>Detailed Findings</h2>
            {self._render_unified_findings_html(report_data['detailed_findings'])}

            <h2>Recommendations</h2>
            {self._render_unified_recommendations_html(report_data['recommendations'])}
        </body>
        </html>
        """

        return html_template

    def _render_unified_markdown_template(self, report_data: Dict[str, Any]) -> str:
        """Render Markdown template for unified report."""
        markdown = f"""# 🔄 Unified Migration Validation Report

**Report ID:** {report_data['metadata']['report_id']}
**Generated:** {report_data['metadata']['generated_at']}
**Validation Types:** {', '.join(report_data['executive_summary']['validation_types']).title()}

## Executive Summary

### {report_data['executive_summary']['status_description']}

**Unified Fidelity Score:** {report_data['executive_summary']['fidelity_percentage']} ({report_data['fidelity_assessment']['category']})

{report_data['executive_summary']['summary']}

### Validation Component Scores
{self._render_component_scores_markdown(report_data['fidelity_assessment']['component_scores'])}

### Summary Statistics
- 🔴 Critical Issues: {report_data['executive_summary']['discrepancy_counts']['critical']}
- 🟡 Warnings: {report_data['executive_summary']['discrepancy_counts']['warning']}
- 🔵 Info: {report_data['executive_summary']['discrepancy_counts']['info']}

## Validation Breakdown

{self._render_validation_breakdown_markdown(report_data['validation_breakdown'])}

## Detailed Findings

{self._render_unified_findings_markdown(report_data['detailed_findings'])}

## Recommendations

{self._render_unified_recommendations_markdown(report_data['recommendations'])}

## Technical Details

**Migration Context:**
- Source: {report_data['technical_details'].get('migration_context', {}).get('source_technology', 'N/A')}
- Target: {report_data['technical_details'].get('migration_context', {}).get('target_technology', 'N/A')}
- Scope: {report_data['technical_details'].get('migration_context', {}).get('validation_scope', 'N/A')}

---
*Report generated by AI-Powered Migration Validation System - Unified Validation*
"""

        return markdown

    def _render_html_template(self, report_data: Dict[str, Any]) -> str:
        """Render HTML template for the report."""
        # Simple HTML template - in production, use a proper templating engine
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Migration Validation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .summary {{ background: #e8f5e8; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .critical {{ color: #cc0000; }}
                .warning {{ color: #ff6600; }}
                .info {{ color: #0066cc; }}
                .finding {{ margin: 10px 0; padding: 10px; border-left: 3px solid #ccc; }}
                .score {{ font-size: 24px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Migration Validation Report</h1>
                <p>Report ID: {report_data['metadata']['report_id']}</p>
                <p>Generated: {report_data['metadata']['generated_at']}</p>
            </div>
            
            <div class="summary">
                <h2>Executive Summary</h2>
                <p class="score">Fidelity Score: {report_data['executive_summary']['fidelity_percentage']}</p>
                <p>{report_data['executive_summary']['status_description']}</p>
                <p>{report_data['executive_summary']['summary']}</p>
            </div>
            
            <h2>Detailed Findings</h2>
            {self._render_findings_html(report_data['detailed_findings'])}
            
            <h2>Recommendations</h2>
            {self._render_recommendations_html(report_data['recommendations'])}
        </body>
        </html>
        """

        return html_template

    def _render_validation_breakdown_html(self, breakdown: Dict[str, Any]) -> str:
        """Render validation breakdown section in HTML."""
        html = ""

        if "static_analysis" in breakdown:
            static = breakdown["static_analysis"]
            html += f"""
            <div class="component-score">
                <span class="static-badge">STATIC</span>
                <strong>Score:</strong> {static['fidelity_score']:.1%} |
                <strong>Status:</strong> {static['status']} |
                <strong>Weight:</strong> {static['weight_in_unified_score']:.1%}
            </div>
            """

        if "behavioral_testing" in breakdown:
            behavioral = breakdown["behavioral_testing"]
            html += f"""
            <div class="component-score">
                <span class="behavioral-badge">BEHAVIORAL</span>
                <strong>Score:</strong> {behavioral['fidelity_score']:.1%} |
                <strong>Status:</strong> {behavioral['status']} |
                <strong>Weight:</strong> {behavioral['weight_in_unified_score']:.1%}
            </div>
            """

        return html

    def _render_unified_findings_html(self, findings: Dict[str, Any]) -> str:
        """Render unified findings section in HTML."""
        html = ""

        for severity in ["critical", "warning", "info"]:
            if findings["by_severity"][severity]:
                icon = (
                    "🔴"
                    if severity == "critical"
                    else "🟡" if severity == "warning" else "🔵"
                )
                html += f"<h3 class='{severity}'>{icon} {severity.title()} Issues ({len(findings['by_severity'][severity])})</h3>"

                for finding in findings["by_severity"][severity]:
                    validation_badge = f'<span class="{"static-badge" if finding["validation_source"] == "static" else "behavioral-badge"}">{finding["validation_source"].upper()}</span>'
                    html += f"""
                    <div class="finding">
                        {validation_badge}
                        <strong>{finding['description']}</strong><br>
                        {finding.get('recommendation', '')}
                    </div>
                    """

        return html

    def _render_unified_recommendations_html(
        self, recommendations: Dict[str, Any]
    ) -> str:
        """Render unified recommendations section in HTML."""
        html = ""

        if recommendations["immediate_actions"]:
            html += "<h3>🔴 Immediate Actions Required</h3><ul>"
            for action in recommendations["immediate_actions"]:
                validation_badge = f'<span class="{"static-badge" if action["validation_source"] == "static" else "behavioral-badge"}">{action["validation_source"].upper()}</span>'
                html += f"<li>{validation_badge} {action['description']}</li>"
            html += "</ul>"

        if recommendations["review_items"]:
            html += "<h3>🟡 Items for Review</h3><ul>"
            for item in recommendations["review_items"]:
                validation_badge = f'<span class="{"static-badge" if item["validation_source"] == "static" else "behavioral-badge"}">{item["validation_source"].upper()}</span>'
                html += f"<li>{validation_badge} {item['description']}</li>"
            html += "</ul>"

        if recommendations["unified"]:
            html += "<h3>🔄 Unified Recommendations</h3><ul>"
            for rec in recommendations["unified"]:
                html += f"<li>{rec}</li>"
            html += "</ul>"

        return html

    def _render_component_scores_markdown(
        self, component_scores: Dict[str, Any]
    ) -> str:
        """Render component scores in Markdown."""
        markdown = ""

        for component, score_info in component_scores.items():
            component_name = component.replace("_", " ").title()
            markdown += f"- **{component_name}:** {score_info['percentage']} (weight: {score_info['weight']:.1%})\n"

        return markdown

    def _render_validation_breakdown_markdown(self, breakdown: Dict[str, Any]) -> str:
        """Render validation breakdown section in Markdown."""
        markdown = ""

        if "static_analysis" in breakdown:
            static = breakdown["static_analysis"]
            markdown += f"""### 🔧 Static Analysis
- **Status:** {static['status']}
- **Fidelity Score:** {static['fidelity_score']:.1%}
- **Discrepancies Found:** {static['discrepancy_count']}
- **Weight in Unified Score:** {static['weight_in_unified_score']:.1%}
- **Execution Time:** {static.get('execution_time', 'N/A')}s

"""

        if "behavioral_testing" in breakdown:
            behavioral = breakdown["behavioral_testing"]
            markdown += f"""### 🧪 Behavioral Testing
- **Status:** {behavioral['status']}
- **Fidelity Score:** {behavioral['fidelity_score']:.1%}
- **Discrepancies Found:** {behavioral['discrepancy_count']}
- **Weight in Unified Score:** {behavioral['weight_in_unified_score']:.1%}
- **Execution Time:** {behavioral.get('execution_time', 'N/A')}s
- **Execution Log Entries:** {behavioral.get('execution_log_entries', 'N/A')}

"""

        return markdown

    def _render_unified_findings_markdown(self, findings: Dict[str, Any]) -> str:
        """Render unified findings section in Markdown."""
        markdown = ""

        for severity in ["critical", "warning", "info"]:
            icon = (
                "🔴"
                if severity == "critical"
                else "🟡" if severity == "warning" else "🔵"
            )
            if findings["by_severity"][severity]:
                markdown += f"\n### {icon} {severity.title()} Issues ({len(findings['by_severity'][severity])})\n\n"

                for i, finding in enumerate(findings["by_severity"][severity], 1):
                    validation_source = finding["validation_source"].upper()
                    markdown += (
                        f"{i}. **[{validation_source}]** {finding['description']}\n"
                    )
                    if finding.get("recommendation"):
                        markdown += (
                            f"   - *Recommendation:* {finding['recommendation']}\n"
                        )
                    markdown += "\n"

        return markdown

    def _render_unified_recommendations_markdown(
        self, recommendations: Dict[str, Any]
    ) -> str:
        """Render unified recommendations section in Markdown."""
        markdown = ""

        if recommendations["immediate_actions"]:
            markdown += "\n### 🔴 Immediate Actions Required\n\n"
            for action in recommendations["immediate_actions"]:
                validation_source = action["validation_source"].upper()
                markdown += f"- **[{validation_source}]** {action['description']}\n"

        if recommendations["review_items"]:
            markdown += "\n### 🟡 Items for Review\n\n"
            for item in recommendations["review_items"]:
                validation_source = item["validation_source"].upper()
                markdown += f"- **[{validation_source}]** {item['description']}\n"

        if recommendations["static_specific"]:
            markdown += "\n### 🔧 Static Analysis Specific\n\n"
            for rec in recommendations["static_specific"]:
                markdown += f"- {rec['description']}\n"

        if recommendations["behavioral_specific"]:
            markdown += "\n### 🧪 Behavioral Testing Specific\n\n"
            for rec in recommendations["behavioral_specific"]:
                markdown += f"- {rec['description']}\n"

        if recommendations["unified"]:
            markdown += "\n### 🔄 Unified Recommendations\n\n"
            for rec in recommendations["unified"]:
                markdown += f"- {rec}\n"

        return markdown

    def _render_findings_html(self, findings: Dict[str, Any]) -> str:
        """Render findings section in HTML."""
        html = ""

        for severity in ["critical", "warning", "info"]:
            if findings["by_severity"][severity]:
                html += f"<h3 class='{severity}'>{'🔴' if severity == 'critical' else '🟡' if severity == 'warning' else '🔵'} {severity.title()} Issues ({len(findings['by_severity'][severity])})</h3>"

                for finding in findings["by_severity"][severity]:
                    html += f"""
                    <div class="finding">
                        <strong>{finding['description']}</strong><br>
                        {finding.get('recommendation', '')}
                    </div>
                    """

        return html

    def _render_recommendations_html(self, recommendations: Dict[str, Any]) -> str:
        """Render recommendations section in HTML."""
        html = ""

        if recommendations["immediate_actions"]:
            html += "<h3>🔴 Immediate Actions Required</h3><ul>"
            for action in recommendations["immediate_actions"]:
                html += f"<li>{action['description']}</li>"
            html += "</ul>"

        if recommendations["review_items"]:
            html += "<h3>🟡 Items for Review</h3><ul>"
            for item in recommendations["review_items"]:
                html += f"<li>{item['description']}</li>"
            html += "</ul>"

        return html

    def _render_markdown_template(self, report_data: Dict[str, Any]) -> str:
        """Render Markdown template for the report."""
        markdown = f"""# Migration Validation Report

**Report ID:** {report_data['metadata']['report_id']}  
**Generated:** {report_data['metadata']['generated_at']}

## Executive Summary

### {report_data['executive_summary']['status_description']}

**Fidelity Score:** {report_data['executive_summary']['fidelity_percentage']} ({report_data['fidelity_assessment']['category']})

{report_data['executive_summary']['summary']}

### Summary Statistics
- 🔴 Critical Issues: {report_data['executive_summary']['discrepancy_counts']['critical']}
- 🟡 Warnings: {report_data['executive_summary']['discrepancy_counts']['warning']}  
- 🔵 Info: {report_data['executive_summary']['discrepancy_counts']['info']}

## Detailed Findings

{self._render_findings_markdown(report_data['detailed_findings'])}

## Recommendations

{self._render_recommendations_markdown(report_data['recommendations'])}

## Technical Details

**Migration Context:**
- Source: {report_data['technical_details']['migration_context']['source_technology']}
- Target: {report_data['technical_details']['migration_context']['target_technology']}
- Scope: {report_data['technical_details']['migration_context']['validation_scope']}

---
*Report generated by AI-Powered Migration Validation System*
"""

        return markdown

    def _render_findings_markdown(self, findings: Dict[str, Any]) -> str:
        """Render findings section in Markdown."""
        markdown = ""

        for severity in ["critical", "warning", "info"]:
            icon = (
                "🔴"
                if severity == "critical"
                else "🟡" if severity == "warning" else "🔵"
            )
            if findings["by_severity"][severity]:
                markdown += f"\n### {icon} {severity.title()} Issues ({len(findings['by_severity'][severity])})\n\n"

                for i, finding in enumerate(findings["by_severity"][severity], 1):
                    markdown += f"{i}. **{finding['description']}**\n"
                    if finding.get("recommendation"):
                        markdown += (
                            f"   - *Recommendation:* {finding['recommendation']}\n"
                        )
                    markdown += "\n"

        return markdown

    def _render_recommendations_markdown(self, recommendations: Dict[str, Any]) -> str:
        """Render recommendations section in Markdown."""
        markdown = ""

        if recommendations["immediate_actions"]:
            markdown += "\n### 🔴 Immediate Actions Required\n\n"
            for action in recommendations["immediate_actions"]:
                markdown += f"- {action['description']}\n"

        if recommendations["review_items"]:
            markdown += "\n### 🟡 Items for Review\n\n"
            for item in recommendations["review_items"]:
                markdown += f"- {item['description']}\n"

        if recommendations["general"]:
            markdown += "\n### General Recommendations\n\n"
            for rec in recommendations["general"]:
                markdown += f"- {rec}\n"

        return markdown

