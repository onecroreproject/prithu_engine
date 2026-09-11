"""
Basic tests for Prithu recommendation engine
"""

import pytest
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import Config
from app.exceptions import ErrorCode, PrithuException


class TestConfig:
    """Test configuration module."""

    def test_config_mongodb_uri_exists(self):
        """Test that MongoDB URI is configured."""
        assert Config.MONGODB_URI is not None
        assert len(Config.MONGODB_URI) > 0

    def test_config_database_name_exists(self):
        """Test that database name is configured."""
        assert Config.MONGODB_DATABASE is not None
        assert len(Config.MONGODB_DATABASE) > 0

    def test_config_scoring_weights(self):
        """Test that scoring weights sum to 1.0."""
        total = (
            Config.WEIGHT_FESTIVAL +
            Config.WEIGHT_PUSH +
            Config.WEIGHT_TRENDING
        )
        assert abs(total - 1.0) < 0.01

    def test_config_validate(self):
        """Test config validation passes."""
        assert Config.validate() is True


class TestExceptions:
    """Test exception classes."""

    def test_error_code_exists(self):
        """Test that all error codes exist."""
        assert ErrorCode.DB_CONNECTION_FAILED is not None
        assert ErrorCode.INVALID_INPUT is not None
        assert ErrorCode.RESOURCE_NOT_FOUND is not None

    def test_prithu_exception_to_dict(self):
        """Test exception serialization."""
        exc = PrithuException(
            message="Test error",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            status_code=500
        )
        exc_dict = exc.to_dict()

        assert exc_dict["success"] is False
        assert exc_dict["error"]["code"] == ErrorCode.INTERNAL_SERVER_ERROR.value
        assert exc_dict["error"]["message"] == "Test error"
        assert exc_dict["data"] is None


class TestSchemas:
    """Test Pydantic schemas."""

    def test_recommendation_request_validation(self):
        """Test RecommendationRequest model."""
        from app.models.schemas import RecommendationRequest

        # Valid request
        req = RecommendationRequest(
            user_id="user123",
            limit=20
        )
        assert req.user_id == "user123"
        assert req.limit == 20

    def test_recommendation_request_invalid_user_id(self):
        """Test RecommendationRequest with invalid user_id."""
        from app.models.schemas import RecommendationRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RecommendationRequest(user_id="")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
