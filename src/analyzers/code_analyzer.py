"""
Code analyzer for extracting features from source code files.

Implements analysis of code files to extract UI elements, backend functions,
data structures, and API endpoints using LLM-based analysis.
"""

import ast
import os
import re
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from ..core.models import (
    AbstractRepresentation,
    BackendFunction,
    DataField,
    InputData,
    InputType,
    TechnologyContext,
    UIElement,
    ValidationScope,
)
from .base import (
    BaseAnalyzer,
    ExtractionError,
    InvalidInputError,
    UnsupportedScopeError,
)


class CodeAnalyzer(BaseAnalyzer):
    """Analyzer for extracting features from source code."""

    def __init__(self, technology_context: TechnologyContext):
        """Initialize code analyzer."""
        super().__init__(technology_context)
        self.supported_scopes = [
            ValidationScope.BACKEND_FUNCTIONALITY,
            ValidationScope.DATA_STRUCTURE,
            ValidationScope.API_ENDPOINTS,
            ValidationScope.BUSINESS_LOGIC,
            ValidationScope.FULL_SYSTEM,
        ]

        # Add UI support for frontend technologies
        if self._is_frontend_tech():
            self.supported_scopes.append(ValidationScope.UI_LAYOUT)

    def _is_frontend_tech(self) -> bool:
        """Check if technology context is frontend-focused."""
        frontend_techs = [
            "javascript-react",
            "javascript-vue",
            "javascript-angular",
            "typescript-react",
            "typescript-vue",
            "typescript-angular",
        ]
        return self.technology_context.type.value in frontend_techs

    async def analyze(
        self, input_data: InputData, scope: ValidationScope
    ) -> AbstractRepresentation:
        """Analyze code files and extract abstract representation."""
        if not self.supports_scope(scope):
            raise UnsupportedScopeError(f"Scope {scope.value} not supported")

        if input_data.type not in [InputType.CODE_FILES, InputType.HYBRID]:
            raise InvalidInputError("CodeAnalyzer requires code files")

        if not input_data.files:
            raise InvalidInputError("No code files provided")

        representation = AbstractRepresentation()

        try:
            # Process each file
            for file_path in input_data.files:
                if not os.path.exists(file_path):
                    continue

                file_analysis = await self._analyze_file(file_path, scope)
                self._merge_analysis(representation, file_analysis)

            return representation

        except Exception as e:
            raise ExtractionError(f"Failed to analyze code: {str(e)}")

    async def _analyze_file(
        self, file_path: str, scope: ValidationScope
    ) -> AbstractRepresentation:
        """Analyze a single code file."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == ".py":
            return await self._analyze_python_file(content, file_path, scope)
        elif file_ext in [".js", ".jsx", ".ts", ".tsx"]:
            return await self._analyze_javascript_file(content, file_path, scope)
        elif file_ext in [".java"]:
            return await self._analyze_java_file(content, file_path, scope)
        elif file_ext in [".cs"]:
            return await self._analyze_csharp_file(content, file_path, scope)
        elif file_ext in [".php"]:
            return await self._analyze_php_file(content, file_path, scope)
        elif file_ext in [".html", ".htm"]:
            return await self._analyze_html_file(content, file_path, scope)
        else:
            # Generic text analysis using LLM
            return await self._analyze_generic_file(content, file_path, scope)

    async def _analyze_python_file(
        self, content: str, file_path: str, scope: ValidationScope
    ) -> AbstractRepresentation:
        """Analyze Python file using AST and pattern matching."""
        representation = AbstractRepresentation()

        try:
            tree = ast.parse(content)

            # Extract classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func = self._extract_python_function(node, content)
                    if func:
                        representation.backend_functions.append(func)

                elif isinstance(node, ast.ClassDef):
                    # Extract data fields from class
                    fields = self._extract_python_class_fields(node)
                    representation.data_fields.extend(fields)

            # Extract Flask/Django routes if applicable
            if "flask" in content.lower() or "django" in content.lower():
                endpoints = self._extract_python_endpoints(content)
                representation.api_endpoints.extend(endpoints)

        except SyntaxError:
            # Fall back to regex-based analysis
            representation = await self._analyze_generic_file(content, file_path, scope)

        return representation

    def _extract_python_function(
        self, node: ast.FunctionDef, content: str
    ) -> Optional[BackendFunction]:
        """Extract function information from AST node."""
        try:
            # Get function parameters
            params = [arg.arg for arg in node.args.args if arg.arg != "self"]

            # Try to extract docstring for logic summary
            logic_summary = None
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
            ):
                logic_summary = node.body[0].value.value

            # Check for Flask route decorators
            endpoint = None
            http_method = None
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if hasattr(decorator.func, "attr") and decorator.func.attr == "route":
                        if decorator.args:
                            endpoint = (
                                decorator.args[0].value
                                if hasattr(decorator.args[0], "value")
                                else None
                            )

                    # Check for HTTP method decorators
                    if hasattr(decorator.func, "id"):
                        method_name = decorator.func.id.upper()
                        if method_name in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                            http_method = method_name

            return BackendFunction(
                name=node.name,
                parameters=params,
                logic_summary=logic_summary,
                endpoint=endpoint,
                http_method=http_method,
            )
        except Exception:
            return None

    def _extract_python_class_fields(self, node: ast.ClassDef) -> List[DataField]:
        """Extract data fields from Python class."""
        fields = []

        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                # Type annotated fields
                field_name = item.target.id
                field_type = "unknown"

                if isinstance(item.annotation, ast.Name):
                    field_type = item.annotation.id
                elif isinstance(item.annotation, ast.Constant):
                    field_type = str(item.annotation.value)

                fields.append(DataField(name=field_name, type=field_type))

        return fields

    def _extract_python_endpoints(self, content: str) -> List[Dict[str, Any]]:
        """Extract API endpoints from Python web frameworks."""
        endpoints = []

        # Flask route patterns
        flask_routes = re.findall(
            r'@app\.route\(["\']([^"\']+)["\'](?:.*?methods=\[(.*?)\])?\)', content
        )
        for route, methods in flask_routes:
            methods_list = (
                [m.strip().strip("'\"") for m in methods.split(",")] if methods else ["GET"]
            )
            endpoints.append({"path": route, "methods": methods_list, "framework": "flask"})

        # Django URL patterns (basic)
        django_patterns = re.findall(r'path\(["\']([^"\']+)["\']', content)
        for pattern in django_patterns:
            endpoints.append(
                {
                    "path": pattern,
                    "methods": ["GET", "POST"],  # Default assumption
                    "framework": "django",
                }
            )

        return endpoints

    async def _analyze_javascript_file(
        self, content: str, file_path: str, scope: ValidationScope
    ) -> AbstractRepresentation:
        """Analyze JavaScript/TypeScript file."""
        representation = AbstractRepresentation()

        # Extract React components if applicable
        if "react" in content.lower() or file_path.endswith((".jsx", ".tsx")):
            ui_elements = self._extract_react_elements(content)
            representation.ui_elements.extend(ui_elements)

        # Extract functions
        functions = self._extract_js_functions(content)
        representation.backend_functions.extend(functions)

        # Extract API calls
        api_calls = self._extract_api_calls(content)
        representation.api_endpoints.extend(api_calls)

        return representation

    def _extract_react_elements(self, content: str) -> List[UIElement]:
        """Extract UI elements from React components."""
        elements = []

        # Extract JSX elements
        jsx_patterns = [
            r'<input[^>]*(?:id=["\']([^"\']+)["\'])?[^>]*'
            r'(?:placeholder=["\']([^"\']+)["\'])?[^>]*/>',
            r'<button[^>]*(?:id=["\']([^"\']+)["\'])?[^>]*>([^<]+)</button>',
            r'<label[^>]*(?:htmlFor=["\']([^"\']+)["\'])?[^>]*>([^<]+)</label>',
        ]

        for pattern in jsx_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                element_id = groups[0] if len(groups) > 0 else None
                element_text = groups[1] if len(groups) > 1 else None

                if "input" in match.group().lower():
                    element_type = "input"
                elif "button" in match.group().lower():
                    element_type = "button"
                elif "label" in match.group().lower():
                    element_type = "label"
                else:
                    element_type = "unknown"

                elements.append(UIElement(type=element_type, id=element_id, text=element_text))

        return elements

    def _extract_js_functions(self, content: str) -> List[BackendFunction]:
        """Extract JavaScript functions."""
        functions = []

        # Function declarations and arrow functions
        patterns = [
            r"function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)",
            r"const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\(([^)]*)\)\s*=>",
            r"([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*\(([^)]*)\)\s*=>",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                func_name = match.group(1)
                params_str = match.group(2) if len(match.groups()) > 1 else ""
                params = [p.strip() for p in params_str.split(",") if p.strip()]

                functions.append(BackendFunction(name=func_name, parameters=params))

        return functions

    def _extract_api_calls(self, content: str) -> List[Dict[str, Any]]:
        """Extract API calls from JavaScript code."""
        api_calls = []

        # Fetch API calls
        fetch_patterns = [
            r'fetch\(["\']([^"\']+)["\'](?:.*?method:\s*["\']([^"\']+)["\'])?',
            r'axios\.([a-z]+)\(["\']([^"\']+)["\']',
            r'\.([get|post|put|delete]+)\(["\']([^"\']+)["\']',
        ]

        for pattern in fetch_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    if "axios" in match.group():
                        method = groups[0].upper()
                        url = groups[1]
                    else:
                        url = groups[0]
                        method = groups[1].upper() if groups[1] else "GET"

                    api_calls.append({"url": url, "method": method, "type": "client_call"})

        return api_calls

    async def _analyze_java_file(
        self, content: str, file_path: str, scope: ValidationScope
    ) -> AbstractRepresentation:
        """Analyze Java file."""
        # TODO: Implement Java-specific analysis
        return await self._analyze_generic_file(content, file_path, scope)

    async def _analyze_csharp_file(
        self, content: str, file_path: str, scope: ValidationScope
    ) -> AbstractRepresentation:
        """Analyze C# file."""
        # TODO: Implement C#-specific analysis
        return await self._analyze_generic_file(content, file_path, scope)

    async def _analyze_php_file(
        self, content: str, file_path: str, scope: ValidationScope
    ) -> AbstractRepresentation:
        """Analyze PHP file."""
        # TODO: Implement PHP-specific analysis
        return await self._analyze_generic_file(content, file_path, scope)

    async def _analyze_html_file(
        self, content: str, file_path: str, scope: ValidationScope
    ) -> AbstractRepresentation:
        """Analyze HTML file for UI elements."""
        representation = AbstractRepresentation()

        if scope == ValidationScope.UI_LAYOUT:
            # Extract form elements
            ui_elements = self._extract_html_elements(content)
            representation.ui_elements.extend(ui_elements)

        return representation

    def _extract_html_elements(self, content: str) -> List[UIElement]:
        """Extract UI elements from HTML."""
        elements = []

        # Common HTML form elements
        patterns = {
            "input": (
                r'<input[^>]*(?:id=["\']([^"\']+)["\'])?[^>]*'
                r'(?:placeholder=["\']([^"\']+)["\'])?[^>]*'
                r'(?:type=["\']([^"\']+)["\'])?[^>]*>'
            ),
            "button": r'<button[^>]*(?:id=["\']([^"\']+)["\'])?[^>]*>([^<]+)</button>',
            "label": r'<label[^>]*(?:for=["\']([^"\']+)["\'])?[^>]*>([^<]+)</label>',
            "select": r'<select[^>]*(?:id=["\']([^"\']+)["\'])?[^>]*>',
            "textarea": (
                r'<textarea[^>]*(?:id=["\']([^"\']+)["\'])?[^>]*'
                r'(?:placeholder=["\']([^"\']+)["\'])?[^>]*>'
            ),
        }

        for element_type, pattern in patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                element_id = groups[0] if len(groups) > 0 else None
                element_text = groups[1] if len(groups) > 1 else None

                elements.append(UIElement(type=element_type, id=element_id, text=element_text))

        return elements

    async def _analyze_generic_file(
        self, content: str, file_path: str, scope: ValidationScope
    ) -> AbstractRepresentation:
        """Generic file analysis using LLM (placeholder for now)."""
        # TODO: Implement LLM-based analysis for unsupported file types
        return AbstractRepresentation(
            metadata={
                "file_path": file_path,
                "analysis_method": "generic",
                "content_length": len(content),
            }
        )

    def _merge_analysis(self, target: AbstractRepresentation, source: AbstractRepresentation):
        """Merge analysis results from multiple files."""
        target.ui_elements.extend(source.ui_elements)
        target.backend_functions.extend(source.backend_functions)
        target.data_fields.extend(source.data_fields)
        target.api_endpoints.extend(source.api_endpoints)
        target.metadata.update(source.metadata)

    def supports_scope(self, scope: ValidationScope) -> bool:
        """Check if analyzer supports the given validation scope."""
        return scope in self.supported_scopes
