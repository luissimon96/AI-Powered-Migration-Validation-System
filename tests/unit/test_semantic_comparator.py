"""
Unit tests for semantic comparator.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.comparators.semantic_comparator import SemanticComparator
from src.core.models import TechnologyType


@pytest.mark.unit
class TestSemanticComparator:
    """Test SemanticComparator component."""

    def test_comparator_initialization(self):
        """Test comparator initialization."""
        mock_llm = AsyncMock()
        comparator = SemanticComparator(llm_service=mock_llm)
        assert comparator is not None
        assert comparator.llm_service == mock_llm

    def test_initialization_without_llm(self):
        """Test comparator initialization without LLM service."""
        comparator = SemanticComparator()
        assert comparator is not None
        assert comparator.llm_service is None

    @pytest.mark.asyncio
    async def test_compare_code_semantics(
        self, mock_llm_service, sample_python_code, sample_java_code
    ):
        """Test comparing code semantics."""
        comparator = SemanticComparator(llm_service=mock_llm_service)

        comparison = await comparator.compare_semantics(
            source_code=sample_python_code,
            target_code=sample_java_code,
            source_tech=TechnologyType.PYTHON_FLASK,
            target_tech=TechnologyType.JAVA_SPRING,
        )

        assert comparison is not None
        assert "similarity_score" in comparison
        assert "functionally_equivalent" in comparison
        assert "key_differences" in comparison
        assert "business_logic_preserved" in comparison
        assert 0.0 <= comparison["similarity_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_compare_without_llm(self, sample_python_code, sample_java_code):
        """Test comparing code without LLM service (fallback mode)."""
        comparator = SemanticComparator()

        comparison = await comparator.compare_semantics(
            source_code=sample_python_code,
            target_code=sample_java_code,
            source_tech=TechnologyType.PYTHON_FLASK,
            target_tech=TechnologyType.JAVA_SPRING,
        )

        assert comparison is not None
        assert "similarity_score" in comparison
        assert "method" in comparison
        assert comparison["method"] == "structural_analysis"

    def test_extract_semantic_features_python(self, sample_python_code):
        """Test extracting semantic features from Python code."""
        comparator = SemanticComparator()

        features = comparator.extract_semantic_features(
            sample_python_code, TechnologyType.PYTHON_FLASK
        )

        assert features is not None
        assert "functions" in features
        assert "classes" in features
        assert "business_logic" in features
        assert "data_flow" in features
        assert "control_structures" in features

    def test_extract_semantic_features_java(self, sample_java_code):
        """Test extracting semantic features from Java code."""
        comparator = SemanticComparator()

        features = comparator.extract_semantic_features(
            sample_java_code, TechnologyType.JAVA_SPRING
        )

        assert features is not None
        assert "methods" in features
        assert "classes" in features
        assert "business_logic" in features

    def test_calculate_structural_similarity(self, sample_python_code, sample_java_code):
        """Test calculating structural similarity."""
        comparator = SemanticComparator()

        python_features = comparator.extract_semantic_features(
            sample_python_code, TechnologyType.PYTHON_FLASK
        )
        java_features = comparator.extract_semantic_features(
            sample_java_code, TechnologyType.JAVA_SPRING
        )

        similarity = comparator.calculate_structural_similarity(python_features, java_features)

        assert similarity is not None
        assert "overall_similarity" in similarity
        assert "function_similarity" in similarity
        assert "class_similarity" in similarity
        assert "logic_similarity" in similarity
        assert 0.0 <= similarity["overall_similarity"] <= 1.0

    def test_identify_functional_equivalence(self):
        """Test identifying functional equivalence."""
        comparator = SemanticComparator()

        # Functionally equivalent code in different languages
        python_func = """
        def add_numbers(a, b):
            return a + b
        """

        java_func = """
        public static int addNumbers(int a, int b) {
            return a + b;
        }
        """

        python_features = comparator.extract_semantic_features(
            python_func, TechnologyType.PYTHON_FLASK
        )
        java_features = comparator.extract_semantic_features(java_func, TechnologyType.JAVA_SPRING)

        equivalence = comparator.identify_functional_equivalence(python_features, java_features)

        assert equivalence is not None
        assert "is_equivalent" in equivalence
        assert "confidence" in equivalence
        assert "matching_functions" in equivalence

    def test_analyze_business_logic_preservation(self):
        """Test analyzing business logic preservation."""
        comparator = SemanticComparator()

        source_logic = {
            "business_rules": ["validate_email", "check_password_strength"],
            "workflows": ["user_registration", "login_process"],
            "validations": ["input_validation", "security_checks"],
        }

        target_logic = {
            "business_rules": ["validateEmail", "checkPasswordStrength"],
            "workflows": ["userRegistration", "loginProcess"],
            "validations": ["inputValidation", "securityChecks"],
        }

        preservation = comparator.analyze_business_logic_preservation(source_logic, target_logic)

        assert preservation is not None
        assert "preserved_rules" in preservation
        assert "missing_rules" in preservation
        assert "additional_rules" in preservation
        assert "preservation_score" in preservation

    def test_detect_semantic_discrepancies(self):
        """Test detecting semantic discrepancies."""
        comparator = SemanticComparator()

        source_features = {
            "functions": [
                {
                    "name": "calculate_tax",
                    "parameters": ["amount", "rate"],
                    "returns": "float",
                }
            ],
            "business_logic": ["tax_calculation"],
        }

        target_features = {
            "functions": [{"name": "calculateTax", "parameters": ["amount"], "returns": "double"}],
            "business_logic": ["tax_calculation"],
        }

        discrepancies = comparator.detect_discrepancies(source_features, target_features)

        assert discrepancies is not None
        assert len(discrepancies) > 0
        assert any("parameter" in d["type"] for d in discrepancies)

    def test_generate_mapping_suggestions(self):
        """Test generating mapping suggestions."""
        comparator = SemanticComparator()

        source_elements = ["getUserData", "validateInput", "processOrder"]
        target_elements = ["get_user_data", "validate_input", "process_order"]

        mappings = comparator.generate_mapping_suggestions(source_elements, target_elements)

        assert mappings is not None
        assert len(mappings) == 3
        assert all("confidence" in mapping for mapping in mappings)
        assert all("source" in mapping for mapping in mappings)
        assert all("target" in mapping for mapping in mappings)

    def test_analyze_data_flow_similarity(self):
        """Test analyzing data flow similarity."""
        comparator = SemanticComparator()

        source_flow = {
            "inputs": ["user_input", "database_data"],
            "transformations": ["validation", "processing"],
            "outputs": ["response", "log_entry"],
        }

        target_flow = {
            "inputs": ["userInput", "databaseData"],
            "transformations": ["validation", "processing"],
            "outputs": ["response", "logEntry"],
        }

        flow_similarity = comparator.analyze_data_flow_similarity(source_flow, target_flow)

        assert flow_similarity is not None
        assert "similarity_score" in flow_similarity
        assert "matching_flows" in flow_similarity
        assert "missing_flows" in flow_similarity

    @pytest.mark.asyncio
    async def test_llm_enhanced_comparison(self, mock_llm_service):
        """Test LLM-enhanced semantic comparison."""
        comparator = SemanticComparator(llm_service=mock_llm_service)

        source_features = {
            "functions": ["validate_user"],
            "business_logic": ["authentication"],
        }
        target_features = {
            "functions": ["validateUser"],
            "business_logic": ["authentication"],
        }

        enhanced_comparison = await comparator.llm_enhanced_comparison(
            source_features, target_features
        )

        assert enhanced_comparison is not None
        assert "semantic_similarity" in enhanced_comparison
        assert "functional_equivalence" in enhanced_comparison
        assert "confidence" in enhanced_comparison

        # Verify LLM service was called
        mock_llm_service.analyze_code_semantic_similarity.assert_called()

    def test_calculate_confidence_score(self):
        """Test calculating confidence score for comparisons."""
        comparator = SemanticComparator()

        comparison_results = {
            "structural_similarity": 0.85,
            "functional_equivalence": True,
            "business_logic_preserved": True,
            "discrepancy_count": 2,
        }

        confidence = comparator.calculate_confidence_score(comparison_results)

        assert 0.0 <= confidence <= 1.0
        assert isinstance(confidence, float)

    def test_handle_edge_cases(self):
        """Test handling edge cases in semantic comparison."""
        comparator = SemanticComparator()

        # Empty code
        features_empty = comparator.extract_semantic_features("", TechnologyType.PYTHON_FLASK)
        assert features_empty is not None

        # Invalid syntax
        features_invalid = comparator.extract_semantic_features(
            "invalid syntax {{{", TechnologyType.PYTHON_FLASK
        )
        assert features_invalid is not None
        assert "syntax_errors" in features_invalid

        # Very large code
        large_code = "\n".join([f"def func_{i}(): pass" for i in range(1000)])
        features_large = comparator.extract_semantic_features(
            large_code, TechnologyType.PYTHON_FLASK
        )
        assert features_large is not None


@pytest.mark.unit
class TestSemanticComparatorUtils:
    """Test SemanticComparator utility functions."""

    def test_normalize_identifiers(self):
        """Test normalizing identifiers for comparison."""
        comparator = SemanticComparator()

        # Test camelCase to snake_case
        assert comparator.normalize_identifier("getUserData") == "get_user_data"
        assert comparator.normalize_identifier("validateUserInput") == "validate_user_input"

        # Test snake_case to camelCase
        assert (
            comparator.normalize_identifier("get_user_data", target_style="camelCase")
            == "getUserData"
        )

    def test_calculate_edit_distance(self):
        """Test calculating edit distance between strings."""
        comparator = SemanticComparator()

        distance = comparator.calculate_edit_distance("kitten", "sitting")
        assert distance == 3

        distance = comparator.calculate_edit_distance("saturday", "sunday")
        assert distance == 3

    def test_find_best_matches(self):
        """Test finding best matches between element lists."""
        comparator = SemanticComparator()

        source_list = ["getUserData", "validateInput", "processOrder"]
        target_list = [
            "get_user_data",
            "validate_input",
            "process_payment",
            "process_order",
        ]

        matches = comparator.find_best_matches(source_list, target_list, threshold=0.7)

        assert len(matches) >= 2  # Should match at least getUserData and validateInput
        assert all(match["confidence"] >= 0.7 for match in matches)
