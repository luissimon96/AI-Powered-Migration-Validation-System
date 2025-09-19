"""
Validation reporter for generating user-friendly migration validation reports.

Transforms validation results into structured reports with executive summaries,
detailed findings, and actionable recommendations.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from ..core.models import (
    ValidationResult,
    ValidationDiscrepancy,
    SeverityLevel,
    AbstractRepresentation,
    MigrationValidationRequest
)


class ValidationReporter:
    """Generates comprehensive validation reports."""
    
    def __init__(self):
        """Initialize validation reporter."""
        self.severity_colors = {
            SeverityLevel.CRITICAL: "#FF4444",
            SeverityLevel.WARNING: "#FFA500", 
            SeverityLevel.INFO: "#4444FF"
        }
        
        self.severity_icons = {
            SeverityLevel.CRITICAL: "🔴",
            SeverityLevel.WARNING: "🟡",
            SeverityLevel.INFO: "🔵"
        }
    
    def generate_report(
        self,
        validation_result: ValidationResult,
        request: MigrationValidationRequest,
        source_representation: Optional[AbstractRepresentation] = None,
        target_representation: Optional[AbstractRepresentation] = None
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
            "fidelity_assessment": self._generate_fidelity_assessment(validation_result),
            "detailed_findings": self._generate_detailed_findings(validation_result.discrepancies),
            "recommendations": self._generate_recommendations(validation_result.discrepancies),
            "technical_details": self._generate_technical_details(
                request, source_representation, target_representation
            ),
            "appendix": self._generate_appendix(validation_result)
        }
        
        return report
    
    def generate_html_report(
        self,
        validation_result: ValidationResult,
        request: MigrationValidationRequest,
        source_representation: Optional[AbstractRepresentation] = None,
        target_representation: Optional[AbstractRepresentation] = None
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
        target_representation: Optional[AbstractRepresentation] = None
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
        target_representation: Optional[AbstractRepresentation] = None
    ) -> str:
        """Generate Markdown version of the validation report."""
        report_data = self.generate_report(
            validation_result, request, source_representation, target_representation
        )
        
        markdown_content = self._render_markdown_template(report_data)
        return markdown_content
    
    def _generate_report_metadata(
        self,
        request: MigrationValidationRequest,
        result: ValidationResult
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
                    "version": request.source_technology.version
                },
                "target_technology": {
                    "type": request.target_technology.type.value,
                    "version": request.target_technology.version
                },
                "validation_scope": request.validation_scope.value
            },
            "execution_details": {
                "execution_time": result.execution_time,
                "timestamp": result.timestamp.isoformat()
            }
        }
    
    def _generate_executive_summary(self, result: ValidationResult) -> Dict[str, Any]:
        """Generate executive summary section."""
        discrepancy_counts = self._count_discrepancies_by_severity(result.discrepancies)
        
        # Determine overall status description
        status_descriptions = {
            "approved": "✅ Migration validation PASSED. The target system successfully preserves all critical functionality from the source system.",
            "approved_with_warnings": f"⚠️ Migration validation PASSED WITH WARNINGS. The target system preserves core functionality but has {discrepancy_counts['warning']} items requiring attention.",
            "rejected": f"❌ Migration validation FAILED. Critical issues were found that prevent approval of the migration."
        }
        
        return {
            "overall_status": result.overall_status,
            "status_description": status_descriptions.get(result.overall_status, "Unknown status"),
            "fidelity_score": result.fidelity_score,
            "fidelity_percentage": f"{result.fidelity_score * 100:.1f}%",
            "summary": result.summary,
            "discrepancy_counts": discrepancy_counts,
            "key_findings": self._extract_key_findings(result.discrepancies[:3])  # Top 3 findings
        }
    
    def _generate_fidelity_assessment(self, result: ValidationResult) -> Dict[str, Any]:
        """Generate fidelity assessment section."""
        score = result.fidelity_score
        
        # Determine score category and explanation
        if score >= 0.95:
            category = "Excellent"
            explanation = "The migration achieved exceptional fidelity with minimal differences."
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
            explanation = "The migration has critical differences that prevent approval."
        
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
                "failed": "<60% (Critical differences)"
            }
        }
    
    def _generate_detailed_findings(self, discrepancies: List[ValidationDiscrepancy]) -> Dict[str, Any]:
        """Generate detailed findings section."""
        findings_by_severity = {
            "critical": [],
            "warning": [],
            "info": []
        }
        
        for discrepancy in discrepancies:
            severity_key = discrepancy.severity.value
            finding = {
                "type": discrepancy.type,
                "description": discrepancy.description,
                "source_element": discrepancy.source_element,
                "target_element": discrepancy.target_element,
                "recommendation": discrepancy.recommendation,
                "confidence": discrepancy.confidence,
                "icon": self.severity_icons[discrepancy.severity]
            }
            findings_by_severity[severity_key].append(finding)
        
        return {
            "total_findings": len(discrepancies),
            "by_severity": findings_by_severity,
            "summary_counts": self._count_discrepancies_by_severity(discrepancies)
        }
    
    def _generate_recommendations(self, discrepancies: List[ValidationDiscrepancy]) -> Dict[str, Any]:
        """Generate recommendations section."""
        recommendations = {
            "immediate_actions": [],
            "review_items": [],
            "enhancements": []
        }
        
        for discrepancy in discrepancies:
            if discrepancy.recommendation:
                recommendation_item = {
                    "priority": discrepancy.severity.value,
                    "description": discrepancy.recommendation,
                    "related_finding": discrepancy.description,
                    "confidence": discrepancy.confidence
                }
                
                if discrepancy.severity == SeverityLevel.CRITICAL:
                    recommendations["immediate_actions"].append(recommendation_item)
                elif discrepancy.severity == SeverityLevel.WARNING:
                    recommendations["review_items"].append(recommendation_item)
                else:
                    recommendations["enhancements"].append(recommendation_item)
        
        # Add general recommendations
        recommendations["general"] = self._generate_general_recommendations(discrepancies)
        
        return recommendations
    
    def _generate_technical_details(
        self,
        request: MigrationValidationRequest,
        source_representation: Optional[AbstractRepresentation],
        target_representation: Optional[AbstractRepresentation]
    ) -> Dict[str, Any]:
        """Generate technical details section."""
        details = {
            "migration_context": {
                "source_technology": request.source_technology.type.value,
                "target_technology": request.target_technology.type.value,
                "validation_scope": request.validation_scope.value
            },
            "analysis_coverage": {}
        }
        
        if source_representation:
            details["source_analysis"] = {
                "ui_elements_count": len(source_representation.ui_elements),
                "backend_functions_count": len(source_representation.backend_functions),
                "data_fields_count": len(source_representation.data_fields),
                "api_endpoints_count": len(source_representation.api_endpoints)
            }
        
        if target_representation:
            details["target_analysis"] = {
                "ui_elements_count": len(target_representation.ui_elements),
                "backend_functions_count": len(target_representation.backend_functions),
                "data_fields_count": len(target_representation.data_fields),
                "api_endpoints_count": len(target_representation.api_endpoints)
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
                    "Rule-based validation for data structures"
                ]
            },
            "confidence_interpretation": {
                "high": "90-100% (Very reliable finding)",
                "medium": "70-89% (Likely accurate, review recommended)",
                "low": "50-69% (Requires manual verification)"
            },
            "severity_definitions": {
                "critical": "Issues that break functionality or cause data loss",
                "warning": "Issues that may impact usability or maintenance",
                "info": "Differences that don't impact functionality but may be of interest"
            }
        }
    
    def _count_discrepancies_by_severity(self, discrepancies: List[ValidationDiscrepancy]) -> Dict[str, int]:
        """Count discrepancies by severity level."""
        counts = {"critical": 0, "warning": 0, "info": 0}
        
        for discrepancy in discrepancies:
            counts[discrepancy.severity.value] += 1
        
        return counts
    
    def _extract_key_findings(self, top_discrepancies: List[ValidationDiscrepancy]) -> List[str]:
        """Extract key findings from top discrepancies."""
        return [disc.description for disc in top_discrepancies]
    
    def _generate_general_recommendations(self, discrepancies: List[ValidationDiscrepancy]) -> List[str]:
        """Generate general recommendations based on discrepancy patterns."""
        recommendations = []
        
        counts = self._count_discrepancies_by_severity(discrepancies)
        
        if counts["critical"] > 0:
            recommendations.append("Address all critical issues before proceeding with migration deployment")
        
        if counts["warning"] > 3:
            recommendations.append("Consider additional testing to verify that warning-level differences don't impact user experience")
        
        if counts["info"] > 5:
            recommendations.append("Document all identified differences for future reference and maintenance")
        
        # Pattern-based recommendations
        types = [disc.type for disc in discrepancies]
        if types.count("missing_field") > 2:
            recommendations.append("Review data mapping to ensure all necessary fields are migrated")
        
        if types.count("function_renamed") > 2:
            recommendations.append("Update documentation to reflect function name changes")
        
        return recommendations
    
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
            icon = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "🔵"
            if findings["by_severity"][severity]:
                markdown += f"\n### {icon} {severity.title()} Issues ({len(findings['by_severity'][severity])})\n\n"
                
                for i, finding in enumerate(findings["by_severity"][severity], 1):
                    markdown += f"{i}. **{finding['description']}**\n"
                    if finding.get('recommendation'):
                        markdown += f"   - *Recommendation:* {finding['recommendation']}\n"
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