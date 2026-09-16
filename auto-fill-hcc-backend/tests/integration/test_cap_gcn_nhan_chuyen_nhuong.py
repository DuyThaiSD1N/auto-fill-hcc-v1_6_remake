"""Mapper tất định cho [Lào Cai] cấp GCN cho người nhận chuyển nhượng trong dự án BĐS (1.115667).

Dữ liệu lấy theo hồ sơ mẫu trong file mapping: người nộp Nhâm Đắc Đạt (VNeID), chủ hồ sơ là bên nhận
chuyển nhượng ông Ngô Trung Kiên (vợ Đỗ Thị The), bên chuyển nhượng Công ty TNHH xây dựng Thái Lào.
"""

from app.pipelines.cap_GCN_nhan_chuyen_nhuong.process import mapper
from app.pipelines.cap_GCN_nhan_chuyen_nhuong.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai"

_VNEID = {"formContext": {"applicantFullname": "NHÂM ĐẮC ĐẠT", "applicantIdentityNumber": "034203010212"}}

_HO_SO = {
    "ChuHoSo_LoaiDoiTuong": "Cá nhân",
    "ChuHoSo_HoTen": "Ngô Trung Kiên",
    "ChuHoSo_NgaySinh": "1957",
    "ChuHoSo_XungHo": "Ông",
    "ChuHoSo_SoDinhDanh": "0340.5701.7088",
    "ChuHoSo_NgayCap": "09/05/2021",
    "ChuHoSo_NoiCap": "Cục cảnh sát quản lý hành chính về trật tự xã hội",
    "ChuHoSo_DiaChiDon": {
        "quocGia": "Việt Nam", "tinh": "Lào Cai", "xa": "Lào Cai", "diaChi": "Tổ Dân phố 21 Kim Tân",
    },
    "ChuHoSo_DiaChiHopDong": {
        "quocGia": "Việt Nam", "tinh": "Lào Cai", "xa": "Lào Cai", "diaChi": "Tổ dân phố số 21 Kim Tân",
    },
    "Don_DienThoai": "0.35.935.1118",
}


def _run(values: dict, options: dict | None = _VNEID) -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by_name(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_registry_wires_process_and_attach_pipelines():
    proc = get_procedure(KEY)
    assert proc and proc["detect"]["urlScope"] == ["laocai.gov.vn"]
    assert proc["hasAttachmentStep"] is True
    assert get_pipeline(KEY) is not None
    assert get_attach_pipeline(KEY) is not None


def test_every_emitted_field_is_a_real_ui_control():
    out = _run({**_HO_SO, "DanhSachCccd": [{"SoDinhDanh": "034203010212", "NgayCap": "01/02/2022"}]})
    assert out and all(f["name"] in UI_COMP_BY_NAME for f in out)
    assert {f["name"] for f in FIELDS}.isdisjoint(UI_COMP_BY_NAME)


def test_sample_dossier_fills_owner_block_from_documents():
    out = _by_name(_run(_HO_SO))

    assert out["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert out["ChuHoSo_tenChuHoSo"] == "NGÔ TRUNG KIÊN"
    assert out["ChuHoSo_soCMNDChuHoSo"] == "034057017088"
    assert out["ChuHoSo_ngayCapCMNDCHS"] == "09/05/2021"
    assert out["ChuHoSo_noiCapCMNDCHS"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert out["ChuHoSo_gioiTinhChuHoSo"] == "Nam"  # suy từ xưng hô "Ông"
    assert out["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert out["ChuHoSo_maPhuongXaCHS"] == "Phường Lào Cai"
    assert out["ChuHoSo_diaChiChuHoSo"] == "Tổ Dân phố 21 Kim Tân"  # Đơn thắng HĐ
    assert out["ChuHoSo_diDongLienLacCHS"] == "0359351118"
    # SĐT trên Đơn là của chủ hồ sơ: không điền trùng sang khối người nộp.
    assert "CongDan_diDong" not in out
    assert "CongDan_fax" not in out


def test_birth_year_only_is_never_turned_into_a_date():
    out = _by_name(_run(_HO_SO))
    assert "ChuHoSo_ngaySinhChuHoSo" not in out
    assert "ChuHoSo_danTocChuHoSo" not in out  # giấy tờ đất đai không ghi dân tộc


def test_owner_card_beats_documents_for_identity():
    card = {
        "HoTen": "NGÔ TRUNG KIÊN", "SoDinhDanh": "034057017088", "NgaySinh": "12/3/1957",
        "GioiTinh": "Nam", "DanToc": "Kinh", "NgayCap": "10/10/2022", "NoiCap": "Bộ Công an",
    }
    out = _by_name(_run({**_HO_SO, "DanhSachCccd": [card]}))

    assert out["ChuHoSo_ngaySinhChuHoSo"] == "12/03/1957"
    assert out["ChuHoSo_danTocChuHoSo"] == "Kinh"
    # Ngày/nơi cấp: nguồn ưu tiên là HĐ chuyển nhượng, thẻ chỉ bù khi HĐ không ghi.
    assert out["ChuHoSo_ngayCapCMNDCHS"] == "09/05/2021"


def test_applicant_issue_fields_only_from_applicant_own_card():
    owner_card = {"HoTen": "NGÔ TRUNG KIÊN", "SoDinhDanh": "034057017088", "NgayCap": "09/05/2021",
                  "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"}
    out = _by_name(_run({**_HO_SO, "DanhSachCccd": [owner_card]}))
    assert "CongDan_ngayCapCmnd" not in out
    assert "CongDan_noiCapCmnd" not in out

    applicant_card = {"HoTen": "NHÂM ĐẮC ĐẠT", "SoDinhDanh": "034203010212", "NgayCap": "3/4/2022",
                      "NoiCap": "Bộ Công an"}
    out = _by_name(_run({**_HO_SO, "DanhSachCccd": [owner_card, applicant_card]}))
    assert out["CongDan_ngayCapCmnd"] == "03/04/2022"
    assert out["CongDan_noiCapCmnd"] == "Bộ Công an"


def test_prefilled_applicant_identity_is_never_overwritten():
    applicant_card = {"HoTen": "NHÂM ĐẮC ĐẠT", "SoDinhDanh": "034203010212", "NgaySinh": "03/12/2003"}
    out = _by_name(_run({**_HO_SO, "DanhSachCccd": [applicant_card]}))
    for name in ("CongDan_tenCongDan", "CongDan_soCmnd", "CongDan_maTinhThanh", "CongDan_diaChi"):
        assert name not in out


def test_applicant_own_card_fills_applicant_block():
    owner_card = {"HoTen": "NGÔ TRUNG KIÊN", "SoDinhDanh": "034057017088", "GioiTinh": "Nam", "DanToc": "Tày"}
    applicant_card = {
        "HoTen": "NGUYỄN DUY THÁI", "SoDinhDanh": "001204018566", "NgaySinh": "11/8/2004", "GioiTinh": "Nam",
        "DanToc": "Kinh", "NgayCap": "20/05/2022", "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    }
    ctx = {"formContext": {"applicantFullname": "NGUYỄN DUY THÁI", "applicantIdentityNumber": "001204018566"}}
    out = _by_name(_run({**_HO_SO, "DanhSachCccd": [owner_card, applicant_card]}, ctx))

    assert out["CongDan_ngaySinhCongDan"] == "11/08/2004"
    assert out["CongDan_gioiTinhCongDan"] == "Nam"  # cổng mặc định Nữ → phải sửa theo thẻ
    assert out["CongDan_danTocCongDan"] == "Kinh"
    assert out["CongDan_ngayCapCmnd"] == "20/05/2022"
    assert out["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert out["ChuHoSo_danTocChuHoSo"] == "Tày"  # thẻ người nộp không lẫn sang chủ hồ sơ


def test_applicant_card_matched_by_account_name_when_number_missing():
    applicant_card = {"HoTen": "Nguyễn Duy Thái", "SoDinhDanh": "001204018566", "DanToc": "Kinh"}
    ctx = {"formContext": {"applicantFullname": "NGUYỄN DUY THÁI", "applicantIdentityNumber": ""}}
    out = _by_name(_run({**_HO_SO, "DanhSachCccd": [applicant_card]}, ctx))
    assert out["CongDan_danTocCongDan"] == "Kinh"

    out = _by_name(_run({**_HO_SO, "DanhSachCccd": [applicant_card]}, {}))
    assert "CongDan_danTocCongDan" not in out  # không biết tài khoản là ai → không đoán


def test_driver_select_is_emitted_before_owner_fields():
    names = [f["name"] for f in _run(_HO_SO)]
    driver = names.index("ChuHoSo_maDoiTuongNopHS")
    assert all(driver < names.index(n) for n in names if n.startswith("ChuHoSo_") and n != names[driver])
    assert names.index("ChuHoSo_maTinhThanhCHS") < names.index("ChuHoSo_maPhuongXaCHS")


def test_organization_recipient_uses_its_own_name_and_tax_code():
    out = _by_name(_run({
        "ChuHoSo_LoaiDoiTuong": "Tổ chức",
        "ChuHoSo_TenToChuc": "Công ty cổ phần An Phát",
        "ChuHoSo_MaSoThue": "5300123456",
        "ChuHoSo_DiaChiHopDong": {"tinh": "Lào Cai", "xa": "Lào Cai", "diaChi": "Số 5 Hoàng Liên"},
    }))
    assert out["ChuHoSo_maDoiTuongNopHS"] == "DN"
    assert out["ChuHoSo_tenCoQuanToChucCHS"] == "CÔNG TY CỔ PHẦN AN PHÁT"
    assert out["ChuHoSo_maSoThueChuHoSo"] == "5300123456"
    assert "ChuHoSo_tenChuHoSo" not in out


def test_missing_identity_number_does_not_pick_owner_branch():
    values = dict(_HO_SO)
    values.pop("ChuHoSo_SoDinhDanh")
    out = _by_name(_run(values))
    assert "ChuHoSo_maDoiTuongNopHS" not in out
    assert "ChuHoSo_tenChuHoSo" not in out
