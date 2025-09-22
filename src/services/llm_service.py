"""
LLM Service for AI-Powered Migration Validation System.

Provides a unified interface for multiple LLM providers (OpenAI, Anthropic, Google)
with async support, error handling, and token management.
"""

import asyncio
import base64
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import structlog

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
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""

    pass


class LLMProviderNotAvailable(LLMServiceError):
    """Raised when requested LLM provider is not available."""

    pass


class LLMService:
    """
    Unified LLM service supporting multiple providers with failover.

    Provides a resilient async interface for semantic analysis, code comparison,
    and natural language processing tasks in the migration validation pipeline.
    """

    def __init__(self, configs: List[LLMConfig]):
        """Initialize LLM service with a list of configurations for failover."""
        if not configs:
            raise LLMServiceError("At least one LLM configuration is required.")
        self.configs = configs
        self.logger = logger.bind(
            providers=[c.provider.value for c in configs],
            models=[c.model for c in configs],
        )

        # Initialize provider-specific clients
        self._clients: Dict[LLMProvider, Any] = {}
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
                        api_key=api_key, timeout=config.timeout
                    )

                elif config.provider == LLMProvider.ANTHROPIC:
                    if anthropic is None:
                        raise LLMProviderNotAvailable("Anthropic package not installed")
                    api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
                    if not api_key:
                        raise LLMProviderNotAvailable("Anthropic API key not found")
                    self._clients[config.provider] = AsyncAnthropic(
                        api_key=api_key, timeout=config.timeout
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
                    # Note: Google's client is model-specific, so we store the model object
                    self._clients[config.provider] = genai.GenerativeModel(
                        config.model
                    )

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
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate response from LLM with failover support.

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
                    "Skipping uninitialized provider", provider=config.provider.value
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
                elif config.provider == LLMProvider.ANTHROPIC:
                    return await self._anthropic_generate(
                        config, messages, system_prompt, **kwargs
                    )
                elif config.provider == LLMProvider.GOOGLE:
                    return await self._google_generate(
                        config, messages, system_prompt, **kwargs
                    )
                else:
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
            f"All LLM providers failed. Last error: {last_error}"
        ) from last_error

    async def _openai_generate(
        self,
        config: LLMConfig,
        messages: List[Dict[str, str]],
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
        messages: List[Dict[str, str]],
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
        messages: List[Dict[str, str]],
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
        self, source_code: str, target_code: str, context: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze semantic similarity between source and target code.

        Args:
            source_code: Source code snippet
            target_code: Target code snippet
            context: Additional context about the migration

        Returns:
            Analysis results with similarity score and discrepancies
        """
        system_prompt = """You are an expert code analysis AI specializing in migration validation.
        
Your task is to analyze two code snippets (source and target) and determine:
1. Semantic similarity score (0.0 to 1.0)
2. Functional equivalence assessment
3. Key differences and potential issues
4. Business logic preservation

Respond in JSON format with:
{
  "similarity_score": float,
  "functionally_equivalent": boolean,
  "confidence": float,
  "key_differences": [string],
  "potential_issues": [string],
  "business_logic_preserved": boolean,
  "recommendations": [string]
}"""

        messages = [
            {
                "role": "user",
                "content": f"""Analyze these code snippets for semantic similarity:

SOURCE CODE:
```
{source_code}
```

TARGET CODE:
```
{target_code}
```

CONTEXT: {context}

Provide detailed analysis in JSON format.""",
            }
        ]

        response = await self.generate_response(messages, system_prompt)

        try:
            import json

            return json.loads(response.content)
        except json.JSONDecodeError:
            self.logger.warning(
                "Failed to parse JSON response", content=response.content
            )
            return {
                "similarity_score": 0.5,
                "functionally_equivalent": False,
                "confidence": 0.3,
                "key_differences": ["Analysis failed - could not parse response"],
                "potential_issues": ["LLM response parsing error"],
                "business_logic_preserved": False,
                "recommendations": ["Manual review required"],
            }

    async def compare_ui_elements(
        self,
        source_elements: List[Dict[str, Any]],
        target_elements: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Compare UI elements between source and target systems.

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
            }
        ]

        response = await self.generate_response(messages, system_prompt)

        try:
            import json

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
        source_functions: List[Dict[str, Any]],
        target_functions: List[Dict[str, Any]],
        domain_context: str = "",
    ) -> Dict[str, Any]:
        """
        Validate preservation of business logic between source and target.

        Args:
            source_functions: Source business functions
            target_functions: Target business functions
            domain_context: Business domain context

        Returns:
            Business logic validation results
        """
        system_prompt = """You are a business analyst and software architect expert.
        
Analyze the business logic preservation in a system migration by comparing:
1. Function signatures and parameters
2. Business rules and constraints
3. Data validation logic
4. Error handling patterns
5. Workflow preservation

Focus on identifying critical business logic that must be preserved."""

        messages = [
            {
                "role": "user",
                "content": f"""Validate business logic preservation:

DOMAIN CONTEXT: {domain_context}

SOURCE FUNCTIONS:
{source_functions}

TARGET FUNCTIONS:
{target_functions}

Analyze business logic preservation and identify critical discrepancies.""",
            }
        ]

        response = await self.generate_response(messages, system_prompt)

        try:
            import json

            return json.loads(response.content)
        except json.JSONDecodeError:
            return {
                "business_logic_preserved": False,
                "critical_discrepancies": ["Analysis failed"],
                "validation_gaps": ["Manual review required"],
                "risk_assessment": "high",
                "recommendations": [
                    "Comprehensive manual business logic review required"
                ],
            }

    async def analyze_ui_screenshot(
        self, image_base64: str, prompt: str, detail: str = "auto"
    ) -> Dict[str, Any]:
        """
        Analyze a UI screenshot using a multimodal LLM.

        Args:
            image_base64: Base64 encoded image string.
            prompt: The text prompt to guide the analysis.
            detail: The level of detail for the image analysis (OpenAI specific).

        Returns:
            A dictionary containing the analysis from the LLM.

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
                        }
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
                    img_blob = {"mime_type": "image/png", "data": base64.b64decode(image_base64)}
                    response = await asyncio.to_thread(
                        vision_client.generate_content, [prompt, img_blob]
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
                        }
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

                import json
                return json.loads(content)

            except json.JSONDecodeError:
                self.logger.warning(
                    "Failed to parse JSON from vision model, returning raw content",
                    provider=provider.value,
                )
                return {"raw_content": content}
            except Exception as e:
                last_error = e
                self.logger.error(
                    "Screenshot analysis failed for provider",
                    provider=provider.value,
                    error=str(e),
                )

        raise LLMServiceError(
            f"All vision providers failed. Last error: {last_error}"
        ) from last_error

    def get_provider_info(self) -> List[Dict[str, Any]]:
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
    providers: str = "openai", models: Optional[str] = None, **kwargs
) -> LLMService:
    """
    Factory function to create LLM service with failover support.

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

    configs: List[LLMConfig] = []
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
