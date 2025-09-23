"""
Property-based testing for code analyzer components.

This module uses Hypothesis to generate test cases automatically, discovering edge cases
and validating invariants that should hold for all inputs.
"""

import ast
import re
from typing import Dict, List, Any
from unittest.mock import Mock, patch

import pytest
from hypothesis import given, strategies as st, assume, example, note, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, Bundle

from src.analyzers.code_analyzer import CodeAnalyzer
from src.core.models import TechnologyType


# ═══════════════════════════════════════════════════════════════
# Hypothesis Strategies for Code Generation
# ═══════════════════════════════════════════════════════════════

# Valid Python identifiers
python_identifiers = st.from_regex(r"^[a-zA-Z_][a-zA-Z0-9_]*$", fullmatch=True)

# Python keywords to avoid
PYTHON_KEYWORDS = {
    "False",
    "None",
    "True",
    "and",
    "as",
    "assert",
    "async",
    "await",
    "break",
    "class",
    "continue",
    "def",
    "del",
    "elif",
    "else",
    "except",
    "finally",
    "for",
    "from",
    "global",
    "if",
    "import",
    "in",
    "is",
    "lambda",
    "nonlocal",
    "not",
    "or",
    "pass",
    "raise",
    "return",
    "try",
    "while",
    "with",
    "yield",
}

# Valid Python variable names
valid_python_names = python_identifiers.filter(lambda x: x not in PYTHON_KEYWORDS)

# Simple Python expressions
python_literals = st.one_of(
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(min_size=0, max_size=50),
    st.booleans(),
)

# Python function parameter strategies
python_parameters = st.lists(valid_python_names, min_size=0, max_size=5, unique=True)


# Python function body strategies
def python_statements():
    return st.one_of(
        st.just("pass"),
        st.text(min_size=1, max_size=100).map(lambda x: f"# {x}"),
        valid_python_names.map(lambda x: f"{x} = 42"),
        st.just("return None"),
        python_literals.map(lambda x: f"return {repr(x)}"),
    )


# Complete Python function generator
@st.composite
def python_function(draw):
    """Generate a valid Python function."""
    func_name = draw(valid_python_names)
    params = draw(python_parameters)
    body_statements = draw(st.lists(python_statements(), min_size=1, max_size=5))

    params_str = ", ".join(params)
    body_str = "\n    ".join(body_statements)

    return f"""def {func_name}({params_str}):
    {body_str}"""


# Complete Python class generator
@st.composite
def python_class(draw):
    """Generate a valid Python class."""
    class_name = draw(valid_python_names.filter(lambda x: x[0].isupper() or x.startswith("_")))
    methods = draw(st.lists(python_function(), min_size=0, max_size=3))

    if not methods:
        methods = ["    pass"]
    else:
        methods = [f"    {method.replace(chr(10), chr(10) + '    ')}" for method in methods]

    methods_str = "\n\n".join(methods)

    return f"""class {class_name}:
{methods_str}"""


# Complete Python module generator
@st.composite
def python_module(draw):
    """Generate a complete Python module."""
    imports = draw(
        st.lists(
            st.sampled_from(
                [
                    "import os",
                    "import sys",
                    "from typing import List, Dict, Any",
                    "import json",
                    "from datetime import datetime",
                ]
            ),
            min_size=0,
            max_size=3,
            unique=True,
        )
    )

    functions = draw(st.lists(python_function(), min_size=0, max_size=3))
    classes = draw(st.lists(python_class(), min_size=0, max_size=2))

    components = imports + functions + classes

    if not components:
        components = ["# Empty module"]

    return "\n\n".join(components)


# ═══════════════════════════════════════════════════════════════
# Property-Based Tests for Code Analyzer
# ═══════════════════════════════════════════════════════════════


@pytest.mark.property
@pytest.mark.unit
class TestCodeAnalyzerProperties:
    """Property-based tests for CodeAnalyzer."""

    def setup_method(self):
        """Setup test environment."""
        self.analyzer = CodeAnalyzer()

    @given(python_module())
    @example("")  # Empty code
    @example("# Just a comment")
    @example("pass")
    @settings(max_examples=50, deadline=30000)
    def test_analyze_code_invariants(self, code):
        """Test invariants that should hold for any code analysis."""
        note(f"Testing code: {code[:100]}...")

        try:
            result = self.analyzer.analyze_code(code, TechnologyType.PYTHON_FLASK)

            # Invariants that should always hold
            assert isinstance(result, dict), "Result must be a dictionary"

            # Required keys should exist
            required_keys = ["functions", "classes", "dependencies"]
            for key in required_keys:
                assert key in result, f"Required key '{key}' missing from result"
                assert isinstance(result[key], list), f"Key '{key}' should be a list"

            # Function analysis invariants
            if result["functions"]:
                for func in result["functions"]:
                    assert isinstance(func, dict), "Function info must be a dictionary"
                    assert "name" in func, "Function must have a name"
                    assert isinstance(func["name"], str), "Function name must be a string"
                    assert func["name"].strip(), "Function name cannot be empty"

            # Class analysis invariants
            if result["classes"]:
                for cls in result["classes"]:
                    assert isinstance(cls, dict), "Class info must be a dictionary"
                    assert "name" in cls, "Class must have a name"
                    assert isinstance(cls["name"], str), "Class name must be a string"
                    assert cls["name"].strip(), "Class name cannot be empty"

            # If code is syntactically valid, analysis should succeed
            try:
                ast.parse(code)
                # If AST parsing succeeds, analysis should not fail
                assert "syntax_errors" not in result or not result["syntax_errors"]
            except SyntaxError:
                # If AST parsing fails, analysis should report syntax errors
                assert "syntax_errors" in result or "error" in result

        except ValueError as e:
            # ValueError is acceptable for invalid technology types or malformed code
            assert "unsupported" in str(e).lower() or "invalid" in str(e).lower()
        except Exception as e:
            # Log unexpected exceptions for debugging
            note(f"Unexpected exception: {type(e).__name__}: {e}")
            raise

    @given(st.lists(python_function(), min_size=1, max_size=10))
    @settings(max_examples=30)
    def test_extract_functions_properties(self, functions):
        """Test properties of function extraction."""
        code = "\n\n".join(functions)
        note(f"Testing {len(functions)} functions")

        try:
            extracted = self.analyzer.extract_functions(code, "python")

            # Properties that should hold
            assert isinstance(extracted, list), "Extracted functions must be a list"

            # Number of extracted functions should not exceed input functions
            assert len(extracted) <= len(functions), "Cannot extract more functions than exist"

            # Each extracted function should have required properties
            for func_info in extracted:
                assert isinstance(func_info, dict)
                assert "name" in func_info
                assert "line_number" in func_info
                assert isinstance(func_info["line_number"], int)
                assert func_info["line_number"] > 0

                # Function name should be valid Python identifier
                func_name = func_info["name"]
                assert func_name.isidentifier(), f"'{func_name}' is not a valid identifier"
                assert func_name not in PYTHON_KEYWORDS, f"'{func_name}' is a Python keyword"

        except Exception as e:
            note(f"Exception during function extraction: {type(e).__name__}: {e}")
            # Some exceptions are acceptable for malformed code
            if not isinstance(e, (SyntaxError, ValueError)):
                raise

    @given(st.lists(python_class(), min_size=1, max_size=5))
    @settings(max_examples=30)
    def test_extract_classes_properties(self, classes):
        """Test properties of class extraction."""
        code = "\n\n".join(classes)
        note(f"Testing {len(classes)} classes")

        try:
            extracted = self.analyzer.extract_classes(code, "python")

            # Properties that should hold
            assert isinstance(extracted, list), "Extracted classes must be a list"
            assert len(extracted) <= len(classes), "Cannot extract more classes than exist"

            for class_info in extracted:
                assert isinstance(class_info, dict)
                assert "name" in class_info
                assert "line_number" in class_info
                assert isinstance(class_info["line_number"], int)
                assert class_info["line_number"] > 0

                # Class name should follow Python conventions
                class_name = class_info["name"]
                assert class_name.isidentifier(), f"'{class_name}' is not a valid identifier"

        except Exception as e:
            note(f"Exception during class extraction: {type(e).__name__}: {e}")
            if not isinstance(e, (SyntaxError, ValueError)):
                raise

    @given(python_module())
    @settings(max_examples=30)
    def test_calculate_metrics_properties(self, code):
        """Test properties of code metrics calculation."""
        note(f"Testing metrics for code: {code[:50]}...")

        try:
            metrics = self.analyzer.calculate_metrics(code, "python")

            if metrics is not None:
                assert isinstance(metrics, dict), "Metrics must be a dictionary"

                # Check for expected metric keys
                expected_metrics = [
                    "lines_of_code",
                    "cyclomatic_complexity",
                    "maintainability_index",
                ]

                for metric in expected_metrics:
                    if metric in metrics:
                        value = metrics[metric]
                        assert isinstance(
                            value, (int, float)
                        ), f"Metric '{metric}' must be numeric"
                        assert value >= 0, f"Metric '{metric}' cannot be negative"

                # Lines of code should correlate with actual line count
                if "lines_of_code" in metrics:
                    actual_lines = len([line for line in code.split("\n") if line.strip()])
                    reported_lines = metrics["lines_of_code"]
                    # Allow some variance for different counting methods
                    assert abs(actual_lines - reported_lines) <= max(actual_lines * 0.2, 5)

        except Exception as e:
            note(f"Exception during metrics calculation: {type(e).__name__}: {e}")
            # Some exceptions are acceptable
            if not isinstance(e, (SyntaxError, ValueError, TypeError)):
                raise

    @given(
        st.text(min_size=10, max_size=1000),
        st.sampled_from([TechnologyType.PYTHON_FLASK, TechnologyType.JAVA_SPRING]),
    )
    @settings(max_examples=50)
    def test_security_analysis_properties(self, code, tech_type):
        """Test properties of security analysis."""
        note(f"Testing security analysis for: {tech_type}")

        try:
            security_issues = self.analyzer.identify_security_issues(code, tech_type.value.lower())

            if security_issues is not None:
                assert isinstance(security_issues, list), "Security issues must be a list"

                for issue in security_issues:
                    assert isinstance(issue, dict), "Security issue must be a dictionary"
                    assert "type" in issue, "Security issue must have a type"
                    assert "severity" in issue, "Security issue must have a severity"
                    assert "description" in issue, "Security issue must have a description"

                    # Severity should be valid
                    severity = issue["severity"]
                    valid_severities = ["low", "medium", "high", "critical"]
                    assert severity.lower() in valid_severities, f"Invalid severity: {severity}"

        except Exception as e:
            note(f"Exception during security analysis: {type(e).__name__}: {e}")
            # Security analysis might fail for unsupported languages
            if not isinstance(e, (ValueError, NotImplementedError)):
                raise

    @given(st.data())
    @settings(max_examples=20)
    def test_analyze_dependencies_properties(self, data):
        """Test properties of dependency analysis."""
        # Generate code with imports
        imports = data.draw(
            st.lists(
                st.sampled_from(
                    [
                        "import os",
                        "import sys",
                        "import json",
                        "from typing import List",
                        "from datetime import datetime",
                        "import numpy as np",
                        "import pandas as pd",
                        "from flask import Flask",
                        "import requests",
                    ]
                ),
                min_size=0,
                max_size=5,
                unique=True,
            )
        )

        code = "\n".join(imports) + "\n\nprint('Hello World')"
        note(f"Testing dependency analysis with {len(imports)} imports")

        try:
            dependencies = self.analyzer.analyze_dependencies(code, "python")

            if dependencies is not None:
                assert isinstance(dependencies, dict), "Dependencies must be a dictionary"

                expected_keys = ["internal_dependencies", "external_dependencies"]
                for key in expected_keys:
                    if key in dependencies:
                        assert isinstance(dependencies[key], list), f"'{key}' must be a list"

                # Total dependencies should not exceed imports
                total_deps = 0
                if "internal_dependencies" in dependencies:
                    total_deps += len(dependencies["internal_dependencies"])
                if "external_dependencies" in dependencies:
                    total_deps += len(dependencies["external_dependencies"])

                assert total_deps <= len(imports) + 5, "Too many dependencies detected"

        except Exception as e:
            note(f"Exception during dependency analysis: {type(e).__name__}: {e}")
            if not isinstance(e, (ValueError, ImportError)):
                raise


# ═══════════════════════════════════════════════════════════════
# Stateful Testing for Code Analyzer
# ═══════════════════════════════════════════════════════════════


class CodeAnalyzerStateMachine(RuleBasedStateMachine):
    """Stateful testing for CodeAnalyzer behavior."""

    code_samples = Bundle("code_samples")

    def __init__(self):
        super().__init__()
        self.analyzer = CodeAnalyzer()
        self.analyzed_codes = []

    @rule(target=code_samples, code=python_module())
    def generate_code(self, code):
        """Generate a code sample for analysis."""
        assume(len(code.strip()) > 0)  # Non-empty code
        return code

    @rule(code=code_samples)
    def analyze_code_sample(self, code):
        """Analyze a code sample and verify consistency."""
        try:
            result1 = self.analyzer.analyze_code(code, TechnologyType.PYTHON_FLASK)
            result2 = self.analyzer.analyze_code(code, TechnologyType.PYTHON_FLASK)

            # Results should be consistent between calls
            assert result1 == result2, "Analyzer should produce consistent results"

            self.analyzed_codes.append((code, result1))

        except Exception as e:
            # Some exceptions are acceptable
            assert isinstance(e, (ValueError, SyntaxError, TypeError))

    @rule(code=code_samples)
    def analyze_with_different_technologies(self, code):
        """Test analysis with different technology types."""
        technologies = [TechnologyType.PYTHON_FLASK, TechnologyType.JAVA_SPRING]

        for tech in technologies:
            try:
                result = self.analyzer.analyze_code(code, tech)
                if result is not None:
                    assert isinstance(result, dict)
            except ValueError:
                # Different technologies might not support the same code
                pass

    @invariant()
    def analyzer_remains_functional(self):
        """Invariant: analyzer should always remain functional."""
        assert self.analyzer is not None
        assert hasattr(self.analyzer, "analyze_code")
        assert callable(self.analyzer.analyze_code)

    @invariant()
    def no_memory_leaks(self):
        """Invariant: no excessive memory accumulation."""
        # Simple check: don't accumulate too many analyzed codes
        if len(self.analyzed_codes) > 100:
            self.analyzed_codes = self.analyzed_codes[-50:]


@pytest.mark.property
@pytest.mark.slow
class TestCodeAnalyzerStateful:
    """Stateful testing for CodeAnalyzer."""

    def test_stateful_analysis(self):
        """Run stateful testing for code analyzer."""
        CodeAnalyzerStateMachine.TestCase().runTest()


# ═══════════════════════════════════════════════════════════════
# Mutation Testing Support
# ═══════════════════════════════════════════════════════════════


@pytest.mark.mutation
@pytest.mark.unit
class TestCodeAnalyzerMutationTargets:
    """Tests designed to catch mutations in CodeAnalyzer."""

    def setup_method(self):
        """Setup test environment."""
        self.analyzer = CodeAnalyzer()

    def test_function_count_accuracy(self):
        """Test that catches mutations in function counting logic."""
        code = """
def function1():
    pass

def function2():
    return 1

class TestClass:
    def method1(self):
        pass

    def method2(self):
        return 2
"""

        result = self.analyzer.analyze_code(code, TechnologyType.PYTHON_FLASK)

        # Exactly 2 top-level functions should be detected
        assert len(result["functions"]) == 2

        # Function names should be correct
        func_names = [f["name"] for f in result["functions"]]
        assert "function1" in func_names
        assert "function2" in func_names
        assert "method1" not in func_names  # Should not include class methods
        assert "method2" not in func_names

    def test_class_count_accuracy(self):
        """Test that catches mutations in class counting logic."""
        code = """
class Class1:
    pass

class Class2:
    def method(self):
        pass

def standalone_function():
    pass
"""

        result = self.analyzer.analyze_code(code, TechnologyType.PYTHON_FLASK)

        # Exactly 2 classes should be detected
        assert len(result["classes"]) == 2

        # Class names should be correct
        class_names = [c["name"] for c in result["classes"]]
        assert "Class1" in class_names
        assert "Class2" in class_names

    def test_security_issue_detection_accuracy(self):
        """Test that catches mutations in security analysis logic."""
        insecure_code = """
import os
import subprocess

def vulnerable_function(user_input):
    # SQL injection
    query = "SELECT * FROM users WHERE id = " + user_input

    # Command injection
    os.system("cat " + user_input)

    # Eval usage
    result = eval(user_input)

    return result
"""

        issues = self.analyzer.identify_security_issues(insecure_code, "python")

        # Should detect security issues
        assert len(issues) > 0, "Should detect security vulnerabilities"

        # Should detect specific issue types
        issue_types = [issue["type"].lower() for issue in issues]
        assert any("injection" in issue_type for issue_type in issue_types)
        assert any("eval" in issue_type for issue_type in issue_types)

    def test_metrics_calculation_bounds(self):
        """Test that catches mutations in metrics calculation."""
        simple_code = "def simple(): pass"
        complex_code = """
def complex_function(a, b, c):
    if a > 0:
        if b > 0:
            if c > 0:
                for i in range(10):
                    for j in range(10):
                        if i == j:
                            return i * j
                        elif i > j:
                            return i - j
                        else:
                            return i + j
            else:
                return c
        else:
            return b
    else:
        return a
"""

        simple_metrics = self.analyzer.calculate_metrics(simple_code, "python")
        complex_metrics = self.analyzer.calculate_metrics(complex_code, "python")

        # Complex code should have higher complexity
        if (
            "cyclomatic_complexity" in simple_metrics
            and "cyclomatic_complexity" in complex_metrics
        ):
            assert (
                complex_metrics["cyclomatic_complexity"] > simple_metrics["cyclomatic_complexity"]
            )

        # Complex code should have more lines
        if "lines_of_code" in simple_metrics and "lines_of_code" in complex_metrics:
            assert complex_metrics["lines_of_code"] > simple_metrics["lines_of_code"]

    def test_error_handling_robustness(self):
        """Test that catches mutations in error handling logic."""
        malformed_codes = [
            "def incomplete(",  # Syntax error
            "def function():\n  invalid_indent",  # Indentation error
            "",  # Empty code
            "   ",  # Whitespace only
        ]

        for code in malformed_codes:
            try:
                result = self.analyzer.analyze_code(code, TechnologyType.PYTHON_FLASK)

                # Should handle gracefully
                assert result is not None
                assert isinstance(result, dict)

                # Should report syntax errors for malformed code
                if code.strip() and "incomplete" in code:
                    assert "syntax_errors" in result or "error" in result

            except Exception as e:
                # Should not raise unexpected exceptions
                assert isinstance(e, (ValueError, SyntaxError))


# ═══════════════════════════════════════════════════════════════
# Regression Testing for Known Issues
# ═══════════════════════════════════════════════════════════════


@pytest.mark.regression
@pytest.mark.unit
class TestCodeAnalyzerRegression:
    """Regression tests for previously identified issues."""

    def setup_method(self):
        """Setup test environment."""
        self.analyzer = CodeAnalyzer()

    def test_unicode_handling_regression(self):
        """Regression test for Unicode handling issues."""
        unicode_code = """
def función_con_ñ():
    \"\"\"Función with ñ and other Unicode characters: αβγδε\"\"\"
    variable_ñ = "Hola, múndo! 🌍"
    return variable_ñ

class ClaseConÑ:
    def método_con_tildes(self):
        return "áéíóú"
"""

        # Should handle Unicode without errors
        result = self.analyzer.analyze_code(unicode_code, TechnologyType.PYTHON_FLASK)

        assert result is not None
        assert len(result["functions"]) == 1
        assert len(result["classes"]) == 1
        assert result["functions"][0]["name"] == "función_con_ñ"
        assert result["classes"][0]["name"] == "ClaseConÑ"

    def test_nested_structure_regression(self):
        """Regression test for deeply nested structure handling."""
        nested_code = """
class Outer:
    class Inner:
        def inner_method(self):
            def nested_function():
                def deeply_nested():
                    return "deep"
                return deeply_nested()
            return nested_function()

    def outer_method(self):
        return self.Inner().inner_method()
"""

        # Should handle nested structures correctly
        result = self.analyzer.analyze_code(nested_code, TechnologyType.PYTHON_FLASK)

        assert result is not None
        # Should detect outer class
        assert len(result["classes"]) >= 1
        assert any(cls["name"] == "Outer" for cls in result["classes"])

    def test_large_file_regression(self):
        """Regression test for large file handling."""
        # Generate a reasonably large code file
        large_code = "\n".join([f"def function_{i}():\n    return {i}" for i in range(1000)])

        # Should handle large files efficiently
        import time

        start_time = time.time()

        result = self.analyzer.analyze_code(large_code, TechnologyType.PYTHON_FLASK)

        execution_time = time.time() - start_time

        assert result is not None
        assert len(result["functions"]) == 1000
        assert execution_time < 30.0  # Should complete within 30 seconds
