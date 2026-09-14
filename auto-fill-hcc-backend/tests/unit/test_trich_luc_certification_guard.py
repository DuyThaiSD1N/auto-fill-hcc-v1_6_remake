"""Cấp bản sao trích lục: số chứng thực của giấy ủy quyền không được vào ô thông tin đăng ký hộ tịch."""

from app.pipelines.trich_luc.process import mapper
from app.pipelines.trich_luc.process.prompt import EXTRA_RULES
from app.pipelines.trich_luc.process.runner import _compact_field_fallback

_UY_QUYEN_OCR = (
    "GIẤY ỦY QUYỀN\n"
    "Hôm nay, ngày 14 tháng 9 năm 2026, tại UBND xã Hiệp Hòa, tỉnh Bắc Ninh.\n"
    "Ông Nguyễn Văn Tú, Sinh ngày: 06/10/1997\nCCCD số: 0240 9700 2839\n"
    "Chứng thực\n"
    "Số chứng thực: 8160 quyển số 03/2026. TP – SCT CK-ĐC.\n"
    "CĂN CƯỚC CÔNG DÂN\nSố / No.: 024097002839\nHọ và tên / Full name: NGUYỄN VĂN TÚ\n"
)


def test_drops_certification_number_used_as_registration():
    raw = {
        "ChuThe_HoTen": "NGUYỄN VĂN TÚ",
        "ChuThe_SoDinhDanh": "024097002839",
        "ToKhai_LoaiSuKien": "birth",
        "ToKhai_TenGiayTo": "Giấy khai sinh",
        "HoTich_CoQuanDangKy": "UBND xã Hiệp Hòa",
        "HoTich_So": "8160",
        "HoTich_QuyenSo": "03/2026",
        "HoTich_NgayDangKy": "14/09/2026",
    }
    out = _compact_field_fallback(raw, [{"text": _UY_QUYEN_OCR}])

    for name in ("HoTich_CoQuanDangKy", "HoTich_So", "HoTich_QuyenSo", "HoTich_NgayDangKy"):
        assert name not in out
    assert out["ChuThe_SoDinhDanh"] == "024097002839"

    ui = {f["name"] for f in mapper.enrich([{"name": k, "value": v} for k, v in out.items()])}
    assert not ui & {"HoSo_CoQuanDangKy", "HoSo_So", "HoSo_QuyenSo", "HoSo_NgayCapSo"}


def test_keeps_real_registration_number_list_shape():
    ocr = (
        "TRÍCH LỤC KHAI SINH\nSố: 245/2015\nQuyển số: 01\n"
        "Chứng thực bản sao đúng với bản chính. Số chứng thực: 99 quyển số 02 SCT/BS\n"
    )
    raw = [
        {"name": "HoTich_So", "value": "245/2015"},
        {"name": "HoTich_QuyenSo", "value": "01"},
        {"name": "HoTich_NgayDangKy", "value": "11/09/2015"},
    ]
    out = _compact_field_fallback(raw, [{"text": ocr}])
    assert [f["name"] for f in out] == ["HoTich_So", "HoTich_QuyenSo", "HoTich_NgayDangKy"]


def test_power_of_attorney_card_goes_to_subject_and_relation_is_not_self():
    """req_54573521416d: người yêu cầu (bên được ủy quyền) ở TkNyc_*, CCCD bên ủy quyền nằm nhầm Nyc_*."""
    values = {
        "Nyc_HoTen": "NGUYỄN VĂN TÚ", "Nyc_SoDinhDanh": "024097002839", "Nyc_NgaySinh": "06/10/1997",
        "Nyc_GioiTinh": "Nam", "Nyc_NgayCap": "13/06/2023",
        "Nyc_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "Nyc_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Bắc Giang", "xa": "Phúc Thắng", "diaChi": "Danh Thắng"},
        "TkNyc_HoTen": "Nguyễn Đăng Ninh", "TkNyc_SoGiayToTuyThan": "024059007762",
        "TkNyc_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Hiệp Hòa", "diaChi": "Thôn Thống Nhất"},
        "ToKhai_LoaiSuKien": "birth", "ToKhai_TenGiayTo": "Giấy khai sinh",
        "CopyRequest_QuanHe": "Bản thân",
    }
    options = {"formContext": {"applicantFullname": "NGUYỄN DUY THÁI", "applicantIdentityNumber": "001204018566"}}
    out = {f["name"]: f for f in mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)}

    assert out["NYC_QuanHe"]["value"] == "Khác" and out["NYC_QuanHe"].get("default")
    assert out["HoVaTenC"]["value"] == "NGUYỄN ĐĂNG NINH"
    assert out["SoDinhDanhC"]["value"] == "024059007762"
    assert out["NDK_HoVaTen"]["value"] == "NGUYỄN VĂN TÚ"
    assert out["NDK_SoDinhDanh"]["value"] == "024097002839"
    assert out["NDK_NgaySinh"]["value"] == "06/10/1997"
    area = out["NDK_NoiCuTru_TrongNuoc"]["value"]
    assert area["tinh"] == "Bắc Ninh" and area["xa"] == "Xã Hiệp Hòa" and area["diaChi"] == "Phúc Thắng"


_FULL_UY_QUYEN_OCR = """CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập – Tự do – Hạnh phúc

GIẤY ỦY QUYỀN

Hôm nay, ngày 14 tháng 9 năm 2026, tại UBND xã Hiệp Hòa, tỉnh Bắc Ninh.
Chúng tôi gồm:
I.BÊN ỦY QUYỀN
Ông Nguyễn Văn Tú, Sinh ngày: 06/10/1997
CCCD số: 0240 9700 2839
Địa chỉ thường trú: Thôn Thống Nhất, xã Hiệp Hòa, tỉnh Bắc Ninh.
II.BÊN ĐƯỢC ỦY QUYỀN:
Ông Nguyễn Đăng Ninh, Sinh ngày: 19/01/1959
CCCD số: 0240 5900 7762
Địa chỉ thường trú: Thôn Thống Nhất, xã Hiệp Hòa, tỉnh Bắc Ninh.
III.NỘI DUNG ỦY QUYỀN:
Bên ủy quyền, ủy quyền cho bên nhận ủy quyền thực hiện các nội dung sau:
Làm thủ tục xin cấp Bản sao trích lục hộ tịch, nhận kết quả giấy khai sinh Bản sao.
N. CAM KẾT:
BÊN ỦY QUYỀN
(Ký ghi rõ họ tên)
Nguyễn văn Tú
BÊN NHẬN ỦY QUYỀN
(Ký ghi rõ họ tên)
Nguyễn Đăng Ninh
Số chứng thực: 8160 quyển số 03/2026. TP – SCT CK-ĐC.
CĂN CƯỚC CÔNG DÂN
Số / No.: 024097002839
Họ và tên / Full name: NGUYỄN VĂN TÚ
Nơi thường trú / Place of residence: Phúc Thắng
Danh Thắng, Hiệp Hòa, Bắc Giang
"""

_TU_CARD = {
    "Nyc_HoTen": "NGUYỄN VĂN TÚ", "Nyc_SoDinhDanh": "024097002839", "Nyc_NgaySinh": "06/10/1997",
    "Nyc_GioiTinh": "Nam", "Nyc_NgayCap": "13/06/2023",
    "Nyc_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "Nyc_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Bắc Giang", "xa": "Phúc Thắng", "diaChi": "Danh Thắng"},
}
_REQUEST = {"ToKhai_LoaiSuKien": "birth", "ToKhai_TenGiayTo": "Giấy khai sinh", "CopyRequest_Quantity": 1}


def _run_power_of_attorney(llm_fields: dict) -> dict:
    fixed = _compact_field_fallback(llm_fields, [{"text": _FULL_UY_QUYEN_OCR}])
    options = {"formContext": {"applicantFullname": "NGUYỄN DUY THÁI", "applicantIdentityNumber": "001204018566"}}
    return {f["name"]: f for f in mapper.enrich([{"name": k, "value": v} for k, v in fixed.items()], options)}


def _assert_power_of_attorney_roles(out: dict) -> None:
    assert out["HoVaTenC"]["value"] == "NGUYỄN ĐĂNG NINH"
    assert out["SoDinhDanhC"]["value"] == "024059007762"
    assert out["NYC_NoiCuTru_TrongNuoc"]["value"]["diaChi"] == "Thôn Thống Nhất"
    assert "NgayCapDDC" not in out   # ngày cấp của thẻ bên ủy quyền không được dán sang người yêu cầu
    assert out["NYC_QuanHe"]["value"] == "Khác"
    assert out["NDK_HoVaTen"]["value"] == "NGUYỄN VĂN TÚ"
    assert out["NDK_SoDinhDanh"]["value"] == "024097002839"
    assert out["NDK_NgayCap"]["value"] == "13/06/2023"


def test_power_of_attorney_llm_picked_agent_as_requester():
    """req_e19f2b91a6b5: agent đọc đúng bên được ủy quyền vào TkNyc_*."""
    _assert_power_of_attorney_roles(_run_power_of_attorney({
        **_TU_CARD, **_REQUEST,
        "TkNyc_HoTen": "Nguyễn Đăng Ninh", "TkNyc_SoGiayToTuyThan": "024059007762",
    }))


def test_power_of_attorney_llm_picked_principal_as_requester():
    """req_6428cb1e9dfd: agent gán nhầm BÊN ỦY QUYỀN vào TkNyc_* → trước đây mục II trống."""
    _assert_power_of_attorney_roles(_run_power_of_attorney({
        **_TU_CARD, **_REQUEST,
        "TkNyc_HoTen": "Nguyễn Văn Tú", "TkNyc_LoaiGiayToTuyThan": "CCCD",
        "TkNyc_SoGiayToTuyThan": "024097002839", "TkNyc_NgayCapGiayToTuyThan": "13/06/2023",
        "TkNyc_NoiCapGiayToTuyThan": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "CopyRequest_QuanHe": "Bản thân",
    }))


def test_no_power_of_attorney_leaves_fields_untouched():
    raw = {**_TU_CARD, "TkNyc_HoTen": "Nguyễn Văn Tú"}
    assert _compact_field_fallback(raw, [{"text": "CĂN CƯỚC CÔNG DÂN\nSố: 024097002839\nNGUYỄN VĂN TÚ"}]) == raw


def test_prompt_explains_power_of_attorney_roles():
    assert "<giay_uy_quyen_rules>" in EXTRA_RULES
    assert "Số chứng thực" in EXTRA_RULES
