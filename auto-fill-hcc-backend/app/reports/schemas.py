from typing import Literal

from pydantic import BaseModel, Field, model_validator


SelectionMode = Literal["province", "accounts"]


class ExcelExportRequest(BaseModel):
    dateFrom: str = Field(min_length=10, max_length=35)
    dateTo: str = Field(min_length=10, max_length=35)
    selectionMode: SelectionMode
    province: str | None = Field(default=None, max_length=120)
    officialOnly: bool = False
    accountIds: list[str] = Field(default_factory=list, max_length=200)
    includeHandfree: bool = False

    @model_validator(mode="after")
    def validate_selection(self):
        self.dateFrom = self.dateFrom.strip()
        self.dateTo = self.dateTo.strip()
        self.province = (self.province or "").strip() or None
        self.accountIds = list(dict.fromkeys(value.strip() for value in self.accountIds if value.strip()))
        if self.selectionMode == "province" and not self.province:
            raise ValueError("Vui lòng chọn tỉnh/thành cần xuất báo cáo.")
        if self.selectionMode == "accounts" and not self.accountIds:
            raise ValueError("Vui lòng chọn ít nhất một tài khoản.")
        return self
