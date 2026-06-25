from agentic_service_py_template.config import Settings

def test_settings_defaults():
    s = Settings(_env_file=None)  # type: ignore[call-arg]  # no env file, use defaults
    assert s.http_host == "0.0.0.0"
    assert s.http_port == 8000

def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("ASPT_DB_CONNECTION_STRING", "sqlite:///test.db")
    monkeypatch.setenv("ASPT_LLM_ENDPOINT", "https://models.inference.ai.azure.com")
    monkeypatch.setenv("ASPT_LLM_API_KEY", "test-key")
    monkeypatch.setenv("ASPT_AUTH_JWT_SECRET", "test-secret")
    s = Settings()
    assert s.db_connection_string == "sqlite:///test.db"
    assert s.llm_endpoint == "https://models.inference.ai.azure.com"
    assert s.llm_api_key.get_secret_value() == "test-key"  # type: ignore[union-attr]
    assert s.auth_jwt_secret == "test-secret"
