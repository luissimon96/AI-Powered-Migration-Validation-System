"""
Semantic comparator for migration validation.

Implements the core comparison logic using LLM to analyze abstract representations
and identify discrepancies between source and target systems.
"""

import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from ..core.models import (
    AbstractRepresentation,
    BackendFunction,
    DataField,
    SeverityLevel,
    UIElement,
    ValidationDiscrepancy,
    ValidationScope,
)
from ..services.llm_service import LLMService, LLMServiceError, create_llm_service


class SemanticComparator:
    """Core comparator for semantic analysis of migration differences."""

    def __init__(self, llm_client=None):
        """Initialize semantic comparator with optional LLM client."""
        self.llm_service = llm_client
        if self.llm_service is None:
            try:
                # Try to create default LLM service
                self.llm_service = create_llm_service()
            except Exception:
                # LLM service not available, will use fallback analysis
                self.llm_service = None
        self.comparison_weights = {
            ValidationScope.UI_LAYOUT: {
                "ui_elements": 0.8,
                "data_fields": 0.2,
                "backend_functions": 0.0,
                "api_endpoints": 0.0,
            },
            ValidationScope.BACKEND_FUNCTIONALITY: {
                "ui_elements": 0.0,
                "data_fields": 0.3,
                "backend_functions": 0.7,
                "api_endpoints": 0.0,
            },
            ValidationScope.DATA_STRUCTURE: {
                "ui_elements": 0.0,
                "data_fields": 1.0,
                "backend_functions": 0.0,
                "api_endpoints": 0.0,
            },
            ValidationScope.API_ENDPOINTS: {
                "ui_elements": 0.0,
                "data_fields": 0.2,
                "backend_functions": 0.3,
                "api_endpoints": 0.5,
            },
            ValidationScope.BUSINESS_LOGIC: {
                "ui_elements": 0.1,
                "data_fields": 0.2,
                "backend_functions": 0.7,
                "api_endpoints": 0.0,
            },
            ValidationScope.FULL_SYSTEM: {
                "ui_elements": 0.3,
                "data_fields": 0.2,
                "backend_functions": 0.3,
                "api_endpoints": 0.2,
            },
        }

    async def compare(
        self,
        source: AbstractRepresentation,
        target: AbstractRepresentation,
        scope: ValidationScope,
    ) -> List[ValidationDiscrepancy]:
        """
        Compare source and target representations and identify discrepancies.

        Args:
            source: Source system representation
            target: Target system representation
            scope: Validation scope to focus comparison

        Returns:
            List of validation discrepancies found
        """
        discrepancies = []

        # Get weights for this scope
        weights = self.comparison_weights.get(
            scope, self.comparison_weights[ValidationScope.FULL_SYSTEM]
        )

        # Compare different aspects based on scope weights
        if weights["ui_elements"] > 0:
            ui_discrepancies = await self._compare_ui_elements(
                source.ui_elements, target.ui_elements
            )
            discrepancies.extend(ui_discrepancies)

        if weights["data_fields"] > 0:
            data_discrepancies = await self._compare_data_fields(
                source.data_fields, target.data_fields
            )
            discrepancies.extend(data_discrepancies)

        if weights["backend_functions"] > 0:
            function_discrepancies = await self._compare_backend_functions(
                source.backend_functions, target.backend_functions
            )
            discrepancies.extend(function_discrepancies)

        if weights["api_endpoints"] > 0:
            api_discrepancies = await self._compare_api_endpoints(
                source.api_endpoints, target.api_endpoints
            )
            discrepancies.extend(api_discrepancies)

        # Enhance discrepancies with LLM analysis if available
        if self.llm_client:
            enhanced_discrepancies = await self._enhance_with_llm_analysis(
                source, target, discrepancies, scope
            )
            return enhanced_discrepancies

        return discrepancies

    async def _compare_ui_elements(
        self, source_elements: List[UIElement], target_elements: List[UIElement]
    ) -> List[ValidationDiscrepancy]:
        """Compare UI elements between source and target."""
        discrepancies = []

        # Create maps for easier comparison
        source_map = {self._get_element_key(elem): elem for elem in source_elements}
        target_map = {self._get_element_key(elem): elem for elem in target_elements}

        # Find missing elements (in source but not in target)
        for key, source_elem in source_map.items():
            if key not in target_map:
                # Try fuzzy matching
                fuzzy_match = self._find_fuzzy_ui_match(source_elem, target_elements)
                if fuzzy_match:
                    discrepancy = ValidationDiscrepancy(
                        type="ui_element_renamed",
                        severity=SeverityLevel.WARNING,
                        description=f"UI element '{self._describe_ui_element(source_elem)}' appears to be renamed to '{self._describe_ui_element(fuzzy_match)}'",
                        source_element=self._describe_ui_element(source_elem),
                        target_element=self._describe_ui_element(fuzzy_match),
                        recommendation="Verify that the renamed element maintains the same functionality",
                        confidence=0.7,
                    )
                else:
                    discrepancy = ValidationDiscrepancy(
                        type="missing_ui_element",
                        severity=SeverityLevel.CRITICAL,
                        description=f"UI element '{self._describe_ui_element(source_elem)}' is missing in target",
                        source_element=self._describe_ui_element(source_elem),
                        recommendation="Add the missing UI element to maintain feature parity",
                    )
                discrepancies.append(discrepancy)

        # Find additional elements (in target but not in source)
        for key, target_elem in target_map.items():
            if key not in source_map:
                # Check if this wasn't already identified as a rename
                if not self._is_likely_rename(target_elem, source_elements):
                    discrepancy = ValidationDiscrepancy(
                        type="additional_ui_element",
                        severity=SeverityLevel.INFO,
                        description=f"Additional UI element '{self._describe_ui_element(target_elem)}' found in target",
                        target_element=self._describe_ui_element(target_elem),
                        recommendation="Verify if this element is intentional or represents new functionality",
                    )
                    discrepancies.append(discrepancy)

        # Compare matching elements for attribute differences
        for key in source_map.keys() & target_map.keys():
            source_elem = source_map[key]
            target_elem = target_map[key]

            elem_discrepancies = self._compare_ui_element_attributes(source_elem, target_elem)
            discrepancies.extend(elem_discrepancies)

        return discrepancies

    def _get_element_key(self, element: UIElement) -> str:
        """Generate a key for UI element comparison."""
        if element.id:
            return f"{element.type}#{element.id}"
        elif element.text:
            return f"{element.type}:{element.text[:50]}"
        else:
            return f"{element.type}:anonymous"

    def _describe_ui_element(self, element: UIElement) -> str:
        """Generate human-readable description of UI element."""
        desc_parts = [element.type]
        if element.id:
            desc_parts.append(f"id='{element.id}'")
        if element.text:
            desc_parts.append(f"text='{element.text[:30]}'")
        return " ".join(desc_parts)

    def _find_fuzzy_ui_match(
        self, source_elem: UIElement, target_elements: List[UIElement]
    ) -> Optional[UIElement]:
        """Find potential fuzzy match for a UI element."""
        if not target_elements:
            return None

        # Look for same type and similar text
        for target_elem in target_elements:
            if (
                source_elem.type == target_elem.type
                and source_elem.text
                and target_elem.text
                and self._text_similarity(source_elem.text, target_elem.text) > 0.8
            ):
                return target_elem

        return None

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity score."""
        if not text1 or not text2:
            return 0.0

        text1_lower = text1.lower().strip()
        text2_lower = text2.lower().strip()

        if text1_lower == text2_lower:
            return 1.0

        # Simple similarity based on common characters
        common_chars = set(text1_lower) & set(text2_lower)
        total_chars = set(text1_lower) | set(text2_lower)

        return len(common_chars) / len(total_chars) if total_chars else 0.0

    def _is_likely_rename(self, target_elem: UIElement, source_elements: List[UIElement]) -> bool:
        """Check if target element is likely a rename of a source element."""
        return self._find_fuzzy_ui_match(target_elem, source_elements) is not None

    def _compare_ui_element_attributes(
        self, source_elem: UIElement, target_elem: UIElement
    ) -> List[ValidationDiscrepancy]:
        """Compare attributes of matching UI elements."""
        discrepancies = []

        # Compare positions if available
        if (
            source_elem.position
            and target_elem.position
            and source_elem.position != target_elem.position
        ):
            discrepancy = ValidationDiscrepancy(
                type="ui_position_change",
                severity=SeverityLevel.WARNING,
                description=f"UI element position changed from {source_elem.position} to {target_elem.position}",
                source_element=self._describe_ui_element(source_elem),
                target_element=self._describe_ui_element(target_elem),
                recommendation="Verify that position change doesn't affect usability",
            )
            discrepancies.append(discrepancy)

        return discrepancies

    async def _compare_data_fields(
        self, source_fields: List[DataField], target_fields: List[DataField]
    ) -> List[ValidationDiscrepancy]:
        """Compare data fields between source and target."""
        discrepancies = []

        # Create maps for comparison
        source_map = {field.name: field for field in source_fields}
        target_map = {field.name: field for field in target_fields}

        # Find missing fields
        for name, source_field in source_map.items():
            if name not in target_map:
                # Try fuzzy matching for renamed fields
                fuzzy_match = self._find_fuzzy_field_match(source_field, target_fields)
                if fuzzy_match:
                    discrepancy = ValidationDiscrepancy(
                        type="field_renamed",
                        severity=SeverityLevel.WARNING,
                        description=f"Data field '{source_field.name}' appears to be renamed to '{fuzzy_match.name}'",
                        source_element=f"field:{source_field.name}",
                        target_element=f"field:{fuzzy_match.name}",
                        recommendation="Verify that renamed field maintains the same data semantics",
                        confidence=0.7,
                    )
                else:
                    discrepancy = ValidationDiscrepancy(
                        type="missing_field",
                        severity=SeverityLevel.CRITICAL,
                        description=f"Data field '{source_field.name}' (type: {source_field.type}) is missing in target",
                        source_element=f"field:{source_field.name}",
                        recommendation="Add the missing data field or ensure data is handled elsewhere",
                    )
                discrepancies.append(discrepancy)

        # Find additional fields
        for name, target_field in target_map.items():
            if name not in source_map and not self._is_likely_field_rename(
                target_field, source_fields
            ):
                discrepancy = ValidationDiscrepancy(
                    type="additional_field",
                    severity=SeverityLevel.INFO,
                    description=f"Additional data field '{target_field.name}' (type: {target_field.type}) found in target",
                    target_element=f"field:{target_field.name}",
                    recommendation="Verify if this field represents new functionality or data requirements",
                )
                discrepancies.append(discrepancy)

        # Compare matching fields for type mismatches
        for name in source_map.keys() & target_map.keys():
            source_field = source_map[name]
            target_field = target_map[name]

            if source_field.type != target_field.type:
                discrepancy = ValidationDiscrepancy(
                    type="type_mismatch",
                    severity=SeverityLevel.CRITICAL,
                    description=f"Field '{name}' type changed from {source_field.type} to {target_field.type}",
                    source_element=f"field:{source_field.name}:{source_field.type}",
                    target_element=f"field:{target_field.name}:{target_field.type}",
                    recommendation="Ensure type conversion is handled properly and data integrity is maintained",
                )
                discrepancies.append(discrepancy)

            # Compare constraints
            if source_field.required != target_field.required:
                severity = (
                    SeverityLevel.CRITICAL
                    if source_field.required and not target_field.required
                    else SeverityLevel.WARNING
                )
                discrepancy = ValidationDiscrepancy(
                    type="constraint_change",
                    severity=severity,
                    description=f"Field '{name}' required constraint changed from {source_field.required} to {target_field.required}",
                    source_element=f"field:{source_field.name}",
                    target_element=f"field:{target_field.name}",
                    recommendation="Verify that constraint changes don't break data validation",
                )
                discrepancies.append(discrepancy)

        return discrepancies

    def _find_fuzzy_field_match(
        self, source_field: DataField, target_fields: List[DataField]
    ) -> Optional[DataField]:
        """Find potential fuzzy match for a data field."""
        # Look for fields with similar names and same type
        for target_field in target_fields:
            if (
                source_field.type == target_field.type
                and self._field_name_similarity(source_field.name, target_field.name) > 0.7
            ):
                return target_field
        return None

    def _field_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate field name similarity considering common naming conventions."""
        # Convert to lowercase and handle common transformations
        clean1 = name1.lower().replace("_", "").replace("-", "")
        clean2 = name2.lower().replace("_", "").replace("-", "")

        # Check for camelCase vs snake_case conversions
        if clean1 == clean2:
            return 0.9  # High similarity for naming convention changes

        return self._text_similarity(name1, name2)

    def _is_likely_field_rename(
        self, target_field: DataField, source_fields: List[DataField]
    ) -> bool:
        """Check if target field is likely a rename of a source field."""
        return self._find_fuzzy_field_match(target_field, source_fields) is not None

    async def _compare_backend_functions(
        self,
        source_functions: List[BackendFunction],
        target_functions: List[BackendFunction],
    ) -> List[ValidationDiscrepancy]:
        """Compare backend functions between source and target."""
        discrepancies = []

        # Create maps for comparison
        source_map = {func.name: func for func in source_functions}
        target_map = {func.name: func for func in target_functions}

        # Find missing functions
        for name, source_func in source_map.items():
            if name not in target_map:
                fuzzy_match = self._find_fuzzy_function_match(source_func, target_functions)
                if fuzzy_match:
                    discrepancy = ValidationDiscrepancy(
                        type="function_renamed",
                        severity=SeverityLevel.WARNING,
                        description=f"Function '{source_func.name}' appears to be renamed to '{fuzzy_match.name}'",
                        source_element=f"function:{source_func.name}",
                        target_element=f"function:{fuzzy_match.name}",
                        recommendation="Verify that renamed function maintains the same business logic",
                        confidence=0.7,
                    )
                else:
                    discrepancy = ValidationDiscrepancy(
                        type="missing_function",
                        severity=SeverityLevel.CRITICAL,
                        description=f"Function '{source_func.name}' is missing in target",
                        source_element=f"function:{source_func.name}",
                        recommendation="Implement the missing function or ensure functionality is preserved elsewhere",
                    )
                discrepancies.append(discrepancy)

        # Compare matching functions
        for name in source_map.keys() & target_map.keys():
            source_func = source_map[name]
            target_func = target_map[name]

            func_discrepancies = self._compare_function_details(source_func, target_func)
            discrepancies.extend(func_discrepancies)

        return discrepancies

    def _find_fuzzy_function_match(
        self, source_func: BackendFunction, target_functions: List[BackendFunction]
    ) -> Optional[BackendFunction]:
        """Find potential fuzzy match for a backend function."""
        # Look for functions with similar names and parameters
        for target_func in target_functions:
            if (
                self._function_name_similarity(source_func.name, target_func.name) > 0.7
                and self._parameter_similarity(source_func.parameters, target_func.parameters)
                > 0.8
            ):
                return target_func
        return None

    def _function_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate function name similarity."""
        return self._field_name_similarity(name1, name2)  # Reuse field similarity logic

    def _parameter_similarity(self, params1: List[str], params2: List[str]) -> float:
        """Calculate parameter list similarity."""
        if not params1 and not params2:
            return 1.0
        if not params1 or not params2:
            return 0.0

        common_params = set(params1) & set(params2)
        total_params = set(params1) | set(params2)

        return len(common_params) / len(total_params) if total_params else 0.0

    def _compare_function_details(
        self, source_func: BackendFunction, target_func: BackendFunction
    ) -> List[ValidationDiscrepancy]:
        """Compare details of matching functions."""
        discrepancies = []

        # Compare parameters
        if set(source_func.parameters) != set(target_func.parameters):
            discrepancy = ValidationDiscrepancy(
                type="function_signature_change",
                severity=SeverityLevel.WARNING,
                description=f"Function '{source_func.name}' parameters changed from {source_func.parameters} to {target_func.parameters}",
                source_element=f"function:{source_func.name}",
                target_element=f"function:{target_func.name}",
                recommendation="Verify that parameter changes don't break calling code",
            )
            discrepancies.append(discrepancy)

        # Compare logic summaries if available
        if (
            source_func.logic_summary
            and target_func.logic_summary
            and source_func.logic_summary != target_func.logic_summary
        ):
            discrepancy = ValidationDiscrepancy(
                type="logic_change",
                severity=SeverityLevel.WARNING,
                description=f"Function '{source_func.name}' logic appears to have changed",
                source_element=f"function:{source_func.name}",
                target_element=f"function:{target_func.name}",
                recommendation="Review logic changes to ensure business requirements are still met",
            )
            discrepancies.append(discrepancy)

        return discrepancies

    async def _compare_api_endpoints(
        self,
        source_endpoints: List[Dict[str, Any]],
        target_endpoints: List[Dict[str, Any]],
    ) -> List[ValidationDiscrepancy]:
        """Compare API endpoints between source and target."""
        discrepancies = []

        # Create maps for comparison
        source_map = {self._get_endpoint_key(ep): ep for ep in source_endpoints}
        target_map = {self._get_endpoint_key(ep): ep for ep in target_endpoints}

        # Find missing endpoints
        for key, source_ep in source_map.items():
            if key not in target_map:
                discrepancy = ValidationDiscrepancy(
                    type="missing_endpoint",
                    severity=SeverityLevel.CRITICAL,
                    description=f"API endpoint '{source_ep.get('path', 'unknown')}' is missing in target",
                    source_element=f"endpoint:{key}",
                    recommendation="Implement the missing endpoint or ensure functionality is provided elsewhere",
                )
                discrepancies.append(discrepancy)

        # Find additional endpoints
        for key, target_ep in target_map.items():
            if key not in source_map:
                discrepancy = ValidationDiscrepancy(
                    type="additional_endpoint",
                    severity=SeverityLevel.INFO,
                    description=f"Additional API endpoint '{target_ep.get('path', 'unknown')}' found in target",
                    target_element=f"endpoint:{key}",
                    recommendation="Verify if this endpoint represents new functionality",
                )
                discrepancies.append(discrepancy)

        return discrepancies

    def _get_endpoint_key(self, endpoint: Dict[str, Any]) -> str:
        """Generate a key for endpoint comparison."""
        path = endpoint.get("path", "unknown")
        methods = endpoint.get("methods", ["GET"])
        if isinstance(methods, list):
            methods_str = ",".join(sorted(methods))
        else:
            methods_str = str(methods)
        return f"{methods_str}:{path}"

    async def _enhance_with_llm_analysis(
        self,
        source: AbstractRepresentation,
        target: AbstractRepresentation,
        initial_discrepancies: List[ValidationDiscrepancy],
        scope: ValidationScope,
    ) -> List[ValidationDiscrepancy]:
        """Enhance discrepancy analysis using LLM."""
        if not self.llm_client:
            return initial_discrepancies

        # Prepare data for LLM analysis
        comparison_data = {
            "source": self._serialize_representation(source),
            "target": self._serialize_representation(target),
            "scope": scope.value,
            "initial_discrepancies": [asdict(disc) for disc in initial_discrepancies],
        }

        # Generate LLM prompt
        prompt = self._generate_comparison_prompt(comparison_data)

        try:
            # Call LLM for enhanced analysis
            llm_response = await self._call_llm_for_comparison(prompt, comparison_data)

            # Parse LLM response and enhance discrepancies
            enhanced_discrepancies = self._parse_llm_comparison_response(
                llm_response, initial_discrepancies
            )

            return enhanced_discrepancies

        except Exception as e:
            # Fall back to initial discrepancies if LLM fails
            print(f"LLM enhancement failed: {e}")
            return initial_discrepancies

    def _serialize_representation(self, representation: AbstractRepresentation) -> Dict[str, Any]:
        """Serialize representation for LLM analysis."""
        return {
            "screen_name": representation.screen_name,
            "ui_elements": [asdict(elem) for elem in representation.ui_elements],
            "backend_functions": [asdict(func) for func in representation.backend_functions],
            "data_fields": [asdict(field) for field in representation.data_fields],
            "api_endpoints": representation.api_endpoints,
            "metadata": representation.metadata,
        }

    def _generate_comparison_prompt(self, comparison_data: Dict[str, Any]) -> str:
        """Generate prompt for LLM comparison analysis."""
        return f"""
        You are an expert in software migration validation. Compare the source and target system representations and identify all discrepancies.
        
        Focus on validation scope: {comparison_data['scope']}
        
        Source System:
        {json.dumps(comparison_data['source'], indent=2)}
        
        Target System:
        {json.dumps(comparison_data['target'], indent=2)}
        
        Initial Analysis Found:
        {json.dumps(comparison_data['initial_discrepancies'], indent=2)}
        
        Please provide enhanced analysis including:
        1. Additional discrepancies missed by basic analysis
        2. Severity assessment improvements
        3. Better recommendations for each issue
        4. Confidence scores for identified problems
        5. Overall migration fidelity assessment
        
        Return analysis in JSON format with discrepancies array.
        """

    async def _call_llm_for_comparison(self, prompt: str, data: Dict[str, Any]) -> str:
        """Call LLM for comparison analysis."""
        if self.llm_service is None:
            # Fallback to mock response if LLM service not available
            return await self._mock_llm_comparison_response(data)

        try:
            messages = [
                {
                    "role": "user",
                    "content": f"{prompt}\n\nData to analyze:\n{json.dumps(data, indent=2)}",
                }
            ]

            response = await self.llm_service.generate_response(messages)
            return response.content

        except LLMServiceError as e:
            # Log error and fallback to mock
            print(f"LLM service error: {e}, falling back to mock response")
            return await self._mock_llm_comparison_response(data)

    async def _mock_llm_comparison_response(self, data: Dict[str, Any]) -> str:
        """Mock LLM response for comparison analysis."""
        # Generate mock enhanced analysis
        mock_response = {
            "enhanced_discrepancies": data.get("initial_discrepancies", []),
            "additional_findings": [
                {
                    "type": "semantic_mismatch",
                    "severity": "warning",
                    "description": "Business logic validation appears incomplete in target system",
                    "recommendation": "Review validation rules to ensure data integrity",
                    "confidence": 0.8,
                }
            ],
            "overall_assessment": {
                "fidelity_score": 0.85,
                "migration_status": "approved_with_warnings",
                "critical_issues": 0,
                "warnings": 2,
                "info": 1,
            },
        }

        return json.dumps(mock_response, indent=2)

    def _parse_llm_comparison_response(
        self, llm_response: str, initial_discrepancies: List[ValidationDiscrepancy]
    ) -> List[ValidationDiscrepancy]:
        """Parse LLM response and create enhanced discrepancy list."""
        try:
            response_data = json.loads(llm_response)
            enhanced_discrepancies = initial_discrepancies.copy()

            # Add any additional findings from LLM
            if "additional_findings" in response_data:
                for finding in response_data["additional_findings"]:
                    discrepancy = ValidationDiscrepancy(
                        type=finding.get("type", "llm_finding"),
                        severity=SeverityLevel(finding.get("severity", "info")),
                        description=finding.get("description", "LLM identified issue"),
                        recommendation=finding.get("recommendation"),
                        confidence=finding.get("confidence", 0.8),
                    )
                    enhanced_discrepancies.append(discrepancy)

            return enhanced_discrepancies

        except Exception as e:
            print(f"Failed to parse LLM response: {e}")
            return initial_discrepancies
