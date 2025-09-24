"""LLM Service for AI-Powered Migration Validation System.

Provides a unified interface for multiple LLM providers (OpenAI, Anthropic, Google)
with async support, error handling, token management, and structured prompt templates.
"""

import asyncio
import base64
import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import structlog

from .prompt_templates import AnalysisType, prompt_manager

try:
    import openai
    from openai import AsyncOpenAI
except ImportError:
    openai = None

try:
    import anthropic
    from anthropic import AsyncAnthropic
except ImportError:
    anthropic = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = structlog.get_logger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


@dataclass
class LLMConfig:
    """Configuration for LLM service."""

    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout: float = 60.0


@dataclass
class LLMResponse:
    """Standardized LLM response."""

    content: str
    model: str
    provider: str
    usage: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass
class AnalysisResult:
    """Structured analysis result with confidence scoring."""

    analysis_type: AnalysisType
    result: dict[str, Any]
    confidence: float
    provider_used: str
    model_used: str
    metadata: dict[str, Any]


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""


class LLMProviderNotAvailable(LLMServiceError):
    """Raised when requested LLM provider is not available."""


class LLMService:
    """Unified LLM service supporting multiple providers with failover and structured analysis.

    Provides a resilient async interface for semantic analysis, code comparison,
    and natural language processing tasks in the migration validation pipeline.
    """

    def __init__(self, configs: list[LLMConfig]):
        """Initialize LLM service with a list of configurations for failover."""
        if not configs:
            raise LLMServiceError("At least one LLM configuration is required.")
        self.configs = configs
        self.logger = logger.bind(
            providers=[c.provider.value for c in configs],
            models=[c.model for c in configs],
        )

        # Initialize provider-specific clients
        self._clients: dict[LLMProvider, Any] = {}
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize all clients based on the provided configurations."""
        for config in self.configs:
            if config.provider in self._clients:
                continue  # Skip if a client for this provider is already initialized

            try:
                if config.provider == LLMProvider.OPENAI:
                    if openai is None:
                        raise LLMProviderNotAvailable("OpenAI package not installed")
                    api_key = config.api_key or os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        raise LLMProviderNotAvailable("OpenAI API key not found")
                    self._clients[config.provider] = AsyncOpenAI(
                        api_key=api_key,
                        timeout=config.timeout,
                    )

                elif config.provider == LLMProvider.ANTHROPIC:
                    if anthropic is None:
                        raise LLMProviderNotAvailable("Anthropic package not installed")
                    api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
                    if not api_key:
                        raise LLMProviderNotAvailable("Anthropic API key not found")
                    self._clients[config.provider] = AsyncAnthropic(
                        api_key=api_key,
                        timeout=config.timeout,
                    )

                elif config.provider == LLMProvider.GOOGLE:
                    if genai is None:
                        raise LLMProviderNotAvailable(
                            "Google GenAI package not installed"
                        )
                    api_key = config.api_key or os.getenv("GOOGLE_API_KEY")
                    if not api_key:
                        raise LLMProviderNotAvailable("Google API key not found")
                    genai.configure(api_key=api_key)
                    # Note: Google's client is model-specific, so we store the model
                    # object
                    self._clients[config.provider] = genai.GenerativeModel(config.model)

                self.logger.info(
                    "LLM client initialized successfully",
                    provider=config.provider.value,
                )
            except LLMProviderNotAvailable as e:
                self.logger.warning(
                    "Failed to initialize LLM client",
                    provider=config.provider.value,
                    error=str(e),
                )

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate response from LLM with failover support.

        It attempts to generate a response from the configured providers in order.
        If one provider fails, it logs the error and tries the next one.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific parameters

        Returns:
            Standardized LLM response

        Raises:
            LLMServiceError: If all configured providers fail.

        """
        last_error: Optional[Exception] = None
        for config in self.configs:
            if config.provider not in self._clients:
                self.logger.warning(
                    "Skipping uninitialized provider",
                    provider=config.provider.value,
                )
                continue

            try:
                self.logger.info(
                    "Attempting generation",
                    provider=config.provider.value,
                    model=config.model,
                )
                if config.provider == LLMProvider.OPENAI:
                    return await self._openai_generate(
                        config, messages, system_prompt, **kwargs
                    )
                if config.provider == LLMProvider.ANTHROPIC:
                    return await self._anthropic_generate(
                        config,
                        messages,
                        system_prompt,
                        **kwargs,
                    )
                if config.provider == LLMProvider.GOOGLE:
                    return await self._google_generate(
                        config, messages, system_prompt, **kwargs
                    )
                self.logger.warning(
                    f"Unsupported provider configured: {config.provider}"
                )
                continue

            except Exception as e:
                last_error = e
                self.logger.error(
                    "LLM generation failed for provider",
                    provider=config.provider.value,
                    error=str(e),
                )

        raise LLMServiceError(
            f"All LLM providers failed. Last error: {last_error}",
        ) from last_error

    async def structured_analysis(
        self,
        analysis_type: AnalysisType,
        context: dict[str, Any],
        retry_on_parse_error: bool = True,
    ) -> AnalysisResult:
        """Perform structured analysis using prompt templates.

        Args:
            analysis_type: Type of analysis to perform
            context: Context data for the analysis
            retry_on_parse_error: Whether to retry with a different provider on parse errors

        Returns:
            Structured analysis result with confidence scoring

        """
        # Get formatted prompts
        system_prompt, user_prompt = prompt_manager.format_prompt(
            analysis_type, context
        )

        # Enhance user prompt with format expectations
        enhanced_user_prompt = f"""{user_prompt}

IMPORTANT: Respond ONLY in valid JSON format matching this structure:
{json.dumps(prompt_manager.get_expected_format(analysis_type), indent=2)}

Do not include any text before or after the JSON response."""

        messages = [{"role": "user", "content": enhanced_user_prompt}]

        last_error = None
        used_provider = None
        used_model = None

        for config in self.configs:
            if config.provider not in self._clients:
                continue

            try:
                self.logger.info(
                    "Attempting structured analysis",
                    analysis_type=analysis_type.value,
                    provider=config.provider.value,
                )

                response = await self.generate_response(
                    messages,
                    system_prompt,
                    max_tokens=config.max_tokens,
                )

                used_provider = response.provider
                used_model = response.model

                # Parse JSON response
                result = self._parse_analysis_response(analysis_type, response.content)

                # Calculate confidence score
                confidence = self._calculate_confidence(analysis_type, result, response)

                return AnalysisResult(
                    analysis_type=analysis_type,
                    result=result,
                    confidence=confidence,
                    provider_used=used_provider,
                    model_used=used_model,
                    metadata={
                        "usage": response.usage,
                        "response_metadata": response.metadata,
                        "parse_successful": True,
                    },
                )

            except json.JSONDecodeError as e:
                self.logger.warning(
                    "JSON parse error for structured analysis",
                    analysis_type=analysis_type.value,
                    provider=config.provider.value,
                    error=str(e),
                )
                last_error = e
                if not retry_on_parse_error:
                    break

            except Exception as e:
                self.logger.error(
                    "Structured analysis failed for provider",
                    analysis_type=analysis_type.value,
                    provider=config.provider.value,
                    error=str(e),
                )
                last_error = e

        # All providers failed, return fallback response
        self.logger.warning(
            "All providers failed for structured analysis, using fallback",
            analysis_type=analysis_type.value,
            last_error=str(last_error) if last_error else "Unknown",
        )

        fallback_result = prompt_manager.get_fallback_response(analysis_type)
        return AnalysisResult(
            analysis_type=analysis_type,
            result=fallback_result,
            confidence=0.1,
            provider_used=used_provider or "fallback",
            model_used=used_model or "fallback",
            metadata={
                "fallback_used": True,
                "last_error": str(last_error) if last_error else None,
                "parse_successful": False,
            },
        )

    def _parse_analysis_response(
        self,
        analysis_type: AnalysisType,
        response_content: str,
    ) -> dict[str, Any]:
        """Parse and validate analysis response."""
        try:
            # Clean response content (remove potential markdown formatting)
            content = response_content.strip()
            content = content.removeprefix("```json")
            content = content.removesuffix("```")
            content = content.strip()

            result = json.loads(content)

            # Validate response format
            if not prompt_manager.validate_response_format(analysis_type, result):
                self.logger.warning(
                    "Response format validation failed",
                    analysis_type=analysis_type.value,
                )

            return result

        except json.JSONDecodeError as e:
            self.logger.error(
                "Failed to parse JSON response",
                analysis_type=analysis_type.value,
                content_preview=response_content[:200],
                error=str(e),
            )
            raise

    def _calculate_confidence(
        self,
        analysis_type: AnalysisType,
        result: dict[str, Any],
        response: LLMResponse,
    ) -> float:
        """Calculate confidence score based on response quality."""
        base_confidence = 0.8  # Base confidence for successful parsing

        # Adjust confidence based on analysis-specific factors
        template = prompt_manager.get_template(analysis_type)

        # Check if response includes confidence field
        if "confidence" in result and isinstance(result["confidence"], (int, float)):
            explicit_confidence = float(result["confidence"])
            # Weight explicit confidence with our assessment
            return (base_confidence + explicit_confidence) / 2

        # Response quality indicators
        quality_factors = []

        # Check completeness of response
        expected_keys = set(template.expected_response_format.keys())
        actual_keys = set(result.keys())
        completeness = len(actual_keys & expected_keys) / len(expected_keys)
        quality_factors.append(completeness)

        # Check for empty or default values
        non_empty_values = sum(
            1 for value in result.values() if value not in [None, "", [], {}, 0]
        )
        value_quality = non_empty_values / len(result) if result else 0
        quality_factors.append(value_quality)

        # Calculate weighted confidence
        quality_score = (
            sum(quality_factors) / len(quality_factors) if quality_factors else 0.5
        )

        return min(base_confidence * quality_score, 1.0)

    async def _openai_generate(
        self,
        config: LLMConfig,
        messages: list[dict[str, str]],
        system_prompt: Optional[str],
        **kwargs,
    ) -> LLMResponse:
        """Generate response using OpenAI."""
        client = self._clients[LLMProvider.OPENAI]
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        openai_messages.extend(messages)

        response = await client.chat.completions.create(
            model=config.model,
            messages=openai_messages,
            max_tokens=kwargs.get("max_tokens", config.max_tokens),
            temperature=kwargs.get("temperature", config.temperature),
            **{
                k: v
                for k, v in kwargs.items()
                if k not in ["max_tokens", "temperature"]
            },
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            provider="openai",
            usage=response.usage.model_dump() if response.usage else None,
            metadata={"finish_reason": response.choices[0].finish_reason},
        )

    async def _anthropic_generate(
        self,
        config: LLMConfig,
        messages: list[dict[str, str]],
        system_prompt: Optional[str],
        **kwargs,
    ) -> LLMResponse:
        """Generate response using Anthropic Claude."""
        client = self._clients[LLMProvider.ANTHROPIC]
        anthropic_messages = [
            {"role": msg["role"], "content": msg["content"]} for msg in messages
        ]

        response = await client.messages.create(
            model=config.model,
            system=system_prompt,
            messages=anthropic_messages,
            max_tokens=kwargs.get("max_tokens", config.max_tokens),
            temperature=kwargs.get("temperature", config.temperature),
        )

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            provider="anthropic",
            usage=response.usage.model_dump() if hasattr(response, "usage") else None,
            metadata={"stop_reason": response.stop_reason},
        )

    async def _google_generate(
        self,
        config: LLMConfig,
        messages: list[dict[str, str]],
        system_prompt: Optional[str],
        **kwargs,
    ) -> LLMResponse:
        """Generate response using Google Gemini."""
        client = self._clients[LLMProvider.GOOGLE]
        prompt_parts = []
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}")
        for msg in messages:
            role = "Human" if msg["role"] == "user" else "Assistant"
            prompt_parts.append(f"{role}: {msg['content']}")
        full_prompt = "\n\n".join(prompt_parts)

        response = await asyncio.to_thread(
            client.generate_content,
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=kwargs.get("max_tokens", config.max_tokens),
                temperature=kwargs.get("temperature", config.temperature),
            ),
        )

        return LLMResponse(
            content=response.text,
            model=config.model,
            provider="google",
            usage=None,
            metadata={"finish_reason": "stop"},
        )

    async def analyze_code_semantic_similarity(
        self,
        source_code: str,
        target_code: str,
        context: str = "",
        source_language: str = "auto",
        target_language: str = "auto",
    ) -> AnalysisResult:
        """Analyze semantic similarity between source and target code using structured prompts.

        Args:
            source_code: Source code snippet
            target_code: Target code snippet
            context: Additional context about the migration
            source_language: Programming language of source code
            target_language: Programming language of target code

        Returns:
            Structured analysis results with similarity score and discrepancies

        """
        analysis_context = {
            "source_code": source_code,
            "target_code": target_code,
            "context": context,
            "source_language": source_language,
            "target_language": target_language,
        }

        return await self.structured_analysis(
            AnalysisType.CODE_SEMANTIC_SIMILARITY,
            analysis_context,
        )

    async def compare_ui_elements(
        self,
        source_elements: list[dict[str, Any]],
        target_elements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compare UI elements between source and target systems.

        Args:
            source_elements: Source UI elements
            target_elements: Target UI elements

        Returns:
            Comparison analysis with matched elements and discrepancies

        """
        system_prompt = """You are a UI/UX expert analyzing migration fidelity.

Analyze the provided UI elements from source and target systems and provide:
1. Element matching and mapping
2. Missing or additional elements
3. Functional equivalence of form controls
4. User experience preservation assessment

Respond in JSON format with detailed analysis."""

        messages = [
            {
                "role": "user",
                "content": f"""Compare these UI elements:

SOURCE ELEMENTS:
{source_elements}

TARGET ELEMENTS:
{target_elements}

Provide comprehensive UI comparison analysis.""",
            },
        ]

        try:
            response = await self.generate_response(messages, system_prompt)
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {
                "elements_matched": 0,
                "missing_elements": [],
                "additional_elements": [],
                "functional_equivalent": False,
                "ux_preserved": False,
                "recommendations": ["Manual UI review required"],
            }

    async def validate_business_logic(
        self,
        source_functions: list[dict[str, Any]],
        target_functions: list[dict[str, Any]],
        domain_context: str = "",
    ) -> AnalysisResult:
        """Validate preservation of business logic between source and target using structured analysis.

        Args:
            source_functions: Source business functions
            target_functions: Target business functions
            domain_context: Business domain context

        Returns:
            Structured business logic validation results

        """
        analysis_context = {
            "source_functions_json": json.dumps(source_functions, indent=2),
            "target_functions_json": json.dumps(target_functions, indent=2),
            "domain_context": domain_context,
        }

        return await self.structured_analysis(
            AnalysisType.BUSINESS_LOGIC_VALIDATION,
            analysis_context,
        )

    async def analyze_ui_screenshot(
        self,
        image_base64: str,
        prompt: str,
        detail: str = "auto",
    ) -> AnalysisResult:
        """Analyze a UI screenshot using a multimodal LLM with structured output.

        Args:
            image_base64: Base64 encoded image string.
            prompt: The text prompt to guide the analysis.
            detail: The level of detail for the image analysis (OpenAI specific).

        Returns:
            Structured analysis result containing the analysis from the LLM.

        Raises:
            LLMServiceError: If all configured vision providers fail.

        """
        last_error: Optional[Exception] = None
        # Prioritize providers known for strong vision capabilities
        vision_providers = [
            LLMProvider.OPENAI,
            LLMProvider.GOOGLE,
            LLMProvider.ANTHROPIC,
        ]

        for provider in vision_providers:
            config = next((c for c in self.configs if c.provider == provider), None)
            if not config or provider not in self._clients:
                continue

            try:
                self.logger.info(
                    "Attempting screenshot analysis",
                    provider=provider.value,
                    model=config.model,
                )
                client = self._clients[provider]
                content = ""

                if provider == LLMProvider.OPENAI:
                    vision_model = "gpt-4-vision-preview"
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_base64}",
                                        "detail": detail,
                                    },
                                },
                            ],
                        },
                    ]
                    response = await client.chat.completions.create(
                        model=vision_model,
                        messages=messages,
                        max_tokens=config.max_tokens,
                    )
                    content = response.choices[0].message.content or ""

                elif provider == LLMProvider.GOOGLE:
                    vision_model = "gemini-pro-vision"
                    vision_client = genai.GenerativeModel(vision_model)
                    img_blob = {
                        "mime_type": "image/png",
                        "data": base64.b64decode(image_base64),
                    }
                    response = await asyncio.to_thread(
                        vision_client.generate_content,
                        [prompt, img_blob],
                    )
                    content = response.text

                elif provider == LLMProvider.ANTHROPIC:
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image_base64,
                                    },
                                },
                                {"type": "text", "text": prompt},
                            ],
                        },
                    ]
                    response = await client.messages.create(
                        model=config.model,  # Assumes model supports vision
                        messages=messages,
                        max_tokens=config.max_tokens,
                    )
                    content = response.content[0].text

                else:
                    continue

                if not content:
                    raise LLMServiceError("Received empty content from provider")

                try:
                    result_data = json.loads(content)
                except json.JSONDecodeError:
                    self.logger.warning(
                        "Failed to parse JSON from vision model, returning raw content",
                        provider=provider.value,
                    )
                    result_data = {"raw_content": content}

                return AnalysisResult(
                    analysis_type=AnalysisType.VISUAL_SCREENSHOT_ANALYSIS,
                    result=result_data,
                    confidence=0.8,  # Default confidence for vision analysis
                    provider_used=provider.value,
                    model_used=config.model,
                    metadata={"vision_analysis": True},
                )

            except Exception as e:
                last_error = e
                self.logger.error(
                    "Screenshot analysis failed for provider",
                    provider=provider.value,
                    error=str(e),
                )

        raise LLMServiceError(
            f"All vision providers failed. Last error: {last_error}",
        ) from last_error

    async def analyze_ui_element_relationships(
        self,
        elements: list[dict[str, Any]],
        screen_context: str = "",
    ) -> AnalysisResult:
        """Analyze relationships between UI elements using structured analysis.

        Args:
            elements: List of UI elements to analyze
            screen_context: Context about the screen/page

        Returns:
            Structured analysis of element relationships and workflows

        """
        analysis_context = {
            "elements_json": json.dumps(elements, indent=2),
            "screen_context": screen_context,
        }

        return await self.structured_analysis(
            AnalysisType.UI_RELATIONSHIP_ANALYSIS,
            analysis_context,
        )

    async def assess_migration_fidelity(
        self,
        source_analysis: dict[str, Any],
        target_analysis: dict[str, Any],
        discrepancies: list[dict[str, Any]],
        validation_scope: str,
    ) -> AnalysisResult:
        """Assess overall migration fidelity using comprehensive analysis.

        Args:
            source_analysis: Source system analysis results
            target_analysis: Target system analysis results
            discrepancies: List of identified discrepancies
            validation_scope: Scope of validation

        Returns:
            Comprehensive migration fidelity assessment

        """
        analysis_context = {
            "source_analysis_json": json.dumps(source_analysis, indent=2),
            "target_analysis_json": json.dumps(target_analysis, indent=2),
            "discrepancies_json": json.dumps(discrepancies, indent=2),
            "validation_scope": validation_scope,
        }

        return await self.structured_analysis(
            AnalysisType.MIGRATION_FIDELITY,
            analysis_context,
        )

    def get_provider_info(self) -> list[dict[str, Any]]:
        """Get information about the current LLM provider configurations."""
        return [
            {
                "provider": config.provider.value,
                "model": config.model,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "timeout": config.timeout,
            }
            for config in self.configs
        ]


def create_llm_service(
    providers: str = "openai",
    models: Optional[str] = None,
    **kwargs,
) -> LLMService:
    """Factory function to create LLM service with failover support.

    Args:
        providers: Comma-separated string of LLM provider names (e.g., "openai,anthropic").
        models: Comma-separated string of model names. If provided, must match the number of providers.
        **kwargs: Additional configuration options applied to all providers.

    Returns:
        Configured LLM service instance.

    """
    provider_names = [p.strip() for p in providers.split(",")]
    model_names = [m.strip() for m in models.split(",")] if models else []

    if model_names and len(provider_names) != len(model_names):
        raise LLMServiceError(
            "The number of models must match the number of providers."
        )

    configs: list[LLMConfig] = []
    for i, provider_name in enumerate(provider_names):
        provider_enum = LLMProvider(provider_name.lower())
        model = model_names[i] if i < len(model_names) else None

        if model is None:
            if provider_enum == LLMProvider.OPENAI:
                model = "gpt-4-turbo-preview"
            elif provider_enum == LLMProvider.ANTHROPIC:
                model = "claude-3-sonnet-20240229"
            elif provider_enum == LLMProvider.GOOGLE:
                model = "gemini-pro"
            else:
                raise ValueError(f"Unknown provider: {provider_name}")

        configs.append(LLMConfig(provider=provider_enum, model=model, **kwargs))

    return LLMService(configs)
