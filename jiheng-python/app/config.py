from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "jiheng-python"
    debug: bool = False

    jwt_secret: str = "jiheng-dev-secret-change-me-in-production-at-least-32-chars"
    jwt_issuer: str = "jiheng-ai"

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 2

    java_internal_base_url: str = "http://127.0.0.1:8080"
    service_token: str = "dev-service-token-change-me"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model_quick: str = "deepseek-flash"
    deepseek_model_deep: str = "deepseek-v4-pro"
    agent_runtime: str = "harness-sdk"
    agent_allow_tool_calls_fallback: bool = False
    dsh_home: str = "./data/dsh-home"
    dsh_workspace: str = "./data/dsh-workspace"
    dsh_template_home: str = "./data/dsh-template"
    harness_profile_patch: str = "./harness/jiheng.cordis.patch.yml"

    search_api_url: str = ""
    search_api_key: str = ""
    quote_api_url: str = ""
    quote_api_key: str = ""
    research_api_url: str = ""
    research_api_key: str = ""

    trace_store_dir: str = "./data/traces"
    financial_mcp_url: str = "https://mcp.agentladle.com/mcp"
    financial_mcp_api_key: str = ""
    cninfo_cache_dir: str = "./data/cninfo"
    data_request_timeout_seconds: float = 15

    model_config = {"env_prefix": "JIHENG_", "env_file": ".env"}


settings = Settings()
