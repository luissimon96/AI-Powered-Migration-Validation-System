"""Unit tests for LLM service.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.llm_service import (LLMConfig, LLMProvider,
                                      LLMProviderNotAvailable, LLMResponse,
                                      LLMService, create_llm_service)


class TestLLMConfig:
    """Test LLM configuration."""

    def test_llm_config_creation(self):
        """Test creating LLM configuration."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4-turbo-preview",
            api_key="test-key",
            max_tokens=2000,
            temperature=0.2,
            timeout=30.0,
        )

        assert config.provider == LLMProvider.OPENAI
        assert config.model == "gpt-4-turbo-preview"
        assert config.api_key == "test-key"
        assert config.max_tokens == 2000
        assert config.temperature == 0.2
        assert config.timeout == 30.0


class TestLLMResponse:
    """Test LLM response model."""

    def test_llm_response_creation(self):
        """Test creating LLM response."""
        response = LLMResponse(
            content="This is a test response",
            model="gpt-4",
            provider="openai",
            usage={"total_tokens": 150, "prompt_tokens": 100, "completion_tokens": 50},
            metadata={"finish_reason": "stop"},
        )

        assert response.content == "This is a test response"
        assert response.model == "gpt-4"
        assert response.provider == "openai"
        assert response.usage["total_tokens"] == 150
        assert response.metadata["finish_reason"] == "stop"


@pytest.mark.asyncio
class TestLLMService:
    """Test LLM service functionality."""

    @patch("src.services.llm_service.openai")
    def test_openai_initialization(self, mock_openai):
        """Test OpenAI client initialization."""
        mock_openai.AsyncOpenAI.return_value = MagicMock()

        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4", api_key="test-key")

        service = LLMService(config)
        assert service.config.provider == LLMProvider.OPENAI
        assert service._openai_client is not None

    def test_initialization_without_api_key(self):
        """Test initialization fails without API key."""
        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4", api_key=None)

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(LLMProviderNotAvailable):
                LLMService(config)

    @patch("src.services.llm_service.openai")
    async def test_openai_generate_response(self, mock_openai):
        """Test OpenAI response generation."""
        # Mock OpenAI client and response
        mock_client = AsyncMock()
        mock_openai.AsyncOpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "gpt-4"
        mock_response.usage.model_dump.return_value = {"total_tokens": 100}

        mock_client.chat.completions.create.return_value = mock_response

        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4", api_key="test-key")

        service = LLMService(config)

        messages = [{"role": "user", "content": "Test message"}]
        response = await service.generate_response(messages)

        assert isinstance(response, LLMResponse)
        assert response.content == "Test response"
        assert response.provider == "openai"
        assert response.model == "gpt-4"

    @patch("src.services.llm_service.openai")
    async def test_analyze_code_semantic_similarity(self, mock_openai):
        """Test code semantic similarity analysis."""
        mock_client = AsyncMock()
        mock_openai.AsyncOpenAI.return_value = mock_client

        # Mock JSON response
        json_response = """
        {
            "similarity_score": 0.92,
            "functionally_equivalent": true,
            "confidence": 0.95,
            "key_differences": ["Variable naming convention"],
            "potential_issues": [],
            "business_logic_preserved": true,
            "recommendations": ["Standardize naming"]
        }
        """

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json_response
        mock_response.model = "gpt-4"
        mock_response.usage = None

        mock_client.chat.completions.create.return_value = mock_response

        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4", api_key="test-key")

        service = LLMService(config)

        result = await service.analyze_code_semantic_similarity(
            "def func(): return 1",
            "function func() { return 1; }",
            "Python to JavaScript migration",
        )

        assert result["similarity_score"] == 0.92
        assert result["functionally_equivalent"] is True
        assert result["confidence"] == 0.95
        assert "Variable naming convention" in result["key_differences"]

    async def test_analyze_code_with_invalid_json(self, mock_llm_service):
        """Test handling of invalid JSON response."""
        # Mock invalid JSON response
        mock_llm_service.generate_response.return_value = LLMResponse(
            content="Invalid JSON response", model="mock-model", provider="mock",
        )

        result = await mock_llm_service.analyze_code_semantic_similarity(
            "code1", "code2", "context",
        )

        # Should return fallback result
        assert result["similarity_score"] == 0.5
        assert result["functionally_equivalent"] is False
        assert "Analysis failed" in result["key_differences"]


class TestLLMServiceFactory:
    """Test LLM service factory function."""

    @patch("src.services.llm_service.openai")
    def test_create_openai_service(self, mock_openai):
        """Test creating OpenAI service with factory."""
        mock_openai.AsyncOpenAI.return_value = MagicMock()

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = create_llm_service(provider="openai")

            assert service.config.provider == LLMProvider.OPENAI
            assert service.config.model == "gpt-4-turbo-preview"  # default

    @patch("src.services.llm_service.anthropic")
    def test_create_anthropic_service(self, mock_anthropic):
        """Test creating Anthropic service with factory."""
        mock_anthropic.AsyncAnthropic.return_value = MagicMock()

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            service = create_llm_service(provider="anthropic")

            assert service.config.provider == LLMProvider.ANTHROPIC
            assert service.config.model == "claude-3-sonnet-20240229"  # default

    def test_create_service_with_invalid_provider(self):
        """Test factory with invalid provider."""
        with pytest.raises(ValueError):
            create_llm_service(provider="invalid-provider")

    @patch("src.services.llm_service.openai")
    def test_create_service_with_custom_model(self, mock_openai):
        """Test factory with custom model."""
        mock_openai.AsyncOpenAI.return_value = MagicMock()

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = create_llm_service(
                provider="openai",
                model="gpt-3.5-turbo",
                max_tokens=2000,
                temperature=0.5,
            )

            assert service.config.model == "gpt-3.5-turbo"
            assert service.config.max_tokens == 2000
            assert service.config.temperature == 0.5
