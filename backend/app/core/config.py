from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/leave_expense"
    random_seed: int = 20261022
    openai_api_key: str | None = None
    llm_model: str | None = None

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30


    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
