from datetime import datetime

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ArchiveSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    vault_url: str = ""
    vault_token: str = ""
    vault_timeout_s: int = 120
    vault_max_kbps: int = 0
    archive_hmac_key: str = ""
    archive_after_minutes: int = 30
    archive_send_delay_seconds: int = 10
    archive_poll_seconds: int = 30
    archive_live_poll_seconds: int = 5
    archive_batch: int = 50
    archive_concurrency: int = 16
    archive_since: datetime | None = None
    archive_require_ack_before: datetime | None = None

    @field_validator("archive_since", "archive_require_ack_before", mode="before")
    @classmethod
    def _blank_is_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @property
    def enabled(self) -> bool:
        return bool(self.vault_url)

    def cap_ttl(self, seconds: int) -> int:
        if not self.enabled:
            return seconds
        return min(seconds, self.archive_after_minutes * 60)


archive_settings = ArchiveSettings()
