from typing import Any, Literal

from pydantic import BaseModel, Field

from app.process.schemas import FileItem


class AttachmentPlanReq(BaseModel):
    procedure: str
    options: dict[str, Any] = Field(default_factory=dict)
    files: list[FileItem]


class AttachmentPlanItem(BaseModel):
    fileIndex: int
    # Các file gốc (theo thứ tự) FE sẽ GỘP thành 1 PDF cho item này; None/1 phần tử = file lẻ.
    sourceFileIndexes: list[int] | None = None
    fileName: str
    documentName: str
    componentName: str = ""
    # "supplementary": ô đính kèm bổ sung ngoài danh mục (vd cổng Bắc Ninh: fsfile...fileDinhKem)
    # — FE gán file vào input bổ sung, không cần componentName.
    target: Literal["existing", "new", "fixed-slot", "supplementary"]
    componentIndex: int | None = None
    needsAddComponent: bool
    detectedType: str | None = None
    # Dùng cho target "fixed-slot" (vd Hỗ trợ mai táng): chỉ định ô upload cố định trên form.
    slotKey: str | None = None
    slotIndex: int | None = None
    slotName: str | None = None
    # Với một số cổng, cùng một dòng giấy tờ chỉ nhận một file mỗi lần bấm "Chọn tệp tin".
    # FE sẽ mở lại đúng slot và upload từng file thay vì gộp nhiều file vào một input.
    repeatUpload: bool | None = None
    # Dùng cho đăng ký hộ kinh doanh (cổng HkdOnline): loại tài liệu cổng — "BUSREGFRM" | "OTHERS".
    # FE tự suy attId (ô modal khai báo) + droptypleValue (ô "Loại đính kèm") từ category.
    category: str | None = None


class AttachmentPlanResp(BaseModel):
    attachments: list[AttachmentPlanItem]
    extracted: dict[str, Any] = Field(default_factory=dict)
    stats: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
