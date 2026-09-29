"""Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại (Bộ Công Thương, 2.001474)."""

from pathlib import Path

from app.pipelines.thong_bao_sua_doi_ctkm.attach import planner
from app.pipelines.thong_bao_sua_doi_ctkm.process import mapper
from app.pipelines.thong_bao_sua_doi_ctkm.process.prompt import EXTRA_RULES
from app.pipelines.thong_bao_sua_doi_ctkm.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "thong-bao-sua-doi-bo-sung-noi-dung-chuong-trinh-khuyen-mai"
_ACCOUNT = {"formContext": {"applicantFullname": "Nguyễn Văn A", "applicantIdentityNumber": "001099000001"}}


def _trader():
    return {
        "ThuongNhan_Ten": "Công ty TNHH Thương Mại ABC",
        "ThuongNhan_MaSoThue": "0100000001",
        "ThuongNhan_DiaChi": {
            "tinh": "Thành phố Hà Nội", "xa": "Phường Hoàn Kiếm", "diaChi": "Số 1 phố Mẫu",
            "fullText": "Số 1 phố Mẫu, phường Hoàn Kiếm, Thành phố Hà Nội",
        },
        "ThuongNhan_DienThoai": "0240000001",
        "ThuongNhan_Fax": "0240000002",
        "ThuongNhan_NguoiLienHe": "Trần Thị B",
        "ThuongNhan_DienThoaiLienHe": "0900000001",
        "ThongBao_So": "01-2026-KM",
        "ThongBao_NgayLap": "08/09/2026",
        "ThongBao_KinhGui": "Sở Công Thương tỉnh Quảng Trị",
        "ThongBaoGoc_So": "05-2026-KM",
        "ThongBaoGoc_Ngay": "11/05/2026",
        "CTKM_Ten": "Mua 1 tặng 1",
        "CTKM_NgayBatDauSuaDoi": "14/09/2026",
        "CTKM_LyDoDieuChinh": "Điều chỉnh giao diện trò chơi",
        "CTKM_CamKet": "Cam kết thứ nhất\nCam kết thứ hai",
    }


def _cccd():
    return {
        "NguoiNop_HoTen": "NGUYỄN VĂN A",
        "NguoiNop_SoDinhDanh": "001099000001",
        "NguoiNop_NgaySinh": "01/02/1990",
        "NguoiNop_NgayCap": "03/04/2022",
        "NguoiNop_NoiCuTru": {"tinh": "Tỉnh Quảng Trị", "xa": "Phường Đông Hà", "diaChi": "Khu phố 1"},
    }


def _run(values, options=None):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    by_key = {(f["name"], f.get("occurrence")): f for f in fields}
    return by_key, warnings


def test_registry_detect_theo_ma_ten_va_host():
    proc = get_procedure(KEY)
    assert proc["detect"]["urlScope"] == ["dichvucong-tthc.moit.gov.vn"]
    assert proc["detect"]["textIncludes"] == ["2.001474", "Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại"]
    assert proc["hasAttachmentStep"] is True
    assert get_pipeline(KEY) is not None and get_attach_pipeline(KEY) is not None


def test_key_trung_giua_tai_khoan_va_to_khai_gan_occurrence():
    fields, _ = _run({**_trader(), **_cccd()}, _ACCOUNT)
    assert fields[("data[fullname]", 0)]["value"] == "NGUYỄN VĂN A"
    assert fields[("data[fullname]", 1)]["value"] == "Công ty TNHH Thương Mại ABC"
    assert fields[("data[province]", 0)]["value"] == "Quảng Trị"
    assert fields[("data[province]", 1)]["value"] == "Hà Nội"
    assert fields[("data[address]", 0)]["value"] == "Khu phố 1"
    assert fields[("data[address]", 1)]["value"] == "Số 1 phố Mẫu"
    assert fields[("data[phoneNumber]", 1)]["value"] == "0240000001"
    assert ("data[phoneNumber]", 0) not in fields, "CCCD không in SĐT — không mượn SĐT doanh nghiệp"
    assert fields[("data[village]", None)]["value"] == "Hoàn Kiếm"


def test_chu_ho_so_la_thuong_nhan_va_hai_van_ban_khong_doi_cheo():
    fields, _ = _run(_trader())
    assert fields[("data[isOwnerDossier]", None)]["value"] is False
    assert fields[("data[ownerFullname]", None)]["value"] == "Công ty TNHH Thương Mại ABC"
    assert fields[("data[ownertaxCode]", None)]["value"] == "0100000001"
    assert fields[("data[ownerAddress]", None)]["value"].startswith("Số 1 phố Mẫu")
    assert fields[("data[registerNumber]", None)]["value"] == "01-2026-KM"
    assert fields[("data[ngayNopDon]", None)]["value"] == "08/09/2026"
    assert fields[("data[registerNumberSubmitted]", None)]["value"] == "05-2026-KM"
    assert fields[("data[submissionDate]", None)]["value"] == "11/05/2026"
    assert fields[("data[contactPerson]", None)]["value"] == "Trần Thị B"
    assert fields[("data[phone]", None)]["value"] == "0900000001"
    assert fields[("data[CamKetKhac]", None)]["value"] == "Cam kết thứ nhất\nCam kết thứ hai"
    assert fields[("data[noidungyeucaugiaiquyet]", None)]["value"].endswith('"Mua 1 tặng 1"')


def test_khoi_tai_khoan_chi_dien_khi_cccd_khop_tai_khoan():
    other = {"formContext": {"applicantFullname": "Lê Văn C", "applicantIdentityNumber": "001099000009"}}
    for options, reason in ((other, "không khớp"), (None, "Chưa đọc được tài khoản")):
        fields, warnings = _run({**_trader(), **_cccd()}, options)
        assert ("data[fullname]", 0) not in fields
        assert ("data[identityNumber]", None) not in fields
        assert any(reason in w for w in warnings)
        assert fields[("data[fullname]", 1)]["value"] == "Công ty TNHH Thương Mại ABC"


def test_khop_tai_khoan_theo_ho_ten_bo_dau_khi_thieu_so():
    by_name = {"formContext": {"applicantFullname": "Nguyen Van A"}}
    fields, _ = _run({**_trader(), **_cccd()}, by_name)
    assert fields[("data[identityNumber]", None)]["value"] == "001099000001"


def test_so_bi_che_thieu_chu_so_khong_dien_va_bao_canh_bao():
    values = {**_trader(), "ThuongNhan_DienThoai": "0283", "ThuongNhan_MaSoThue": "030"}
    fields, warnings = _run(values)
    assert ("data[ownertaxCode]", None) not in fields
    assert ("data[ownerPhoneNumber]", None) not in fields
    assert ("data[phoneNumber]", 1) not in fields
    assert any("Mã số thuế" in w for w in warnings)
    assert any("Điện thoại thương nhân" in w for w in warnings)


def test_tinh_nop_don_chi_khi_kinh_gui_neu_dung_mot_tinh():
    fields, _ = _run(_trader())
    assert fields[("data[tinhThanhPhoNopDon]", None)]["value"] == "Quảng Trị"

    toan_quoc = {**_trader(), "ThongBao_KinhGui": "Sở Công Thương các Tỉnh/Thành phố trên toàn quốc"}
    fields, warnings = _run(toan_quoc)
    assert ("data[tinhThanhPhoNopDon]", None) not in fields
    assert any("Tỉnh / Thành Phố nộp đơn" in w for w in warnings)


def test_moi_field_mapper_phat_deu_co_trong_ui_va_prompt_chi_dung_field_hop_le():
    fields, _ = _run({**_trader(), **_cccd()}, _ACCOUNT)
    assert all(name in UI_COMP_BY_NAME for name, _ in fields)
    for name in ("ThongBaoGoc_So", "CTKM_NgayBatDauSuaDoi", "ThuongNhan_DienThoaiLienHe"):
        assert name in ALLOWED and name in EXTRA_RULES


def test_dinh_kem_moi_tep_ke_ca_cccd_vao_dong_thong_bao_giu_ten_goc():
    files = [{"name": "Thong bao sua doi.pdf"}, {"name": "cccd mat truoc.jpg"}, {"name": "cccd mat sau.jpg"}]
    items = planner.build_plan_items(files)
    assert [item["fileIndex"] for item in items] == [0, 1, 2]
    assert all(item["target"] == "attp-row" and item["loaiBan"] == "Bản chính" for item in items)
    assert all(item["componentName"] == "Thông báo sửa đổi, bổ sung nội dung chương trình" for item in items)
    assert [item["documentName"] for item in items] == [f["name"] for f in files]


def test_popup_gui_form_context_cho_thu_tuc_nay():
    popup = Path(__file__).resolve().parents[3] / "auto-fill-hcc-extension" / "popup.js"
    if not popup.exists():
        return
    assert f'cfg.key === "{KEY}"' in popup.read_text(encoding="utf-8")
