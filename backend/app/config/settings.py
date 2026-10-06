import logging
from functools import lru_cache

from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Kept as the default so a developer with no .env still boots and sees the
# problem below rather than an ImportError at module load.
PLACEHOLDER_SECRET_KEY = "change-this-secret-key"


class Settings(BaseSettings):
    APP_NAME: str = "AI LifeOS API"
    APP_VERSION: str = "1.0.0"

    # Off by default. Debug mode makes FastAPI return full tracebacks for
    # unhandled errors, which leaks internals to clients. Opt in explicitly with
    # DEBUG=true while developing.
    #
    # Declared before SECRET_KEY because the SECRET_KEY validator below reads
    # `info.data["DEBUG"]`, which only holds fields validated before it.
    DEBUG: bool = False

    DATABASE_URL: str = (
        "postgresql://postgres:password@localhost:5432/ailifeos"
    )

    SECRET_KEY: str = PLACEHOLDER_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Browser origins allowed to call this API with credentials, as a
    # comma-separated string. The localhost defaults in `main.py` keep
    # `npm run dev` working with no configuration; production sets this to its
    # own origin(s).
    CORS_ORIGINS: str = ""

    def allowed_origins(self) -> list[str]:
        """Resolve the configured origins, ignoring blank entries."""

        return [
            item.strip()
            for item in self.CORS_ORIGINS.split(",")
            if item.strip()
        ]

    @field_validator("SECRET_KEY")
    @classmethod
    def _reject_placeholder_in_production(
        cls,
        value: str,
        info: ValidationInfo,
    ) -> str:
        """
        Fail closed when the placeholder secret would be used in production.

        The placeholder makes every JWT forgeable, so anyone could authenticate
        as any user. Local development keeps working (DEBUG=true is the dev
        signal used throughout this project), but a non-debug deployment must
        refuse to boot rather than serve forgeable tokens.
        """

        if value != PLACEHOLDER_SECRET_KEY:
            return value

        if (info.data or {}).get("DEBUG"):
            logger.warning(
                "SECRET_KEY is still the placeholder value. This is fine for "
                "local development only — set SECRET_KEY in .env before "
                "deploying."
            )
            return value

        raise ValueError(
            "SECRET_KEY is the placeholder value and DEBUG is false. Set a real "
            "SECRET_KEY in the environment before serving this application: with "
            "the placeholder, tokens can be forged for any user."
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()