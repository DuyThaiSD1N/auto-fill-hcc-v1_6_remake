"""Thanh tra ĐƠN VỊ THIẾT KẾ cấp giấy phép xây dựng mới: tổ chức lập thiết kế (tên, mã số doanh nghiệp) và chủ nhiệm thiết kế
(họ tên, số chứng chỉ hành nghề). Đơn hay viết tắt tên công ty, chép lẫn mã chứng chỉ năng lực vào ô mã số doanh nghiệp;
chứng chỉ năng lực / giấy đăng ký doanh nghiệp / khung tên bản vẽ in đủ."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Inspector, Unit, fold

from ..process import mapper
from . import chung

_TO_CHUC = Unit("to_chuc", "Tổ chức lập thiết kế", (
    Field("ThietKe_ToChuc_Ten", "tên tổ chức lập thiết kế"),
    Field("ThietKe_ToChuc_MaSo", "mã số doanh nghiệp 10 chữ số (chi nhánh 10-3) của tổ chức lập thiết kế", "code"),
))
_CHU_NHIEM = Unit("chu_nhiem", "Chủ nhiệm thiết kế", (
    Field("ThietKe_ChuNhiem_HoTen", "họ tên chủ nhiệm thiết kế (bỏ học vị KS./KTS.)"),
    Field("ThietKe_ChuNhiem_ChungChi", "số chứng chỉ hành nghề của CHÍNH chủ nhiệm", "code"),
))
UNITS = (_TO_CHUC, _CHU_NHIEM)

RULES = """
<nguon>
- Tên tổ chức lập thiết kế: tên pháp nhân ĐẦY ĐỦ như trên chứng chỉ năng lực / giấy đăng ký doanh nghiệp / khung tên bản
  vẽ in (đơn hay viết tắt "TNHH MTV", "CTY"). Mã số doanh nghiệp: CHỈ 10 chữ số (chi nhánh 10-3), không phải mã chứng chỉ
  năng lực ("XXX 000…").
- Chủ nhiệm thiết kế: người mà dòng của CHÍNH người đó ghi vai trò "Chủ nhiệm" (danh sách trong đơn, bản kê kinh nghiệm,
  khung tên "Chủ nhiệm thiết kế"). Người chỉ "Chủ trì" không phải chủ nhiệm. Số chứng chỉ lấy trên cùng dòng / chứng chỉ
  hành nghề của chính người đó.
- Hồ sơ "gia đình tự thiết kế" / cá nhân thiết kế không có tổ chức → các mục này null.
</nguon>

<cach_phan_xu>
- A bỏ trống mà giấy có ghi → chọn B.
- A là tên viết tắt / thiếu chữ của CÙNG tổ chức, B là tên đầy đủ trên giấy in → chọn B.
- Mã số doanh nghiệp của A không phải 10 chữ số (tín hiệu mã), B hợp lệ trên giấy → chọn B.
- B là người / mã của dòng khác (người chủ trì, giám đốc công ty) → KHONG_DU_CAN_CU.
</cach_phan_xu>
"""


def signals(unit: Unit, values: dict, case: Case) -> list[tuple[bool, str]]:
    if unit is _TO_CHUC and values.get("ThietKe_ToChuc_MaSo"):
        valid = mapper._ma_so_doanh_nghiep(values["ThietKe_ToChuc_MaSo"]) is not None
        return [(valid, "mã số doanh nghiệp " + ("hợp lệ (10 chữ số)" if valid else "KHÔNG phải mã 10 chữ số"))]
    return []


# Tên tổ chức phải có dấu hiệu là pháp nhân: "gia đình tự lập", tên người không phải tổ chức thiết kế.
_ORG_MARKERS = ("cong ty", "cty", "doanh nghiep", "trung tam", "vien ", "van phong", "hop tac xa", "tnhh", "co phan",
                "chi nhanh", "xi nghiep")


def check(unit: Unit, values: dict, case: Case) -> str:
    name = values.get("ThietKe_ToChuc_Ten")
    if unit is _TO_CHUC and name and not any(marker in f" {fold(name)} " for marker in _ORG_MARKERS):
        return "tên tổ chức lập thiết kế không phải pháp nhân (gia đình / cá nhân tự lập)"
    return ""


# Trang đơn (mục tổ chức lập thiết kế), chứng chỉ năng lực / hành nghề, bản kê kinh nghiệm, khung tên bản vẽ.
_MARKERS = ("thiet ke", "chung chi", "chu nhiem", "chu tri", "nang luc", "dang ky doanh nghiep", "ma so doanh nghiep")


async def find(inspector: Inspector, case: Case, title: str):
    findings = await engine.llm_findings(inspector, chung.narrowed(case, _MARKERS), title)
    # Chủ nhiệm chỉ nhận khi chính dòng chứng cứ ghi vai trò "chủ nhiệm" (người chủ trì / giám đốc không phải chủ nhiệm).
    return [finding for finding in findings
            if finding.unit is not _CHU_NHIEM or "chu nhiem" in fold(finding.quote)]


_ACCEPTED = (chung.DON, chung.CHUNG_CHI, chung.BAN_VE)
INSPECTOR = Inspector("thiet_ke", "ĐƠN VỊ THIẾT KẾ (tổ chức lập thiết kế, chủ nhiệm thiết kế)", UNITS, RULES, check,
                      signals=signals, owners=chung.OWNERS, accepted=_ACCEPTED, find=find)
