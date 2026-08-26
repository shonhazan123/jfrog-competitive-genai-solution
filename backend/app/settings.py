from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://ci:ci@db:5432/ci"
    config_dir: str = "/app/config"
    blob_dir: str = "/app/data/blobs"
    backfill_source: str = "live"
    fixtures_dir: str = "/app/fixtures/wayback"
    user_agent: str = "jfrog-ci-bot/0.1 (+contact: shonhazan19955@gmail.com)"

settings = Settings()
