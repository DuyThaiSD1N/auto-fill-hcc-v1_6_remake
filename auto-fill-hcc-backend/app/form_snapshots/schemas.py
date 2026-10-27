import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

MAX_VALUE_CHARS = 4000


class SnapshotField(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    comp: str = Field(default="", max_length=60)
    occurrence: int | None = None
    section: str | None = Field(default=None, max_length=200)
    label: str | None = Field(default=None, max_length=200)
    pos: int | None = None
    value: Any = None

    @field_validator("value")
    @classmethod
    def _small(cls, value: Any) -> Any:
        if len(json.dumps(value, ensure_ascii=False, default=str)) > MAX_VALUE_CHARS:
            raise ValueError("giá trị quá dài")
        return value


class FormSnapshotReq(BaseModel):
    snapshotId: str = Field(min_length=8, max_length=64)
    requestId: str = Field(min_length=1, max_length=64)
    kind: Literal["fill", "edit", "step"]
    trigger: str = Field(default="", max_length=120)
    host: str = Field(default="", max_length=200)
    path: str = Field(default="", max_length=500)
    at: int = Field(gt=0)
    fields: list[SnapshotField] = Field(max_length=600)
    extVersion: str = Field(default="", max_length=32)
