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

    tmp_dir: Path = Path() / ".temp"
    postgres_url: str = ""
    debug: bool = False

    model_config = ConfigDict(extra="allow")

    def build_postgres_url(self):
        self.postgres_url = f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


settings = Settings()
settings.tmp_dir.mkdir(parents=True, exist_ok=True)
if settings.debug:
    settings.build_postgres_url()

# PARSER CONFIG

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def construct_file_path(invoice_id, file_type):
    return (settings.tmp_dir / f"{invoice_id}.{file_type}").resolve().absolute()
