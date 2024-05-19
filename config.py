from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Anthropic API settings
    ANTHROPIC_API_KEY: str
    ORCHESTRATOR_MODEL: str = "claude-3-opus-20240229"
    SUB_AGENT_MODEL: str = "claude-3-sonnet-20240229"
    REFINER_MODEL: str = "claude-3-opus-20240229"
    TAVILY_API_KEY: str

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"

    # Output settings
    TIMESTAMP_FORMAT: str = "%Y-%m-%d_%H-%M-%S"
    MAX_OBJECTIVE_LENGTH: int = 50

    # Retry settings
    RETRY_ATTEMPTS: int = 5
    RETRY_DELAY: int = 10

    class Config:
        env_file = ".env"

settings = Settings()