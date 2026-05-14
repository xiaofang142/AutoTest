from pydantic_settings import BaseSettings


from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+asyncpg://autotest:autotest@localhost:5432/autotest"
    redis_url: str = "redis://localhost:6379/0"
    litellm_api_key: str = ""
    litellm_api_base: str = "https://api.openai.com/v1"
    extraction_model: str = "gpt-4o"
    analysis_model: str = "gpt-4o-mini"
    storage_backend: str = "local"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "autotest"
    executor_mode: str = "real"
    executor_web_url: str = "http://localhost:3100"
    executor_android_url: str = "http://localhost:3101"
    executor_ios_url: str = "http://localhost:3102"
    log_level: str = "INFO"


settings = Settings()
