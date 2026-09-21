"""Cha/mẹ trùng tên với con thì KHÔNG được xoá trắng vai đó.

Con trai đặt trùng tên bố là chuyện thường trong hồ sơ hộ tịch. Trước đây hai chốt chặn đều
xử theo tên trần:

* `_validate_family_sections` (bước phân vai) xoá vai cha khi không có gì phân biệt;
* `sanitize_extracted_fields` (bước hậu kiểm) xoá THẲNG mọi field `Father_*` chỉ vì tên trùng,
  bất kể cha có CCCD riêng hay năm sinh khác — và vì vai bị xếp vào `broken_prefixes` nên bước
  dựng lại cha/mẹ cũng không cứu được. Kết quả: extension không điền được ô nào của cha.

Cùng một đoạn code nằm ở hai pipeline khai sinh nên test chạy cho cả hai.
"""
import pytest

from app.pipelines.khai_sinh_co_ho_so.process import reason as co_ho_so
from app.pipelines.khai_sinh_dang_ky_lai.process import reason as dang_ky_lai

REASON_MODULES = pytest.mark.parametrize(
    "reason",
    [dang_ky_lai, co_ho_so],
    ids=["dang_ky_lai", "co_ho_so"],
)

_CON = "Nguyễn Văn An"
_ME = "Trần Thị Bé"


def _section(name, id_number="", birth="", gender="", basis="Kết quả agent."):
    """Khối vai theo đúng shape mà bước phân vai dựng ra."""
    return (
        f"Họ tên: {name}\n"
        f"Số CCCD/CMND: {id_number or 'Không xác định'}\n"
        f"Ngày sinh: {birth or 'Không xác định'}\n"
        f"Giới tính: {gender or 'Không xác định'}\n"
        "Dân tộc: Kinh\n"
        "Quốc tịch: Việt Nam\n"
        "Trạng thái: còn sống\n"
        "Nguồn: to-khai.pdf\n"
        f"Căn cứ phân vai: {basis}"
    )


def _declared(reason, **kwargs):
    """Khối vai đọc từ nhãn quan hệ IN SẴN trên tờ khai."""
    return _section(basis=f"{reason._DECLARATION_BASIS_PREFIX} khai sinh.", **kwargs)


def _fields(**overrides):
    values = {
        "Subject_FullName": _CON,
        "Subject_BirthDate": "10/05/2000",
        "Subject_IdNumber": "001200000001",
        "Subject_Gender": "Nam",
        "Father_FullName": _CON,
        "Father_IdNumber": "001070000003",
        "Father_BirthDateOrYear": "1970",
        "Father_Gender": "Nam",
        "Father_Nationality": "Việt Nam",
        "Mother_FullName": _ME,
        "Mother_IdNumber": "001175000002",
        "Mother_BirthDateOrYear": "1975",
        "Mother_Gender": "Nữ",
    }
    values.update(overrides)
    return [
        {"name": name, "comp": "x-input", "value": value}
        for name, value in values.items()
    ]


def _kept(reason, fields, prefix="Father_"):
    result = reason.sanitize_extracted_fields(fields, "")
    return [field["name"] for field in result if field["name"].startswith(prefix)]


# --------------------------------------------------------------------------------------
# Lớp 2: hậu kiểm sau khi trích xuất — lỗi gốc của báo cáo "không điền được thông tin cha"
# --------------------------------------------------------------------------------------


@REASON_MODULES
def test_cha_trung_ten_con_nhung_khac_cccd_thi_giu_nguyen(reason):
    assert _kept(reason, _fields()) == [
        "Father_FullName",
        "Father_IdNumber",
        "Father_BirthDateOrYear",
        "Father_Gender",
        "Father_Nationality",
    ]


@REASON_MODULES
def test_cha_trung_ten_con_chi_khac_nam_sinh_thi_giu_nguyen(reason):
    fields = _fields(Father_IdNumber="", Subject_IdNumber="")

    assert "Father_FullName" in _kept(reason, fields)


@REASON_MODULES
def test_cha_trung_ten_con_chi_khac_gioi_tinh_thi_giu_nguyen(reason):
    fields = _fields(
        Subject_Gender="Nữ",
        Father_IdNumber="",
        Subject_IdNumber="",
        Father_BirthDateOrYear="",
    )

    assert "Father_FullName" in _kept(reason, fields)


@REASON_MODULES
def test_me_trung_ten_con_nhung_khac_cccd_thi_giu_nguyen(reason):
    # Cha mang tên khác để KIỂM TRA 0A (cha trùng tên mẹ) không che mất phép kiểm tra cần đo.
    fields = _fields(
        Mother_FullName=_CON,
        Father_FullName="Nguyễn Văn Bốn",
        Subject_Gender="Nữ",
    )

    assert "Mother_FullName" in _kept(reason, fields, "Mother_")


@REASON_MODULES
def test_cha_cung_cccd_voi_con_thi_van_bi_xoa(reason):
    fields = _fields(Father_IdNumber="001200000001")

    assert _kept(reason, fields) == []


@REASON_MODULES
def test_cha_trung_ten_con_va_khong_co_gi_phan_biet_thi_van_bi_xoa(reason):
    fields = _fields(
        Father_IdNumber="",
        Subject_IdNumber="",
        Father_BirthDateOrYear="",
        Father_Gender="",
    )

    assert _kept(reason, fields) == []


@REASON_MODULES
def test_cha_cung_ngay_sinh_voi_con_thi_van_bi_xoa(reason):
    """KIỂM TRA 2B: trùng cả ngày sinh nghĩa là dữ liệu con bị chép sang vai cha."""
    fields = _fields(Father_IdNumber="", Father_BirthDateOrYear="10/05/2000")

    assert _kept(reason, fields) == []


@REASON_MODULES
def test_vai_me_bi_loai_khong_lam_tat_phep_kiem_tra_vai_cha(reason):
    """Trước đây chỉ cần một vai đã bị loại là phép kiểm tra cha-trùng-con bị bỏ qua hẳn."""
    fields = _fields(
        Mother_Gender="Nam",  # KIỂM TRA 0D loại vai mẹ trước
        Father_IdNumber="",
        Subject_IdNumber="",
        Father_BirthDateOrYear="",
        Father_Gender="",
    )

    assert _kept(reason, fields) == []
    assert _kept(reason, fields, "Mother_") == []


@REASON_MODULES
def test_cha_khac_ten_con_khong_bi_dung_toi(reason):
    fields = _fields(Father_FullName="Nguyễn Văn Bốn")

    assert "Father_FullName" in _kept(reason, fields)


# --------------------------------------------------------------------------------------
# Lớp 1: bước phân vai
# --------------------------------------------------------------------------------------


@REASON_MODULES
def test_to_khai_ghi_ro_hai_nhan_quan_he_thi_giu_vai_cha(reason):
    sections = {
        "con": _declared(reason, name=_CON, gender="Nam"),
        "cha": _declared(reason, name=_CON, gender="Nam"),
        "me": _declared(reason, name=_ME, gender="Nữ"),
    }

    result = reason._validate_family_sections(sections)

    assert reason._role_name(result["cha"]) == _CON


@REASON_MODULES
def test_to_khai_ghi_ro_nhung_cung_cccd_thi_van_xoa_vai_cha(reason):
    sections = {
        "con": _declared(reason, name=_CON, id_number="001200000001", gender="Nam"),
        "cha": _declared(reason, name=_CON, id_number="001200000001", gender="Nam"),
        "me": _declared(reason, name=_ME, gender="Nữ"),
    }

    result = reason._validate_family_sections(sections)

    assert reason._is_unknown(result["cha"])


@REASON_MODULES
def test_khong_phai_to_khai_va_khong_co_gi_phan_biet_thi_van_xoa_vai_cha(reason):
    sections = {
        "con": _section(name=_CON),
        "cha": _section(name=_CON),
        "me": _section(name=_ME),
    }

    result = reason._validate_family_sections(sections)

    assert reason._is_unknown(result["cha"])


@REASON_MODULES
def test_khac_gioi_tinh_thi_giu_vai_cha_du_trung_ten(reason):
    sections = {
        "con": _section(name=_CON, gender="Nữ"),
        "cha": _section(name=_CON, gender="Nam"),
        "me": _section(name=_ME, gender="Nữ"),
    }

    result = reason._validate_family_sections(sections)

    assert reason._role_name(result["cha"]) == _CON


@REASON_MODULES
def test_khoang_cach_the_he_duoi_15_nam_van_xoa_vai_cha(reason):
    """Tờ khai ghi rõ nhãn quan hệ cũng không cứu được vai cha sinh sau con 5 năm."""
    sections = {
        "con": _declared(reason, name=_CON, birth="10/05/2000", gender="Nam"),
        "cha": _declared(reason, name="Nguyễn Văn Bốn", birth="1995", gender="Nam"),
        "me": _declared(reason, name=_ME, gender="Nữ"),
    }

    result = reason._validate_family_sections(sections)

    assert reason._is_unknown(result["cha"])


@REASON_MODULES
def test_cha_gioi_tinh_nu_van_bi_xoa(reason):
    sections = {
        "con": _declared(reason, name=_CON, gender="Nam"),
        "cha": _declared(reason, name="Nguyễn Thị Hoa", gender="Nữ"),
        "me": _declared(reason, name=_ME, gender="Nữ"),
    }

    result = reason._validate_family_sections(sections)

    assert reason._is_unknown(result["cha"])


def test_hai_pipeline_dung_chung_cum_can_cu_to_khai():
    """Đổi câu căn cứ ở một pipeline mà quên pipeline kia là vai cha/mẹ lại rụng."""
    assert dang_ky_lai._DECLARATION_BASIS_PREFIX == co_ho_so._DECLARATION_BASIS_PREFIX
    assert dang_ky_lai._from_declaration_label(
        f"Căn cứ phân vai: {dang_ky_lai._DECLARATION_ROLE_BASIS}"
    )
