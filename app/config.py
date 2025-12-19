"""Configuration module for Uh Bot.

Manages environment variables and validation using Pydantic.
All secrets (API keys, tokens) are loaded from .env file.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration from environment variables.
    
    Attributes:
        TG_BOT_TOKEN: Telegram Bot API token
        OPENAI_API_KEY: OpenAI API key for GPT-5
        REPLICATE_API_TOKEN: Replicate API token (optional)
        LLM_PROVIDER: Primary LLM provider (openai or replicate)
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
        MAX_FILE_SIZE: Maximum file size in bytes (20MB default)
        MAX_ARCHIVE_SIZE: Maximum ZIP archive size after extraction (100MB default)
        RESPONSE_THRESHOLD: Number of messages before generating docx (3 default)
        TEMP_DIR: Temporary directory for file storage
        OPENAI_MODEL: OpenAI model to use
        REPLICATE_MODEL: Replicate model to use
        
    Example:
        >>> config = get_settings()
        >>> print(config.TG_BOT_TOKEN)
    """
    
    TG_BOT_TOKEN: str
    OPENAI_API_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""
    LLM_PROVIDER: str = "openai"  # Primary provider (openai or replicate)
    LOG_LEVEL: str = "INFO"
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20MB
    MAX_ARCHIVE_SIZE: int = 100 * 1024 * 1024  # 100MB
    RESPONSE_THRESHOLD: int = 3  # Messages before generating docx
    TEMP_DIR: str = "./temp"
    OPENAI_MODEL: str = "gpt-4o"  # Fallback to gpt-4o if gpt-5 unavailable
    REPLICATE_MODEL: str = "openai/gpt-5"  # Replicate model
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    def validate_llm_config(self) -> bool:
        """Validate that at least one LLM provider is configured.
        
        Returns:
            bool: True if configuration is valid
            
        Raises:
            ValueError: If no LLM providers are configured
        """
        if not self.OPENAI_API_KEY and not self.REPLICATE_API_TOKEN:
            raise ValueError(
                "At least one LLM provider must be configured: "
                "OPENAI_API_KEY or REPLICATE_API_TOKEN"
            )
        
        if self.LLM_PROVIDER not in ("openai", "replicate"):
            raise ValueError(
                f"Invalid LLM_PROVIDER: {self.LLM_PROVIDER}. "
                "Must be 'openai' or 'replicate'"
            )
        
        # Check that primary provider is available
        if self.LLM_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY required when LLM_PROVIDER=openai"
            )
        if self.LLM_PROVIDER == "replicate" and not self.REPLICATE_API_TOKEN:
            raise ValueError(
                "REPLICATE_API_TOKEN required when LLM_PROVIDER=replicate"
            )
        
        return True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Uses @lru_cache to ensure only one Settings object is created
    during application lifetime.
    
    Returns:
        Settings: Application configuration
        
    Raises:
        ValidationError: If required env vars are missing or invalid
    """
    settings = Settings()
    settings.validate_llm_config()
    return settings
