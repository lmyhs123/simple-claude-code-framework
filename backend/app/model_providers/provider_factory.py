from app.core.config import settings
from app.model_providers.base import ModelProvider
from app.model_providers.mock_provider import MockModelProvider
from app.model_providers.openai_compatible_provider import OpenAICompatibleProvider


def get_model_provider() -> ModelProvider:
    """Create the configured model provider.

    Only mock is implemented now. Real providers will be added behind this
    factory so gateway code does not depend on a specific vendor.
    """
    if settings.model_provider == "mock":
        return MockModelProvider()
    if settings.model_provider == "openai-compatible":
        return OpenAICompatibleProvider()

    raise ValueError(f"Unsupported model provider: {settings.model_provider}")
