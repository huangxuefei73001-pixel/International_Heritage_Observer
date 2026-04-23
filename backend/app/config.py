from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False, env_file=".env")

    database_url: str
    session_secret: str
    openrouter_api_key: str
    openrouter_model: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_sender: str
    library_path: str = "data/library/articles.jsonl"
    incoming_source_dir: str = "/Users/pauline/Desktop/国际遗产观察/3.26-国际观察mptext抓取/本次新增"
    sync_log_dir: str = "data/sync_logs"
    strict_source_mode: bool = True
