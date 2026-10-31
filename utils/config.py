import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    base_url: str | None
    user_email: str | None = field(repr=False)
    user_password: str | None = field(repr=False)

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> "Settings":
        values = os.environ if environ is None else environ
        base_url = values.get("BASE_URL", "").strip().rstrip("/") or None
        user_email = values.get("USER_EMAIL", "").strip() or None
        password = values.get("USER_PASSWORD", "")
        user_password = password if password.strip() else None
        return cls(
            base_url=base_url,
            user_email=user_email,
            user_password=user_password,
        )
