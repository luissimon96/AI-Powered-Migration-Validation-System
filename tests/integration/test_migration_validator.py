"""
Integration tests for migration validator.
"""

from unittest.mock import patch

import pytest

from src.core.migration_validator import MigrationValidator
from src.core.models import ValidationScope


@pytest.mark.integration
@pytest.mark.asyncio
class TestMigrationValidatorIntegration:
    """Integration tests for migration validator."""

    async def test_complete_validation_pipeline(
        self, sample_validation_request, mock_llm_service
    ):
        """Test complete validation pipeline."""
        validator = MigrationValidator(llm_client=mock_llm_service)

        # Execute validation
        session = await validator.validate_migration(sample_validation_request)

        # Verify results
        assert session.request == sample_validation_request
        assert session.result is not None
        assert session.result.overall_status in [
            "approved",
            "approved_with_warnings",
            "rejected",
        ]
        assert 0.0 <= session.result.fidelity_score <= 1.0
        assert len(session.processing_log) > 0

        # Verify analysis was performed
        assert session.source_representation is not None
        assert session.target_representation is not None

        # Verify LLM service was called
        mock_llm_service.generate_response.assert_called()

    async def test_validation_with_different_scopes(
        self, sample_validation_request, mock_llm_service
    ):
        """Test validation with different validation scopes."""
        validator = MigrationValidator(llm_client=mock_llm_service)

        scopes_to_test = [
            ValidationScope.BACKEND_FUNCTIONALITY,
            ValidationScope.DATA_STRUCTURE,
            ValidationScope.BUSINESS_LOGIC,
        ]

        for scope in scopes_to_test:
            sample_validation_request.validation_scope = scope
            session = await validator.validate_migration(sample_validation_request)

            assert session.result is not None
            assert session.result.overall_status is not None

    async def test_validation_error_handling(self, sample_validation_request):
        """Test validation error handling."""
        # Create validator with no LLM service to trigger errors
        validator = MigrationValidator(llm_client=None)

        session = await validator.validate_migration(sample_validation_request)

        # Should complete even without LLM service (using fallbacks)
        assert session.result is not None
        assert len(session.processing_log) > 0


@pytest.mark.integration
class TestMigrationValidatorConfiguration:
    """Test migration validator configuration."""

    @patch("src.core.migration_validator.get_validation_config")
    def test_validator_initialization_with_config(
        self, mock_get_config, mock_llm_service
    ):
        """Test validator initialization with configuration."""
        from src.core.config import LLMProviderConfig, ValidationConfig

        # Mock configuration
        mock_config = ValidationConfig.__new__(ValidationConfig)
        mock_config.get_default_llm_config = lambda: LLMProviderConfig(
            provider="openai", model="gpt-4", api_key="test-key", enabled=True
        )
        mock_get_config.return_value = mock_config

        with patch("src.core.migration_validator.create_llm_service") as mock_create:
            mock_create.return_value = mock_llm_service

            validator = MigrationValidator()

            assert validator.llm_service == mock_llm_service
            mock_create.assert_called_once()

    def test_validator_initialization_without_llm(self):
        """Test validator initialization without LLM service."""
        with patch(
            "src.core.migration_validator.get_validation_config"
        ) as mock_get_config:
            mock_config = ValidationConfig.__new__(ValidationConfig)
            mock_config.get_default_llm_config = lambda: None
            mock_get_config.return_value = mock_config

            validator = MigrationValidator()

            assert validator.llm_service is None
            assert validator.comparator is not None
            assert validator.reporter is not None
