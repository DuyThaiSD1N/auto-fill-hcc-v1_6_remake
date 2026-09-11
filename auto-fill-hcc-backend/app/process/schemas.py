from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    # extra="allow": mapper được phép gắn thêm khoá điều khiển mới cho extension mà KHÔNG phải sửa
    # model này. Trước đây model lọc sạch khoá lạ nên scope/scopeNear/scopeAway/optionLabel do mapper
    # gắn bị BỎ ÂM THẦM giữa đường: extension nhận field trần, dò cả trang và điền vào khối đầu tiên
    # trùng tên. Không lỗi, không cảnh báo, nhìn từ hai đầu đều thấy "đúng".
    model_config = ConfigDict(extra="allow")

    name: str
    comp: str
    value: Any  # str | dict (x-select-area)
    default: bool = False  # True = giá trị BE điền mặc định (extension tô viền vàng), không từ giấy tờ
    # True = XÓA giá trị cổng đã điền sẵn ở ô này (dữ liệu VNeID của người khác), không phải điền.
    clear: bool = False
    occurrence: int | None = None  # Dùng khi Form.io tái sử dụng cùng name cho nhiều cụm field.

    # Khoanh vùng DOM khi nhiều khối trên cùng trang dùng chung field-key (xem mapper cap_lai_CCHN_thu_y).
    scope: str | None = None        # selector khối được phép điền
    scopeNear: str | None = None    # ô neo chỉ có trong khối đó, để thu hẹp khi selector còn rộng
    scopeAway: list[str] | None = None  # mốc của khối CẤM ghi
    # Chọn đúng option trong nhóm checkbox/selectboxes dùng chung một name.
    optionLabel: str | None = None
    optionValue: str | None = None


class ProcessResp(BaseModel):
    fields: list[FieldOut]
    extracted: dict[str, Any]
    stats: dict[str, Any]
    errors: list[str] = Field(default_factory=list)
    sessionId: str | None = None
    requestId: str | None = None
    # Capability ngắn hạn để UI tải sources/ảnh review; chỉ có khi pipeline sinh _review.
    reviewToken: str | None = None
    # Chế độ "fill tất cả trang" (đăng ký kinh doanh): {page_key: [field]} cho cả 8 trang.
    pages: dict[str, list[FieldOut]] | None = None
    # Metadata state machine HkdOnline (wizard tìm HKD + các trang thực sự cần sửa).
    businessFlow: dict[str, Any] | None = None
