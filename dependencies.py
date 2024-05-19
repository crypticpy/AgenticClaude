from anthropic import Anthropic
from tavily import TavilyClient
from config import settings
from exceptions import ConfigurationError

def get_anthropic_client() -> Anthropic:
    try:
        api_key = settings.ANTHROPIC_API_KEY
        anthropic_client = Anthropic(api_key=api_key)
        anthropic_client.api_url = "https://api.anthropic.com/v1/messages"
        anthropic_client.headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        return anthropic_client
    except Exception as e:
        raise ConfigurationError(f"Error configuring Anthropic client: {str(e)}") from e

def get_tavily_client() -> TavilyClient:
    try:
        api_key = settings.TAVILY_API_KEY
        tavily_client = TavilyClient(api_key=api_key)
        return tavily_client
    except Exception as e:
        raise ConfigurationError(f"Error configuring Tavily client: {str(e)}") from e