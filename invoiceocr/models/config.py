from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


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
    temporal_url: str = "temporal:7233"
    debug: bool = False

    openai_api_key: str = ""

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = ""

    model_config = ConfigDict(extra="allow")

    def build_postgres_url(self):
        self.postgres_url = f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    def construct_file_path(self, invoice_id, file_type):
        return (self.tmp_dir / f"{invoice_id}.{file_type}").resolve().absolute()


settings = Settings()
settings.tmp_dir.mkdir(parents=True, exist_ok=True)
if settings.debug:
    settings.build_postgres_url()
