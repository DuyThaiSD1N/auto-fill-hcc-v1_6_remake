from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.process.schemas import FileItem


class AttachmentPlanReq(BaseModel):
    procedure: str
    options: dict[str, Any] = Field(default_factory=dict)
    files: list[FileItem]


class AttachmentSourceSegment(BaseModel):
    """Một phần trang lấy từ file gốc để FE dựng lại tài liệu đính kèm.

    `pageIndexes` dùng chỉ số 0-based đúng với pdf-lib. Khi None, FE dùng toàn bộ file.
    Tách riêng contract này khỏi `sourceFileIndexes` để không đổi nghĩa gộp nguyên file đã có.
    """

    fileIndex: int = Field(ge=0)
    pageIndexes: list[Annotated[int, Field(ge=0)]] | None = None


class AttachmentPlanItem(BaseModel):
    fileIndex: int
    # Các file gốc (theo thứ tự) FE sẽ GỘP thành 1 PDF cho item này; None/1 phần tử = file lẻ.
    sourceFileIndexes: list[int] | None = None
    # Các đoạn trang (theo thứ tự) FE sẽ trích rồi gộp thành 1 PDF. Chỉ planner cần tách tài liệu
    # trong cùng một PDF mới trả field này; planner cũ không bị thay đổi hành vi.
    sourceSegments: list[AttachmentSourceSegment] | None = None
    fileName: str
    documentName: str
    componentName: str = ""
    # "supplementary": ô đính kèm bổ sung ngoài danh mục (vd cổng Bắc Ninh: fsfile...fileDinhKem)
    # — FE gán file vào input bổ sung, không cần componentName.
    # "attp-row": bảng-checkbox Angular CDK (vd ATTP cấp lại — Bộ Công Thương): mỗi dòng có checkbox +
    # radio Bản chính/Bản sao + ô upload; FE khớp dòng theo componentName, tick + chọn loaiBan + set file.
    # "add-document-dialog": cổng Angular có nút "Thêm giấy tờ"; FE chọn componentName trong modal,
    # tạo dòng mới rồi dùng lại engine attp-row để upload.
    target: Literal["existing", "new", "fixed-slot", "supplementary", "attp-row", "add-document-dialog"]
    componentIndex: int | None = None
    needsAddComponent: bool
    detectedType: str | None = None
    # Quan hệ hồ sơ khi một batch Chứng thực chữ ký được chia thành nhiều tab. Các planner khác
    # không trả ba field này nên hợp đồng cũ vẫn giữ nguyên.
    bundleId: str | None = None
    bundleRole: Literal["signature_document", "identity"] | None = None
    # shared: một giấy tùy thân dùng chung và chỉ đính ở tab đầu; matched: giấy tùy thân khớp riêng
    # với người ký của bundle.
    identityScope: Literal["shared", "matched"] | None = None
    # Dùng cho target "fixed-slot" (vd Hỗ trợ mai táng): chỉ định ô upload cố định trên form.
    slotKey: str | None = None
    slotIndex: int | None = None
    slotName: str | None = None
    # Ô DỰ PHÒNG khi cổng chặn tổng dung lượng của một loại giấy tờ (khai sinh liên thông:
    # "không được quá 2.6MB"). FE chỉ dùng khi cổng THẬT SỰ báo quá dung lượng — không phải
    # đường đi mặc định. Planner chỉ gắn cho giấy tờ được phép dời ô.
    fallbackSlotKey: str | None = None
    fallbackSlotIndex: int | None = None
    fallbackSlotName: str | None = None
    # Với một số cổng, cùng một dòng giấy tờ chỉ nhận một file mỗi lần bấm "Chọn tệp tin".
    # FE sẽ mở lại đúng slot và upload từng file thay vì gộp nhiều file vào một input.
    repeatUpload: bool | None = None
    # Dùng cho đăng ký hộ kinh doanh (cổng HkdOnline): loại tài liệu cổng — "BUSREGFRM" | "OTHERS".
    # FE tự suy attId (ô modal khai báo) + droptypleValue (ô "Loại đính kèm") từ category.
    category: str | None = None
    # Dùng cho target "attp-row": chọn radio "Bản chính"/"Bản sao" trên dòng giấy tờ.
    loaiBan: str | None = None
    # Số bản khai trong modal "Thêm giấy tờ" trước khi dòng upload được tạo.
    quantity: int | None = Field(default=None, ge=1)


class AttachmentPlanResp(BaseModel):
    attachments: list[AttachmentPlanItem]
    extracted: dict[str, Any] = Field(default_factory=dict)
    stats: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    # Mã hỗ trợ (request_id) trả về FE để cán bộ copy. KHÔNG khai báo ở đây thì response_model
    # sẽ LƯỢC MẤT field router gắn vào result → FE không hiện được chip mã hỗ trợ.
    requestId: str | None = None
    # Directive hotfix (chỉ Chứng thực bản sao, tài khoản Đà Nẵng/Hải Châu): yêu cầu extension
    # chèn 1 file ẢO (copy đổi tên của file thật) vào ô STT1. Không khai ở đây thì response_model
    # lược mất → extension không nhận được directive. None với mọi trường hợp khác.
    stt1VirtualCopy: dict[str, Any] | None = None


class ClientAttachmentFileMeta(BaseModel):
    """Metadata file do extension tự đính; tuyệt đối không chứa nội dung file."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    type: str = "application/octet-stream"
    role: str = "attachment"
    size: int = Field(default=0, ge=0)


class ClientAttachmentTraceReq(BaseModel):
    """Ghi trace cho case đính kèm hoàn toàn tại trình duyệt."""

    procedure: str
    options: dict[str, Any] = Field(default_factory=dict)
    files: list[ClientAttachmentFileMeta]
    attachments: list[AttachmentPlanItem]


class ClientAttachmentTraceResp(BaseModel):
    requestId: str
