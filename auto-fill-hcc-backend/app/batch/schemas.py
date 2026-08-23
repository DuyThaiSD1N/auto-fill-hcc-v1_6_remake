from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class BatchJobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    procedure: str = Field(min_length=1, max_length=160)

    @field_validator("name", "procedure")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("Không được để trống")
        return value


class BatchFileMetadata(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    type: str | None = Field(default=None, max_length=160)
    role: str = Field(default="doc", max_length=120)
    hasHandwriting: bool = False


class BatchItemMetadata(BaseModel):
    clientDossierId: str = Field(min_length=1, max_length=180)
    options: dict[str, Any] = Field(default_factory=dict)
    files: list[BatchFileMetadata] = Field(default_factory=list)

    @field_validator("clientDossierId")
    @classmethod
    def _strip_dossier_id(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("Mã hồ sơ không được để trống")
        return value
