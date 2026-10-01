"""Application settings, loaded from env / .env via pydantic-settings."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Export .env into os.environ so third-party libs (LiteLLM reads OPENROUTER_API_KEY,
# OPENAI_API_KEY, ... directly from the environment) actually see the keys.
# pydantic-settings alone only populates the Settings object, not os.environ.
load_dotenv()

# Project root (…/HeadOfSocialMediaAgent) — used to anchor relative data/db paths so they
# don't depend on the process's current working directory.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Fallback role -> model map (overridable via env in LLM_ROLE_<ROLE>).
_DEFAULT_ROLE_MODELS = {
    "positioning": "openai/gpt-4o",
    "planning": "openai/gpt-4o",
    "content": "openai/gpt-4o",
    "publishing": "openai/gpt-4o-mini",
    "orchestrator": "gemini/gemini-3-flash-preview",
    "default": "gemini/gemini-3-flash-preview",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="HEADSOF_", extra="ignore")

    app_name: str = "headofsocial"
    db_url: str = "sqlite+aiosqlite:///./data/headofsocial.db"
    data_dir: Path = Path("./data")

    # Media budget (hard caps per asset).
    max_images_per_asset: int = 5
    max_videos_per_asset: int = 2

    # Media provider: "mock" | "litellm".
    media_provider: str = "mock"

    # Web research (Tavily). provider "none" disables research gracefully.
    research_provider: str = "tavily"
    tavily_api_key: str = ""
    max_research_queries_per_run: int = 10
    research_cache_ttl_days: int = 7

    # Image-generation model (LiteLLM string). Used when media_provider=litellm.
    # Examples: gemini/imagen-3.0-generate-002, openai/gpt-image-1, vertex_ai/imagen-3.0-generate-002
    media_image_model: str = "gemini/imagen-3.0-generate-002"
    media_image_size: str = ""  # e.g. "1024x1024"; empty = provider default

    # LLM role -> model strings. Prefix HEADSOF_LLM_ROLE_<ROLE>.
    llm_role_positioning: str = _DEFAULT_ROLE_MODELS["positioning"]
    llm_role_planning: str = _DEFAULT_ROLE_MODELS["planning"]
    llm_role_content: str = _DEFAULT_ROLE_MODELS["content"]
    llm_role_publishing: str = _DEFAULT_ROLE_MODELS["publishing"]
    llm_role_orchestrator: str = _DEFAULT_ROLE_MODELS["orchestrator"]
    llm_role_default: str = _DEFAULT_ROLE_MODELS["default"]

    @property
    def role_models(self) -> dict[str, str]:
        return {
            "positioning": self.llm_role_positioning,
            "planning": self.llm_role_planning,
            "content": self.llm_role_content,
            "publishing": self.llm_role_publishing,
            "orchestrator": self.llm_role_orchestrator,
            "default": self.llm_role_default,
        }

    @property
    def resolved_data_dir(self) -> Path:
        p = self.data_dir
        if not p.is_absolute():
            p = _PROJECT_ROOT / p
        return p.resolve()

    @property
    def resolved_brand_assets_dir(self) -> Path:
        return self.resolved_data_dir / "brand_assets"

    @property
    def resolved_db_url(self) -> str:
        """Absolute sqlite URL anchored at the project root (CWD-independent).

        Prevents a server started from a different directory from opening/locking a
        different database file than the one the tools write to.
        """
        url = self.db_url
        if url.startswith("sqlite") and ":///" in url:
            prefix, _, rest = url.partition(":///")
            if rest.startswith("/"):
                return url  # already absolute
            return f"{prefix}:///{(_PROJECT_ROOT / rest).resolve()}"
        return url


settings = Settings()