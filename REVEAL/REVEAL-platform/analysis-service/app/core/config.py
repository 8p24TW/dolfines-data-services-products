from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    weather_cache_path: str = "/app/cache/weather_cache.json"
    long_term_cache_dir: str = "/app/cache/long-term"
    tmp_dir: str = "/tmp/reveal-analysis"
    playwright_browsers_path: str = "/ms-playwright"
    log_level: str = "info"
    cds_api_url: str | None = None
    cds_api_key: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
