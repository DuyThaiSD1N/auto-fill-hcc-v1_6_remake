"""Thanh tra GIẤY TỜ hồ sơ liên thông khai sinh: Giấy chứng nhận kết hôn của cha mẹ trẻ (số, quyển số, ngày đăng ký, nơi
đăng ký). Lượt trích hay bỏ sót giấy kết hôn hoặc chép thiếu số / quyển → một lượt LLM đọc lại riêng giấy kết hôn (cách
tìm mặc định của khung). Ô lượt trích bỏ trống thì bổ sung; hai bên lệch nhau thì chỉ đem ra xử khi mã thấy giá trị của
thanh tra có nguyên văn trên giấy còn của lượt trích thì không."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold

from . import trang

_OWNER = "giấy chứng nhận / trích lục kết hôn của cha mẹ trẻ"
UNITS = (Unit("gcn_ket_hon", "Giấy chứng nhận kết hôn của cha mẹ trẻ", (
    Field("GcnKetHon_So", "số đăng ký kết hôn, chép đủ như giấy (kể cả phần sau dấu /)", "code"),
    Field("GcnKetHon_QuyenSo", "quyển số, chép đủ như giấy (kể cả năm sau dấu /)", "code"),
    Field("GcnKetHon_NgayCap", "ngày đăng ký kết hôn dd/mm/yyyy", "date"),
    Field("GcnKetHon_NoiCap", "nơi đăng ký kết hôn (cơ quan), chép đủ như giấy", "free"),
)),)

RULES = """
<giay_ket_hon>
Chỉ lấy trên GIẤY CHỨNG NHẬN KẾT HÔN hoặc TRÍCH LỤC KẾT HÔN của chính cha mẹ trẻ (hai bên vợ / chồng trùng tên mẹ / cha
của trẻ trên giấy chứng sinh, CCCD). Không lấy số / ngày của giấy chứng sinh, giấy khai sinh, CCCD hay số bản sao trích lục
("…/TLKH-BS" là số của bản trích lục, không phải số đăng ký kết hôn). Trích lục có dòng "Đã đăng ký kết hôn tại: … Số: …
ngày …" thì lấy số / ngày / nơi theo dòng đó. Số và quyển số chép ĐỦ như giấy, kể cả phần năm sau dấu "/" ("Số: 12/2020",
"Quyển số: 01/2020"). Nơi đăng ký chép đủ tên cơ quan như giấy. Không có giấy kết hôn của cha mẹ trẻ → mọi mục null.
Toà: B là giá trị trên giấy kết hôn của chính cha mẹ trẻ; A bỏ trống, chép thiếu phần năm, hoặc lấy nhầm số của giấy khác →
chọn B. Dòng trích dẫn thuộc giấy khác (giấy chứng sinh, tờ khai...) → KHONG_DU_CAN_CU.
</giay_ket_hon>
"""

async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    """Chỉ đọc lại khi hồ sơ có trang giấy kết hôn (tiêu đề giấy chứng nhận / trích lục kết hôn) — hồ sơ không nộp giấy
    kết hôn thì không tốn một lượt model."""
    if not any("ket hon" in fold(" ".join(page["lines"][:12])) and page["kind"] == "ban_in"
               for page in trang.pages(case.documents)):
        return []
    return await engine.llm_findings(inspector, case, title)


INSPECTOR = Inspector("giay_to", "GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ trẻ", UNITS, RULES,
                      owners=(_OWNER, "giấy khác"), accepted=(_OWNER,), find=find)
