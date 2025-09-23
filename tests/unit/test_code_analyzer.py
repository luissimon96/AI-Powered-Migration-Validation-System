"""Unit tests for code analyzer.
"""


import pytest

from src.analyzers.code_analyzer import CodeAnalyzer
from src.core.models import TechnologyType


@pytest.mark.unit
class TestCodeAnalyzer:
    """Test CodeAnalyzer component."""

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = CodeAnalyzer()
        assert analyzer is not None

    def test_analyze_python_code(self, sample_python_code):
        """Test analyzing Python code."""
        analyzer = CodeAnalyzer()

        analysis = analyzer.analyze_code(
            code=sample_python_code,
            technology=TechnologyType.PYTHON_FLASK,
        )

        assert analysis is not None
        assert "ast_analysis" in analysis
        assert "functions" in analysis
        assert "classes" in analysis
        assert "dependencies" in analysis

    def test_analyze_java_code(self, sample_java_code):
        """Test analyzing Java code."""
        analyzer = CodeAnalyzer()

        analysis = analyzer.analyze_code(
            code=sample_java_code,
            technology=TechnologyType.JAVA_SPRING,
        )

        assert analysis is not None
        assert "structure" in analysis
        assert "methods" in analysis
        assert "classes" in analysis

    def test_extract_functions_python(self, sample_python_code):
        """Test extracting functions from Python code."""
        analyzer = CodeAnalyzer()

        functions = analyzer.extract_functions(sample_python_code, "python")

        assert len(functions) > 0
        assert "validate_user_input" in [f["name"] for f in functions]

        # Check function details
        validate_func = next(f for f in functions if f["name"] == "validate_user_input")
        assert "parameters" in validate_func
        assert "docstring" in validate_func
        assert "line_number" in validate_func

    def test_extract_classes_python(self, sample_python_code):
        """Test extracting classes from Python code."""
        analyzer = CodeAnalyzer()

        classes = analyzer.extract_classes(sample_python_code, "python")

        assert len(classes) > 0
        assert "UserManager" in [c["name"] for c in classes]

        # Check class details
        user_manager = next(c for c in classes if c["name"] == "UserManager")
        assert "methods" in user_manager
        assert "attributes" in user_manager
        assert "line_number" in user_manager

    def test_analyze_control_flow(self, sample_python_code):
        """Test analyzing control flow."""
        analyzer = CodeAnalyzer()

        control_flow = analyzer.analyze_control_flow(sample_python_code, "python")

        assert control_flow is not None
        assert "conditional_statements" in control_flow
        assert "loops" in control_flow
        assert "exception_handling" in control_flow

    def test_detect_patterns(self, sample_python_code):
        """Test detecting code patterns."""
        analyzer = CodeAnalyzer()

        patterns = analyzer.detect_patterns(
            sample_python_code, TechnologyType.PYTHON_FLASK
        )

        assert patterns is not None
        assert "design_patterns" in patterns
        assert "anti_patterns" in patterns
        assert "best_practices" in patterns

    def test_calculate_metrics(self, sample_python_code):
        """Test calculating code metrics."""
        analyzer = CodeAnalyzer()

        metrics = analyzer.calculate_metrics(sample_python_code, "python")

        assert metrics is not None
        assert "cyclomatic_complexity" in metrics
        assert "maintainability_index" in metrics
        assert "lines_of_code" in metrics
        assert "code_duplication" in metrics

    def test_analyze_dependencies(self, sample_python_code):
        """Test analyzing dependencies."""
        analyzer = CodeAnalyzer()

        dependencies = analyzer.analyze_dependencies(sample_python_code, "python")

        assert dependencies is not None
        assert "internal_dependencies" in dependencies
        assert "external_dependencies" in dependencies
        assert "circular_dependencies" in dependencies

    def test_identify_security_issues(self):
        """Test identifying security issues."""
        analyzer = CodeAnalyzer()

        insecure_code = """
        import os
        import subprocess

        def dangerous_function(user_input):
            # SQL injection vulnerability
            query = "SELECT * FROM users WHERE id = " + user_input

            # Command injection vulnerability
            os.system("cat " + user_input)

            # Unsafe eval
            eval(user_input)

            return query
        """

        security_issues = analyzer.identify_security_issues(insecure_code, "python")

        assert len(security_issues) > 0
        assert any("injection" in issue["type"].lower() for issue in security_issues)
        assert any("eval" in issue["description"].lower() for issue in security_issues)

    def test_analyze_performance_bottlenecks(self):
        """Test analyzing performance bottlenecks."""
        analyzer = CodeAnalyzer()

        slow_code = """
        def inefficient_function(data):
            result = []
            for i in range(len(data)):
                for j in range(len(data)):
                    if data[i] == data[j]:
                        result.append(data[i])
            return result

        def nested_loops():
            for i in range(1000):
                for j in range(1000):
                    for k in range(100):
                        pass
        """

        bottlenecks = analyzer.analyze_performance(slow_code, "python")

        assert bottlenecks is not None
        assert "algorithmic_complexity" in bottlenecks
        assert "nested_loops" in bottlenecks
        assert "optimization_suggestions" in bottlenecks

    def test_compare_code_structures(self, sample_python_code, sample_java_code):
        """Test comparing code structures."""
        analyzer = CodeAnalyzer()

        python_structure = analyzer.analyze_code(
            sample_python_code, TechnologyType.PYTHON_FLASK
        )
        java_structure = analyzer.analyze_code(
            sample_java_code, TechnologyType.JAVA_SPRING
        )

        comparison = analyzer.compare_structures(python_structure, java_structure)

        assert comparison is not None
        assert "structural_similarity" in comparison
        assert "function_mapping" in comparison
        assert "class_mapping" in comparison
        assert "differences" in comparison

    def test_extract_business_logic(self, sample_python_code):
        """Test extracting business logic."""
        analyzer = CodeAnalyzer()

        business_logic = analyzer.extract_business_logic(sample_python_code, "python")

        assert business_logic is not None
        assert "business_rules" in business_logic
        assert "validation_logic" in business_logic
        assert "core_workflows" in business_logic

    def test_analyze_error_handling(self, sample_python_code):
        """Test analyzing error handling."""
        analyzer = CodeAnalyzer()

        error_handling = analyzer.analyze_error_handling(sample_python_code, "python")

        assert error_handling is not None
        assert "exception_types" in error_handling
        assert "error_propagation" in error_handling
        assert "missing_error_handling" in error_handling

    def test_analyze_unsupported_language(self):
        """Test analyzing unsupported programming language."""
        analyzer = CodeAnalyzer()

        with pytest.raises(ValueError, match="Unsupported language"):
            analyzer.analyze_code("some code", TechnologyType.REACT)

    def test_analyze_malformed_code(self):
        """Test analyzing malformed code."""
        analyzer = CodeAnalyzer()

        malformed_code = """
        def incomplete_function(
            # Missing closing parenthesis and body
        """

        analysis = analyzer.analyze_code(malformed_code, TechnologyType.PYTHON_FLASK)

        assert analysis is not None
        assert "syntax_errors" in analysis
        assert len(analysis["syntax_errors"]) > 0

    def test_analyze_empty_code(self):
        """Test analyzing empty code."""
        analyzer = CodeAnalyzer()

        analysis = analyzer.analyze_code("", TechnologyType.PYTHON_FLASK)

        assert analysis is not None
        assert analysis["functions"] == []
        assert analysis["classes"] == []


@pytest.mark.unit
class TestCodeAnalyzerPerformance:
    """Test CodeAnalyzer performance characteristics."""

    def test_large_file_analysis(self):
        """Test analyzing large code files."""
        analyzer = CodeAnalyzer()

        # Generate large code file
        large_code = "\n".join(
            [f"def function_{i}():\n    return {i}" for i in range(1000)]
        )

        import time

        start_time = time.time()

        analysis = analyzer.analyze_code(large_code, TechnologyType.PYTHON_FLASK)

        execution_time = time.time() - start_time

        assert analysis is not None
        assert len(analysis["functions"]) == 1000
        assert execution_time < 10.0  # Should complete within 10 seconds

    def test_memory_usage(self):
        """Test memory usage during analysis."""
        analyzer = CodeAnalyzer()

        # This test would ideally use memory profiling
        # For now, just ensure no memory leaks in basic usage
        for i in range(100):
            analyzer.analyze_code(f"def test_{i}(): pass", TechnologyType.PYTHON_FLASK)

        # If we reach here without memory errors, basic test passes
        assert True
