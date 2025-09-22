"""
Visual analyzer for extracting features from screenshots and images.

Implements analysis of UI screenshots using computer vision and multimodal LLMs
to extract UI elements, layout information, and visual structure.
"""

import base64
import io
import os
from typing import Any, Dict, List, Optional

from PIL import Image

from ..core.models import (
    AbstractRepresentation,
    InputData,
    InputType,
    TechnologyContext,
    UIElement,
    ValidationScope,
)
from ..services.llm_service import LLMService, create_llm_service
from .base import (
    BaseAnalyzer,
    ExtractionError,
    InvalidInputError,
    UnsupportedScopeError,
)


class VisualAnalyzer(BaseAnalyzer):
    """Analyzer for extracting features from screenshots and images."""

    def __init__(self, technology_context: TechnologyContext):
        """Initialize visual analyzer."""
        super().__init__(technology_context)
        self.supported_scopes = [ValidationScope.UI_LAYOUT, ValidationScope.FULL_SYSTEM]
        self.supported_image_formats = [".png", ".jpg", ".jpeg", ".bmp", ".gif"]
        self.llm_service: LLMService = create_llm_service(
            providers="openai,google,anthropic"
        )

    async def analyze(
        self, input_data: InputData, scope: ValidationScope
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

            return representation

        except Exception as e:
            raise ExtractionError(f"Failed to analyze screenshots: {str(e)}")

    def _is_supported_image(self, file_path: str) -> bool:
        """Check if image format is supported."""
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.supported_image_formats

    async def _analyze_screenshot(
        self, image_path: str, scope: ValidationScope
    ) -> AbstractRepresentation:
        """Analyze a single screenshot."""
        try:
            # Load and validate image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Get image metadata
                width, height = img.size

                # Extract UI elements using computer vision techniques
                ui_elements = await self._extract_ui_elements_from_image(
                    img, image_path
                )

                # Create representation
                representation = AbstractRepresentation(
                    ui_elements=ui_elements,
                    metadata={
                        "image_path": image_path,
                        "image_size": {"width": width, "height": height},
                        "analysis_method": "visual_llm",
                    },
                )

                return representation

        except Exception as e:
            raise ExtractionError(f"Failed to analyze image {image_path}: {str(e)}")

    async def _extract_ui_elements_from_image(
        self, image: Image.Image, image_path: str
    ) -> List[UIElement]:
        """Extract UI elements from image using a multimodal LLM."""
        elements = []

        # Convert image to base64 for LLM processing
        image_base64 = self._image_to_base64(image)

        # Use multimodal LLM to analyze the image
        llm_response = await self._analyze_with_multimodal_llm(image_base64, image_path)
        elements = self._parse_llm_visual_response(llm_response)

        # Fallback to basic computer vision techniques if LLM fails or returns no elements
        if not elements:
            elements = self._basic_cv_analysis(image, image_path)

        return elements

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_data = buffer.getvalue()
        return base64.b64encode(image_data).decode("utf-8")

    async def _analyze_with_multimodal_llm(
        self, image_base64: str, image_path: str
    ) -> Dict[str, Any]:
        """Analyze image using the multimodal LLM service."""
        prompt = self._generate_visual_analysis_prompt()
        try:
            response = await self.llm_service.analyze_ui_screenshot(
                image_base64=image_base64, prompt=prompt
            )
            return response
        except Exception as e:
            # Log the error and return an empty dict to allow fallback
            print(f"Error during multimodal analysis for {image_path}: {e}")
            return {}

    def _generate_visual_analysis_prompt(self) -> str:
        """Generate prompt for visual analysis LLM."""
        return """
        Analyze this UI screenshot and extract all visible interface elements.
        Respond with a JSON object containing a single key "elements".
        The value should be a list of objects, where each object represents a UI element.
        For each element, identify:
        1. type: (e.g., "button", "input", "label", "image", "text", "table").
        2. text: The text content of the element, if any.
        3. id: A descriptive, stable ID for the element (e.g., "username-input", "login-button").
        4. position: An object with x and y coordinates for the center of the element.
        5. attributes: An object for other properties like "size" or "interactive".
        """

    def _parse_llm_visual_response(self, response: Dict[str, Any]) -> List[UIElement]:
        """Parse LLM response into UIElement objects."""
        elements = []

        # Handle cases where LLM returns raw content instead of JSON
        if "raw_content" in response:
            # Here you could add logic to try and parse elements from raw text
            return []

        if "elements" in response and isinstance(response["elements"], list):
            for elem_data in response["elements"]:
                element = UIElement(
                    type=elem_data.get("type", "unknown"),
                    text=elem_data.get("text"),
                    id=elem_data.get("id"),
                    position=elem_data.get("position"),
                    attributes=elem_data.get("attributes", {}),
                )
                elements.append(element)

        return elements

    def _basic_cv_analysis(
        self, image: Image.Image, image_path: str
    ) -> List[UIElement]:
        """Basic computer vision analysis as fallback."""
        # Placeholder for basic CV techniques
        # Could use OpenCV, OCR libraries, etc.

        elements = []

        # Simple text detection using PIL (very basic)
        # In real implementation, you'd use proper OCR like Tesseract
        width, height = image.size

        # Create a generic element for the entire image
        element = UIElement(
            type="image",
            text=f"Screenshot from {os.path.basename(image_path)}",
            position={"width": width, "height": height},
            attributes={"analysis_method": "basic_cv"},
        )
        elements.append(element)

        return elements

    def _merge_visual_analysis(
        self, target: AbstractRepresentation, source: AbstractRepresentation
    ):
        """Merge visual analysis results from multiple images."""
        target.ui_elements.extend(source.ui_elements)
        target.metadata.update(source.metadata)

        # Track multiple images
        if "analyzed_images" not in target.metadata:
            target.metadata["analyzed_images"] = []

        if "image_path" in source.metadata:
            target.metadata["analyzed_images"].append(source.metadata["image_path"])

    def supports_scope(self, scope: ValidationScope) -> bool:
        """Check if analyzer supports the given validation scope."""
        return scope in self.supported_scopes
