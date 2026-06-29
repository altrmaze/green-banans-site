from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Greens ACC API"
    app_description: str = "Multi-Agent International Trading & Accounting Core Engine"
    app_version: str = "1.0.0"
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_prefix="GREENS_ACC_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
