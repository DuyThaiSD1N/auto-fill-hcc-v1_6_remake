from typing import Any

from pydantic import BaseModel, Field


class FileItem(BaseModel):
    name: str
    type: str
    dataUrl: str
    role: str


class ProcessReq(BaseModel):
    procedure: str
    options: dict[str, Any] = Field(default_factory=dict)
    files: list[FileItem]


class FieldOut(BaseModel):
    name: str
    comp: str
    value: Any  # str | dict (x-select-area)
    default: bool = False  # True = giá trị BE điền mặc định (extension tô viền vàng), không từ giấy tờ
    occurrence: int | None = None  # Dùng khi Form.io tái sử dụng cùng name cho nhiều cụm field.


class ProcessResp(BaseModel):
    fields: list[FieldOut]
    extracted: dict[str, Any]
    stats: dict[str, Any]
    errors: list[str] = Field(default_factory=list)
    sessionId: str | None = None
    requestId: str | None = None
    # Chế độ "fill tất cả trang" (đăng ký kinh doanh): {page_key: [field]} cho cả 8 trang.
    pages: dict[str, list[FieldOut]] | None = None
    # Metadata state machine HkdOnline (wizard tìm HKD + các trang thực sự cần sửa).
    businessFlow: dict[str, Any] | None = None
