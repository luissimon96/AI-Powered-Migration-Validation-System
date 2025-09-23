"""Visual analyzer for extracting features from screenshots and images.

Implements analysis of UI screenshots using computer vision and multimodal LLMs
to extract UI elements, layout information, visual structure, and element relationships.
"""

import base64
import io
import os
from dataclasses import asdict
from typing import Any, Dict, List

from PIL import Image

from ..core.models import (AbstractRepresentation, InputData, InputType,
                           TechnologyContext, UIElement, ValidationScope)
from ..services.llm_service import AnalysisType, LLMService, create_llm_service
from .base import (BaseAnalyzer, ExtractionError, InvalidInputError,
                   UnsupportedScopeError)


class VisualAnalyzer(BaseAnalyzer):
    """Analyzer for extracting features from screenshots and images."""

    def __init__(self, technology_context: TechnologyContext):
        """Initialize visual analyzer."""
        super().__init__(technology_context)
        self.supported_scopes = [ValidationScope.UI_LAYOUT, ValidationScope.FULL_SYSTEM]
        self.supported_image_formats = [".png", ".jpg", ".jpeg", ".bmp", ".gif"]
        self.llm_service: LLMService = create_llm_service(
            providers="openai,google,anthropic")

    async def analyze(
        self, input_data: InputData, scope: ValidationScope,
    ) -> AbstractRepresentation:
        """Analyze screenshots and extract UI representation."""
        if not self.supports_scope(scope):
            raise UnsupportedScopeError(f"Scope {scope.value} not supported")

        if input_data.type not in [InputType.SCREENSHOTS, InputType.HYBRID]:
            raise InvalidInputError("VisualAnalyzer requires screenshots")

        if not input_data.screenshots:
            raise InvalidInputError("No screenshots provided")

        representation = AbstractRepresentation()

        try:
            # Process each screenshot
            for image_path in input_data.screenshots:
                if not os.path.exists(image_path):
                    continue

                if not self._is_supported_image(image_path):
                    continue

                image_analysis = await self._analyze_screenshot(image_path, scope)
                self._merge_visual_analysis(representation, image_analysis)

            # Enhanced analysis with element relationships
            if representation.ui_elements:
                representation = await self._enhance_with_relationship_analysis(
                    representation, scope,
                )

            return representation

        except Exception as e:
            raise ExtractionError(f"Failed to analyze screenshots: {e!s}")

    def _is_supported_image(self, file_path: str) -> bool:
        """Check if image format is supported."""
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.supported_image_formats

    async def _analyze_screenshot(
        self, image_path: str, scope: ValidationScope,
    ) -> AbstractRepresentation:
        """Analyze a single screenshot with comprehensive UI element extraction."""
        try:
            # Load and validate image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Get image metadata
                width, height = img.size

                # Extract UI elements using multimodal LLM
                ui_elements = await self._extract_ui_elements_with_llm(img, image_path)

                # Fallback to basic computer vision if LLM fails
                if not ui_elements:
                    ui_elements = self._basic_cv_analysis(img, image_path)

                # Create representation
                representation = AbstractRepresentation(
                    ui_elements=ui_elements,
                    metadata={
                        "image_path": image_path,
                        "image_size": {"width": width, "height": height},
                        "analysis_method": "multimodal_llm",
                        "elements_count": len(ui_elements),
                    },
                )

                return representation

        except Exception as e:
            raise ExtractionError(f"Failed to analyze image {image_path}: {e!s}")

    async def _extract_ui_elements_with_llm(
        self, image: Image.Image, image_path: str,
    ) -> List[UIElement]:
        """Extract UI elements using advanced multimodal LLM analysis."""
        elements = []

        try:
            # Convert image to base64 for LLM processing
            image_base64 = self._image_to_base64(image)

            # Use structured analysis for UI element extraction
            analysis_result = await self.llm_service.structured_analysis(
                AnalysisType.UI_ELEMENT_EXTRACTION,
                {
                    "additional_context": f"Screenshot from {os.path.basename(image_path)}. "
                    "Focus on interactive elements, form controls, navigation, and content areas.",
                },
            )

            # Convert LLM response to UIElement objects
            if analysis_result.result.get("elements"):
                for elem_data in analysis_result.result["elements"]:
                    element = UIElement(
                        type=elem_data.get("type", "unknown"),
                        text=elem_data.get("text"),
                        id=elem_data.get("id"),
                        position=elem_data.get("position"),
                        attributes={
                            **elem_data.get("attributes", {}),
                            "llm_confidence": analysis_result.confidence,
                            "llm_provider": analysis_result.provider_used,
                            "extraction_method": "multimodal_llm",
                        },
                    )
                    elements.append(element)

            # Store layout structure information
            layout_info = analysis_result.result.get("layout_structure", {})
            if layout_info:
                # Add layout elements as special UI elements
                for section, element_ids in layout_info.items():
                    if element_ids:
                        layout_element = UIElement(
                            type="layout_section",
                            id=section,
                            text=f"{section.replace('_', ' ').title()} Section",
                            attributes={
                                "section_type": section,
                                "contains_elements": element_ids,
                                "extraction_method": "layout_analysis",
                            },
                        )
                        elements.append(layout_element)

        except Exception as e:
            print(f"LLM-based UI extraction failed for {image_path}: {e}")
            # Continue to fallback method

        return elements

    async def _analyze_with_multimodal_llm(
        self, image_base64: str, image_path: str,
    ) -> Dict[str, Any]:
        """Analyze image using the multimodal LLM service with structured prompts."""
        try:
            # Generate structured visual analysis prompt
            prompt = self._generate_enhanced_visual_analysis_prompt()

            # Use the LLM service for screenshot analysis
            analysis_result = await self.llm_service.analyze_ui_screenshot(
                image_base64=image_base64,
                prompt=prompt,
            )

            return analysis_result.result

        except Exception as e:
            print(f"Error during multimodal analysis for {image_path}: {e}")
            return {}

    def _generate_enhanced_visual_analysis_prompt(self) -> str:
        """Generate an enhanced prompt for comprehensive visual analysis."""
        return """
        Analyze this UI screenshot comprehensively and extract all visible interface elements with their relationships.

        Focus on:
        1. Interactive elements (buttons, inputs, links, controls)
        2. Form structures and validation elements
        3. Navigation components (menus, tabs, breadcrumbs)
        4. Data display elements (tables, lists, cards, text blocks)
        5. Layout sections (header, sidebar, main content, footer)
        6. Visual hierarchy and element groupings
        7. Element relationships and dependencies

        For each element, provide:
        - type: Specific element type (button, text_input, select_dropdown, navigation_link, etc.)
        - text: Visible text content or label
        - id: Descriptive, stable identifier based on content/position
        - position: Bounding box with x, y, width, height
        - attributes: Additional properties like:
          - interactive: true/false
          - form_element: true/false
          - navigation: true/false
          - validation_required: true/false
          - placeholder: placeholder text if any
          - size: relative size (small, medium, large)
          - style: visual style notes

        Also identify:
        - Layout structure (header/main/sidebar/footer sections)
        - Element groupings and relationships
        - Form validation patterns
        - Navigation hierarchies
        - Accessibility considerations

        Respond in JSON format with comprehensive element and layout analysis.
        """

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_data = buffer.getvalue()
        return base64.b64encode(image_data).decode("utf-8")

    def _basic_cv_analysis(
            self,
            image: Image.Image,
            image_path: str) -> List[UIElement]:
        """Enhanced basic computer vision analysis as fallback."""
        elements = []
        width, height = image.size

        # Analyze image regions and attempt to identify common UI patterns
        regions = self._identify_ui_regions(image)

        for region in regions:
            element = UIElement(
                type=region.get(
                    "type", "ui_region"), text=region.get(
                    "text", f"Region in {
                        os.path.basename(image_path)}"), position=region.get(
                    "position", {
                        "x": 0, "y": 0, "width": width, "height": height}), attributes={
                            "analysis_method": "basic_cv", "confidence": region.get(
                                "confidence", 0.3), "region_type": region.get(
                                    "region_type", "unknown"), }, )
            elements.append(element)

        # If no regions detected, create a generic full-image element
        if not elements:
            element = UIElement(
                type="screenshot",
                text=f"Full screenshot from {os.path.basename(image_path)}",
                position={"x": 0, "y": 0, "width": width, "height": height},
                attributes={
                    "analysis_method": "basic_cv_fallback",
                    "total_pixels": width * height,
                },
            )
            elements.append(element)

        return elements

    def _identify_ui_regions(self, image: Image.Image) -> List[Dict[str, Any]]:
        """Identify potential UI regions using basic image analysis."""
        regions = []
        width, height = image.size

        # Enhanced region identification using image analysis
        # Convert to numpy array for CV operations
        try:
            import numpy as np
            img_array = np.array(image)

            # Basic edge detection for content regions
            gray = np.mean(
                img_array, axis=2) if len(
                img_array.shape) == 3 else img_array
            edges = np.abs(np.diff(gray, axis=1)).sum(
                axis=1)  # Horizontal edge intensity
            edge_threshold = np.percentile(edges, 75)  # Top 25% edge density

            # Identify content regions by edge density
            content_regions = []
            in_region = False
            region_start = 0

            for i, edge_intensity in enumerate(edges):
                if edge_intensity > edge_threshold and not in_region:
                    region_start = i
                    in_region = True
                elif edge_intensity <= edge_threshold and in_region:
                    if i - region_start > 20:  # Minimum region height
                        content_regions.append((region_start, i))
                    in_region = False

        except ImportError:
            # Fallback to simple heuristic regions if numpy not available
            content_regions = [(height // 4, height * 3 // 4)]

        # Top region (potential header)
        if height > 100:
            regions.append({
                "type": "header_region",
                "position": {"x": 0, "y": 0, "width": width, "height": min(80, height // 10)},
                "confidence": 0.4,
                "region_type": "navigation",
            })

        # Main content area
        main_start_y = min(80, height // 10)
        main_height = height - main_start_y - min(60, height // 15)
        if main_height > 0:
            regions.append({
                "type": "main_content",
                "position": {"x": 0, "y": main_start_y, "width": width, "height": main_height},
                "confidence": 0.5,
                "region_type": "content",
            })

        # Bottom region (potential footer)
        if height > 150:
            footer_height = min(60, height // 15)
            regions.append({"type": "footer_region",
                            "position": {"x": 0,
                                         "y": height - footer_height,
                                         "width": width,
                                         "height": footer_height},
                            "confidence": 0.3,
                            "region_type": "navigation",
                            })

        return regions

    async def _enhance_with_relationship_analysis(
        self, representation: AbstractRepresentation, scope: ValidationScope,
    ) -> AbstractRepresentation:
        """Enhance the representation with UI element relationship analysis."""
        if not representation.ui_elements:
            return representation

        try:
            # Prepare elements for relationship analysis
            elements_data = [asdict(elem) for elem in representation.ui_elements]

            # Analyze element relationships using LLM
            relationship_analysis = await self.llm_service.analyze_ui_element_relationships(
                elements_data,
                f"Screenshot analysis for {scope.value} validation",
            )

            # Enhance representation with relationship data
            representation.metadata["relationship_analysis"] = {
                "confidence": relationship_analysis.confidence,
                "provider": relationship_analysis.provider_used,
                "analysis_results": relationship_analysis.result,
            }

            # Update elements with relationship information
            relationships = relationship_analysis.result.get(
                "element_relationships", [])
            workflows = relationship_analysis.result.get("user_workflows", [])
            form_groups = relationship_analysis.result.get("form_groups", [])

            # Create a mapping for quick lookup
            element_id_map = {
                elem.id: i for i, elem in enumerate(
                    representation.ui_elements) if elem.id}

            # Enhance elements with relationship data
            for relationship in relationships:
                source_id = relationship.get("source_element_id")
                target_id = relationship.get("target_element_id")
                rel_type = relationship.get("relationship_type")

                if source_id in element_id_map:
                    elem_idx = element_id_map[source_id]
                    elem = representation.ui_elements[elem_idx]

                    if elem.attributes is None:
                        elem.attributes = {}

                    if "relationships" not in elem.attributes:
                        elem.attributes["relationships"] = []

                    elem.attributes["relationships"].append({
                        "target": target_id,
                        "type": rel_type,
                        "description": relationship.get("description", ""),
                    })

            # Add workflow information to relevant elements
            for workflow in workflows:
                workflow_steps = workflow.get("steps", [])
                for step in workflow_steps:
                    # Try to match workflow steps to elements
                    for elem in representation.ui_elements:
                        if elem.text and any(word in step.lower()
                                             for word in elem.text.lower().split()):
                            if elem.attributes is None:
                                elem.attributes = {}
                            if "workflows" not in elem.attributes:
                                elem.attributes["workflows"] = []
                            elem.attributes["workflows"].append({
                                "name": workflow.get("workflow_name", ""),
                                "step": step,
                                "critical_path": workflow.get("critical_path", False),
                            })

            # Add form group information
            for form_group in form_groups:
                group_elements = form_group.get("elements", [])
                validation_rules = form_group.get("validation_rules", [])

                for elem_id in group_elements:
                    if elem_id in element_id_map:
                        elem_idx = element_id_map[elem_id]
                        elem = representation.ui_elements[elem_idx]

                        if elem.attributes is None:
                            elem.attributes = {}

                        elem.attributes["form_group"] = {
                            "name": form_group.get("group_name", ""),
                            "validation_rules": validation_rules,
                        }

        except Exception as e:
            representation.metadata["relationship_analysis_error"] = str(e)

        return representation

    def _merge_visual_analysis(
        self, target: AbstractRepresentation, source: AbstractRepresentation,
    ):
        """Merge visual analysis results from multiple images."""
        target.ui_elements.extend(source.ui_elements)
        target.metadata.update(source.metadata)

        # Track multiple images
        if "analyzed_images" not in target.metadata:
            target.metadata["analyzed_images"] = []

        if "image_path" in source.metadata:
            target.metadata["analyzed_images"].append(source.metadata["image_path"])

        # Aggregate element counts
        if "total_elements_count" not in target.metadata:
            target.metadata["total_elements_count"] = 0

        target.metadata["total_elements_count"] += source.metadata.get(
            "elements_count", 0)

    def supports_scope(self, scope: ValidationScope) -> bool:
        """Check if analyzer supports the given validation scope."""
        return scope in self.supported_scopes
