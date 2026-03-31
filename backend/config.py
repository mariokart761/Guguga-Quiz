from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    supabase_url: str
    supabase_service_role_key: str
    supabase_anon_key: str
    allowed_origins: str = "http://localhost:3000"
    secret_key: str = "change-me-in-production"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
