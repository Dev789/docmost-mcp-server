import pytest
from pydantic import ValidationError
from docmost_mcp.config import DocmostConfig
from docmost_mcp.exceptions import DocmostConfigError

def test_config_valid_token(monkeypatch):
    monkeypatch.setenv("DOCMOST_BASE_URL", "https://docs.example.com")
    monkeypatch.setenv("DOCMOST_API_TOKEN", "test-token")
    
    config = DocmostConfig() # type: ignore
    assert config.normalised_base_url == "https://docs.example.com"
    assert config.api_token == "test-token"
    assert config.uses_bearer_token is True

def test_config_valid_login(monkeypatch):
    monkeypatch.setenv("DOCMOST_BASE_URL", "https://docs.example.com/")
    monkeypatch.setenv("DOCMOST_EMAIL", "test@example.com")
    monkeypatch.setenv("DOCMOST_PASSWORD", "secret")
    
    config = DocmostConfig() # type: ignore
    assert config.normalised_base_url == "https://docs.example.com"
    assert config.email == "test@example.com"
    assert config.uses_bearer_token is False

def test_config_missing_auth(monkeypatch):
    monkeypatch.setenv("DOCMOST_BASE_URL", "https://docs.example.com")
    # Clean env for other vars
    monkeypatch.delenv("DOCMOST_API_TOKEN", raising=False)
    monkeypatch.delenv("DOCMOST_EMAIL", raising=False)
    monkeypatch.delenv("DOCMOST_PASSWORD", raising=False)
    
    with pytest.raises(DocmostConfigError):
        DocmostConfig() # type: ignore

def test_config_invalid_url(monkeypatch):
    # BaseSettings will raise if a required field is missing
    monkeypatch.delenv("DOCMOST_BASE_URL", raising=False)
    with pytest.raises(ValidationError):
        DocmostConfig() # type: ignore
