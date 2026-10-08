import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    memory_db_path: str = "data/memory.db"
    kb_min_score: float = 1.0


def get_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        memory_db_path=os.getenv("MEMORY_DB_PATH", "data/memory.db"),
    )
