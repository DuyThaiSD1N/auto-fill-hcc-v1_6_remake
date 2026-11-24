"""Trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng hằng tháng (1.116909): bên được ủy quyền, khớp gần tài khoản, lớp soát thứ
hai (thanh tra định danh + địa chỉ) và điền đợt 2 Form.io. Dữ liệu giả."""

import asyncio

from app.pipelines._shared.thanh_tra.ho_so import Case
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.process import mapper, runner
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.thanh_tra import dia_chi, dinh_danh
from app.procedures.registry import PROCEDURES
from app.second_pass.service import capability

_SUBJECT = {
    "DoiTuong_HoTen": "Hoàng Văn An", "DoiTuong_SoDinhDanh": "012050000111", "DoiTuong_NgaySinh": "01/02/1950",
    "DoiTuong_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Phường Hiệp Hòa", "diaChi": "Thôn Một"},
}
_GUARDIAN = {"NguoiNop_HoTen": "Hoàng Văn Bình", "NguoiNop_SoDinhDanh": "012080000222", "NguoiNop_QuanHe": "Con"}
_PROXY = {"UyQuyen_HoTen": "Lò Thị Cúc", "UyQuyen_SoDinhDanh": "012185000333", "UyQuyen_NgaySinh": "05/06/1985",
          "UyQuyen_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Phường Hiệp Hòa", "diaChi": "Thôn Hai"}}


def _ui(values, options=None):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    return {f["name"]: f["value"] for f in fields}, warnings


def test_dang_ky_dot_hai_form_formio():
    entry = next(p for p in PROCEDURES if p["key"] == "thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang")
    assert capability(entry) == "secondPassFormio"


def test_registry_bat_moc_tai_khoan_cho_auto_fill():
    from app.procedures.registry import public_list
    entry = next(p for p in public_list() if p["key"] == "thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang")
    assert entry["collectFormContext"] is True


def test_theo_to_khai_co_giay_uy_quyen_nguoi_nop_la_ben_duoc_uy_quyen():
    ui, _ = _ui({**_SUBJECT, **_GUARDIAN, **_PROXY}, {"submitterMode": "owner_as_submitter"})
    assert ui["data[fullname]"] == "LÒ THỊ CÚC" and ui["data[birthday]"] == "05/06/1985"
    assert ui["data[address]"] == "Thôn Hai"
    assert ui["data[ownerFullname]"] == "HOÀNG VĂN AN" and ui["data[isOwnerDossierCheck]"] is False
    # Không có giấy ủy quyền → người giám hộ như cũ.
    ui, _ = _ui({**_SUBJECT, **_GUARDIAN}, {"submitterMode": "owner_as_submitter"})
    assert ui["data[fullname]"] == "HOÀNG VĂN BÌNH"


def test_theo_tai_khoan_khop_ben_duoc_uy_quyen_dien_du_nhan_than():
    account = {"formContext": {"applicantFullname": "Lò Thị Cúc", "applicantIdentityNumber": "012185000333"}}
    ui, warnings = _ui({**_SUBJECT, **_GUARDIAN, **_PROXY}, account)
    assert not warnings
    assert ui["data[fullname]"] == "Lò Thị Cúc" and ui["data[birthday]"] == "05/06/1985"


def test_theo_tai_khoan_khop_gan_khi_ocr_lech_ten_va_so():
    account = {"formContext": {"applicantFullname": "Hoàng Văn Bình", "applicantIdentityNumber": "012080000229"}}
    values = {**_SUBJECT, **_GUARDIAN, "NguoiNop_HoTen": "Hoàng Văn Bìh", "NguoiNop_NgaySinh": "11/09/1980"}
    ui, warnings = _ui(values, account)
    assert not warnings
    # Họ tên + số theo tài khoản, nhân thân còn lại của đúng người đó.
    assert ui["data[fullname]"] == "Hoàng Văn Bình" and ui["data[identityNumber]"] == "012080000229"
    assert ui["data[birthday]"] == "11/09/1980"


def test_sdt_phai_du_10_so_va_ten_xa_khong_tien_to():
    ui, _ = _ui({**_SUBJECT, "DoiTuong_DienThoai": "09860221736"}, {"submitterMode": "owner_as_submitter"})
    assert "data[ownerPhoneNumber]" not in ui
    assert ui["data[ownerDistrict]"] == "Hiệp Hòa" and ui["data[ownerProvince]"] == "Bắc Ninh"


def test_runner_luon_bo_khoa_hai_o_nguoi_nop(monkeypatch):
    async def fake_run(*args, **kwargs):
        return {"fields": [{"name": k, "value": v} for k, v in _SUBJECT.items()]}

    monkeypatch.setattr(runner.runner, "run", fake_run)
    res = asyncio.run(runner.run({}, {"formContext": {"applicantFullname": "Người Khác"}}))
    by = {f["name"]: f for f in res["fields"]}
    assert by["data[fullname]"].get("enableInput")
    assert by["data[identityNumber]"]["comp"] == "dom-expect" and by["data[identityNumber]"]["enableInput"]


_MAU_02 = (
    "Mẫu số 02\nTỜ KHAI NHẬN CHĂM SÓC, NUÔI DƯỠNG\nI. Thông tin chung người đại diện hộ gia đình\n1. Họ và tên: Hoàng Văn Bình\n"
    "2. Nơi cư trú: Thôn Ba, xã Hiệp Hòa\nII. Thông tin vợ hoặc chồng\n1. Họ và tên: Lò Thị Dung\n2. Nơi cư trú: Thôn Bốn\n"
)


def test_mau_02_muc_i_la_nguoi_nop_khong_phai_doi_tuong():
    lines = dia_chi.lines_of([{"text": _MAU_02}], {"NguoiNop_HoTen": "Hoàng Văn Bình"})
    assert lines["NguoiNop_NoiCuTru"][0].endswith("xã Hiệp Hòa") and "DoiTuong_NoiCuTru" not in lines


def test_dinh_danh_khong_doi_ten_chi_khac_dau():
    docs = [{"text": "GIẤY XÁC NHẬN KHUYẾT TẬT\nHọ và tên: HÀNG THỊ MÂY\nNơi cư trú: Bản A"}]
    values = {"DoiTuong_HoTen": "HẢNG THỊ MÂY"}
    assert not [f for f in dinh_danh.findings_from(Case(docs, "", values)) if f.unit.key.endswith("ho_ten")]


def test_dia_chi_chi_con_so_nha_la_chi_tiet_bi_cat():
    # Tên đường viết tay đứng sau số nhà bị lượt trích bỏ → thanh tra coi là cắt cụt.
    assert dia_chi._cut_detail("12/3", "12/3 Đường Mẫu", "Phường Mẫu Xã")
    # Phần bị bỏ chính là tên xã → không phải cắt cụt.
    assert not dia_chi._cut_detail("12/3", "12/3 Mẫu Xã", "Phường Mẫu Xã")
    # Chi tiết trọn tên, dòng còn chữ phía sau → giữ như cũ.
    assert not dia_chi._cut_detail("Tổ 4 Đường Mẫu", "Tổ 4 Đường Mẫu Cũ", "Phường Mẫu Xã")


_TO_KHAI_LECH_DAU = (
    "Mẫu số 01\nTỜ KHAI ĐỀ NGHỊ TRỢ CẤP XÃ HỘI\n───── Trang 2/3 ─────\n2.1. Họ và tên: Lê Thị Mẫu\n"
    "Số căn cước/Số định danh cá nhân: 012185000444\nNgày sinh: 05/06/1985 Giới tính: nữ\n───── Trang 3/3 ─────\n"
    "Họ và tên: Lê Thị Mầu\n- Số căn cước/Số định danh cá nhân: 01218500044\n- Ngày sinh: 05 / 06 / 1985\n"
    "Tên chủ tài khoản: Lê Thị Mầu\n"
)
_NGUOI_NOP_LECH_DAU = {"NguoiNop_HoTen": "LÊ THỊ MẪU", "NguoiNop_SoDinhDanh": "012185000444", "NguoiNop_NgaySinh": "05/06/1985"}


def test_dinh_danh_ten_lech_dau_giua_cac_muc_to_khai_lay_cach_viet_nhieu_dong_hon():
    found = [f for f in dinh_danh.findings_from(Case([{"text": _TO_KHAI_LECH_DAU}], "", _NGUOI_NOP_LECH_DAU))
             if f.unit.key == "nguoi_nop.ho_ten"]
    assert [f.values for f in found] == [{"NguoiNop_HoTen": "LÊ THỊ MẦU"}]


def test_dinh_danh_ten_lech_dau_co_giay_in_mang_ten_thi_giu():
    printed = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY XÁC NHẬN\nHọ và tên: Lê Thị Mầu\nNgày sinh: 05/06/1985"
    docs = [{"text": _TO_KHAI_LECH_DAU}, {"text": printed}]
    assert not [f for f in dinh_danh.findings_from(Case(docs, "", _NGUOI_NOP_LECH_DAU)) if f.unit.key.endswith("ho_ten")]
    # Cách viết của lượt trích không có trên giấy (đơn vị quen ghi không dấu) → không đổi.
    values = {**_NGUOI_NOP_LECH_DAU, "NguoiNop_HoTen": "LE THI MAU"}
    assert not [f for f in dinh_danh.findings_from(Case([{"text": _TO_KHAI_LECH_DAU}], "", values))
                if f.unit.key.endswith("ho_ten")]
