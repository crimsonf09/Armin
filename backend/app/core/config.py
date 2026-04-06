from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agentic Chat Backend"
    api_prefix: str = "/api"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "agentic_chat"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file="env.example", env_file_encoding="utf-8")


settings = Settings()
