"""
LLM Service for AI-Powered Migration Validation System.

Provides a unified interface for multiple LLM providers (OpenAI, Anthropic, Google)
with async support, error handling, and token management.
"""

import asyncio
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
    Unified LLM service supporting multiple providers.

    Provides async interface for semantic analysis, code comparison,
    and natural language processing tasks in the migration validation pipeline.
    """

    def __init__(self, config: LLMConfig):
        """Initialize LLM service with configuration."""
        self.config = config
        self.logger = logger.bind(provider=config.provider.value, model=config.model)

        # Initialize provider-specific clients
        self._openai_client: Optional[AsyncOpenAI] = None
        self._anthropic_client: Optional[AsyncAnthropic] = None
        self._google_client: Optional[Any] = None

        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate client based on provider."""
        if self.config.provider == LLMProvider.OPENAI:
            if openai is None:
                raise LLMProviderNotAvailable("OpenAI package not installed")

            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise LLMProviderNotAvailable("OpenAI API key not found")

            self._openai_client = AsyncOpenAI(
                api_key=api_key, timeout=self.config.timeout
            )

        elif self.config.provider == LLMProvider.ANTHROPIC:
            if anthropic is None:
                raise LLMProviderNotAvailable("Anthropic package not installed")

            api_key = self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise LLMProviderNotAvailable("Anthropic API key not found")

            self._anthropic_client = AsyncAnthropic(
                api_key=api_key, timeout=self.config.timeout
            )

        elif self.config.provider == LLMProvider.GOOGLE:
            if genai is None:
                raise LLMProviderNotAvailable("Google GenAI package not installed")

            api_key = self.config.api_key or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise LLMProviderNotAvailable("Google API key not found")

            genai.configure(api_key=api_key)
            self._google_client = genai.GenerativeModel(self.config.model)

        self.logger.info("LLM client initialized successfully")

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate response from LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific parameters

        Returns:
            Standardized LLM response
        """
        try:
            if self.config.provider == LLMProvider.OPENAI:
                return await self._openai_generate(messages, system_prompt, **kwargs)
            elif self.config.provider == LLMProvider.ANTHROPIC:
                return await self._anthropic_generate(messages, system_prompt, **kwargs)
            elif self.config.provider == LLMProvider.GOOGLE:
                return await self._google_generate(messages, system_prompt, **kwargs)
            else:
                raise LLMServiceError(f"Unsupported provider: {self.config.provider}")

        except Exception as e:
            self.logger.error("LLM generation failed", error=str(e))
            raise LLMServiceError(f"LLM generation failed: {str(e)}")

    async def _openai_generate(
        self, messages: List[Dict[str, str]], system_prompt: Optional[str], **kwargs
    ) -> LLMResponse:
        """Generate response using OpenAI."""
        # Prepare messages
        openai_messages = []

        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})

        openai_messages.extend(messages)

        # Make API call
        response = await self._openai_client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
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
        self, messages: List[Dict[str, str]], system_prompt: Optional[str], **kwargs
    ) -> LLMResponse:
        """Generate response using Anthropic Claude."""
        # Prepare messages
        anthropic_messages = []
        for msg in messages:
            anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

        # Make API call
        response = await self._anthropic_client.messages.create(
            model=self.config.model,
            system=system_prompt,
            messages=anthropic_messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
        )

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            provider="anthropic",
            usage=response.usage.model_dump() if hasattr(response, "usage") else None,
            metadata={"stop_reason": response.stop_reason},
        )

    async def _google_generate(
        self, messages: List[Dict[str, str]], system_prompt: Optional[str], **kwargs
    ) -> LLMResponse:
        """Generate response using Google Gemini."""
        # Combine system prompt and messages for Google
        prompt_parts = []

        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}")

        for msg in messages:
            role = "Human" if msg["role"] == "user" else "Assistant"
            prompt_parts.append(f"{role}: {msg['content']}")

        full_prompt = "\n\n".join(prompt_parts)

        # Make API call
        response = await asyncio.to_thread(
            self._google_client.generate_content,
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
            ),
        )

        return LLMResponse(
            content=response.text,
            model=self.config.model,
            provider="google",
            usage=None,  # Google doesn't provide detailed usage in this format
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

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current LLM provider and configuration."""
        return {
            "provider": self.config.provider.value,
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "timeout": self.config.timeout,
        }


def create_llm_service(
    provider: str = "openai", model: Optional[str] = None, **kwargs
) -> LLMService:
    """
    Factory function to create LLM service with sensible defaults.

    Args:
        provider: LLM provider name
        model: Model name (provider-specific defaults if not specified)
        **kwargs: Additional configuration options

    Returns:
        Configured LLM service instance
    """
    provider_enum = LLMProvider(provider.lower())

    # Set default models for each provider
    if model is None:
        if provider_enum == LLMProvider.OPENAI:
            model = "gpt-4-turbo-preview"
        elif provider_enum == LLMProvider.ANTHROPIC:
            model = "claude-3-sonnet-20240229"
        elif provider_enum == LLMProvider.GOOGLE:
            model = "gemini-pro"
        else:
            raise ValueError(f"Unknown provider: {provider}")

    config = LLMConfig(provider=provider_enum, model=model, **kwargs)

    return LLMService(config)
