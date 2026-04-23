import os
import tempfile
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "invoice_db"
    postgres_host: str = "localhost"  # 'db' in Docker, 'localhost' locally
    postgres_port: int = 5432

    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000

    tmp_dir: Path = Path(tempfile.gettempdir()) / "invoices"
    debug: bool = True

    database_url: str = ""

    model_config = ConfigDict(extra="allow")


settings = Settings()
if os.name == "nt":
    settings.database_url = f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
settings.tmp_dir.mkdir(parents=True, exist_ok=True)
