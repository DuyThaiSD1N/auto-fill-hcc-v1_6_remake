"""Tests cho thủ tục "Đăng ký hành nghề" (mã 1.012275 — Sở Y tế).

Chủ hồ sơ (Phần II) là CƠ SỞ khám bệnh, chữa bệnh: tên + địa chỉ lấy từ Danh sách đăng ký hành nghề, nhân
thân lấy từ CCCD người đại diện. Phần I (tài khoản VNeID) không được chạm tới.
"""

from app.pipelines.dang_ky_hanh_nghe import process as agent
from app.pipelines.dang_ky_hanh_nghe.attach import plan as attach_plan
from app.pipelines.dang_ky_hanh_nghe.attach.planner import build_plan_items
from app.pipelines.dang_ky_hanh_nghe.process import mapper
from app.pipelines.dang_ky_hanh_nghe.process.schema import FIELDS
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "dang-ky-hanh-nghe"


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _values(mapped: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in mapped}


def _ho_so() -> list[dict]:
    return [
        _field("CoSo_Ten", "Trạm Y tế xã Mường Than"),
        _field("CoSo_DiaChi", {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Xã Mường Than", "diaChi": "Bản Nà Ban"}),
        _field("CoSo_NguoiChiuTrachNhiem", "Nhâm Đắc Đạt"),
        _field("NguoiDaiDien_HoTen", "NHÂM ĐẮC ĐẠT"),
        _field("NguoiDaiDien_NgaySinh", "3/12/2003"),
        _field("NguoiDaiDien_GioiTinh", "Nam"),
        _field("NguoiDaiDien_SoDinhDanh", "0342 0301 0212"),
        _field("NguoiDaiDien_NgayCapCCCD", "01/07/2021"),
        _field("NguoiDaiDien_NoiCapCCCD", "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"),
    ]


def test_dang_ky_hanh_nghe_registered_and_link_nop_tai_so():
    proc = get_procedure(KEY)
    assert proc and proc["mode"] == "agent" and proc["hasAttachmentStep"] is True
    assert get_pipeline(KEY) is agent.run
    assert get_attach_pipeline(KEY) is attach_plan

    link = next(item for item in KE_KHAI_LINKS if item.get("key") == KEY)
    assert link["code"] == "1.012275"
    assert link["selectSo"] is True


def test_dang_ky_hanh_nghe_schema_khong_co_field_nguoi_hanh_nghe_ca_nhan():
    names = {f["name"] for f in FIELDS}
    assert {"CoSo_Ten", "CoSo_DiaChi", "NguoiDaiDien_SoDinhDanh"} <= names


def test_dang_ky_hanh_nghe_dien_co_so_vao_chu_ho_so_khong_dung_phan_i():
    out, warnings = mapper.enrich(_ho_so(), {})
    d = _values(out)

    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[ownerFullname]"] == "Trạm Y tế xã Mường Than"
    assert d["data[ownerBirthday]"] == "03/12/2003"
    assert d["data[ownerGender]"] == "Nam"
    assert d["data[ownerIdentityNumber]"] == "034203010212"
    assert d["data[ownerIdentityDate]"] == "01/07/2021"
    assert d["data[ownerIdIssuePlace]"]
    assert d["data[ownerProvince]"] == "Tỉnh Lai Châu"
    assert d["data[ownerDistrict]"]
    assert d["data[ownerNation]"] == "Việt Nam"
    # Phần I là tài khoản VNeID — không phát ô nào.
    assert not any(
        name in d
        for name in ("data[chonDoiTuong]", "data[fullname]", "data[identityNumber]", "data[birthday]", "data[phoneNumber]")
    )
    # SĐT không có trong giấy tờ → không bịa, chỉ nhắc nhập tay.
    assert "data[ownerPhoneNumber]" not in d
    assert any("điện thoại" in w for w in warnings)


def test_dang_ky_hanh_nghe_thieu_cccd_va_nhieu_co_so_thi_canh_bao():
    fields = [
        _field("CoSo_Ten", "Trạm Y tế xã Mường Than"),
        _field("CoSo_CacCoSoKhac", "Trung tâm Y tế Nậm Nhùn; Trạm Y tế xã Mường Mô"),
    ]
    out, warnings = mapper.enrich(fields, {})
    d = _values(out)

    assert d["data[ownerFullname]"] == "Trạm Y tế xã Mường Than"
    assert "data[ownerIdentityNumber]" not in d
    assert any("CCCD của người đại diện" in w for w in warnings)
    assert any("Trung tâm Y tế Nậm Nhùn" in w for w in warnings)


def test_dang_ky_hanh_nghe_file_that_tram_y_te_muong_than():
    """Mẫu 01 thật của Trạm Y tế xã Mường Than: địa chỉ chỉ tới cấp xã, người ký là Giám đốc trạm, không CCCD."""
    fields = [
        _field("CoSo_Ten", "Trạm Y tế xã Mường Than"),
        _field("CoSo_DiaChi", {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Xã Mường Than", "diaChi": ""}),
        _field("CoSo_NguoiChiuTrachNhiem", "Lò Văn Sơn"),
    ]
    out, warnings = mapper.enrich(fields, {})
    d = _values(out)

    assert d["data[ownerFullname]"] == "Trạm Y tế xã Mường Than"
    assert d["data[ownerProvince]"] == "Tỉnh Lai Châu"
    assert d["data[ownerDistrict]"] == "Xã Mường Than"
    # Ô địa chỉ chi tiết bắt buộc → không để trống, nhưng nhắc bổ sung.
    assert d["data[ownerAddress]"] == "Xã Mường Than"
    assert any("Địa chỉ chi tiết" in w for w in warnings)
    assert any("CCCD của người đại diện" in w for w in warnings)


def test_dang_ky_hanh_nghe_khong_dung_cccd_nguoi_nop_cho_chu_ho_so_req_bb6d9a7bfd29():
    """Danh sách do Lò Văn Sơn ký + CCCD của người nộp Nguyễn Duy Thái: LLM vẫn đổ CCCD người nộp vào
    NguoiDaiDien_* → mapper phải bỏ, không để ngày sinh/số CCCD người khác lên Phần II."""
    fields = [
        _field("CoSo_Ten", "Trạm Y tế xã Mường Than"),
        _field("CoSo_DiaChi", {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Mường Than", "diaChi": "", "huyen": ""}),
        _field("CoSo_NguoiChiuTrachNhiem", "Lò Văn Sơn"),
        _field("NguoiDaiDien_HoTen", "NGUYỄN DUY THÁI"),
        _field("NguoiDaiDien_NgaySinh", "11/08/2004"),
        _field("NguoiDaiDien_GioiTinh", "Nam"),
        _field("NguoiDaiDien_SoDinhDanh", "001204018566"),
    ]
    out, warnings = mapper.enrich(fields, {"formContext": {"applicantFullname": "NGUYỄN DUY THÁI"}})
    d = _values(out)

    assert d["data[ownerFullname]"] == "Trạm Y tế xã Mường Than"
    for name in ("data[ownerBirthday]", "data[ownerGender]", "data[ownerIdentityNumber]",
                 "data[ownerIdentityDate]", "data[ownerIdIssuePlace]"):
        assert name not in d, name
    assert any("NGUYỄN DUY THÁI" in w and "Lò Văn Sơn" in w for w in warnings)


def test_dang_ky_hanh_nghe_cccd_dung_nguoi_chiu_trach_nhiem_thi_van_dien():
    fields = [
        _field("CoSo_Ten", "Trạm Y tế xã Mường Than"),
        _field("CoSo_NguoiChiuTrachNhiem", "Lò Văn Sơn"),
        _field("NguoiDaiDien_HoTen", "LÒ VĂN SƠN"),
        _field("NguoiDaiDien_NgaySinh", "02/03/1980"),
        _field("NguoiDaiDien_SoDinhDanh", "012080000123"),
    ]
    out, _ = mapper.enrich(fields, {"formContext": {"applicantFullname": "NGUYỄN DUY THÁI"}})
    d = _values(out)

    assert d["data[ownerIdentityNumber]"] == "012080000123"
    assert d["data[ownerBirthday]"] == "02/03/1980"


DS_TEXT = (
    "Mẫu 01 DANH SÁCH ĐĂNG KÝ NGƯỜI HÀNH NGHỀ TẠI CƠ SỞ KHÁM BỆNH, CHỮA BỆNH 1. Tên cơ sở: Trạm Y tế xã "
    "Mường Than 2. Địa chỉ: xã Mường Than, tỉnh Lai Châu STT Họ và tên Số giấy phép hành nghề Phạm vi hành nghề"
)
BAO_CAO_TEXT = "SỞ Y TẾ LAI CHÂU TRẠM Y TẾ XÃ MƯỜNG THAN BÁO CÁO Về tình hình hoạt động khám bệnh, chữa bệnh"
CCCD_TEXT = "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM CĂN CƯỚC CÔNG DÂN Số 034203010212 Họ và tên NHÂM ĐẮC ĐẠT"


def _files(*names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def test_dang_ky_hanh_nghe_attach_rule_xep_dung_dong_khi_llm_loi():
    files = _files("ds1.pdf", "ds2.pdf", "ds3.pdf", "baocao.pdf", "cccd.pdf")
    ocr = [
        {"name": "ds1.pdf", "text": DS_TEXT},
        {"name": "ds2.pdf", "text": DS_TEXT.replace("Mường Than", "Mường Mô")},
        {"name": "ds3.pdf", "text": DS_TEXT.replace("Trạm Y tế xã Mường Than", "Trung tâm Y tế Nậm Nhùn")},
        {"name": "baocao.pdf", "text": BAO_CAO_TEXT},
        {"name": "cccd.pdf", "text": CCCD_TEXT},
    ]
    items, warnings, classified = build_plan_items(files, ocr, {})

    by_file = {item["fileName"]: item for item in items}
    assert set(by_file) == {"ds1.pdf", "ds2.pdf", "ds3.pdf", "baocao.pdf"}
    for name in ("ds1.pdf", "ds2.pdf", "ds3.pdf"):
        assert by_file[name]["componentIndex"] == 1
        assert by_file[name]["target"] == "attp-row"
        assert by_file[name]["loaiBan"] == "Bản chính"
        # 3 file cùng dòng → giữ tên gốc để FE không coi là file trùng.
        assert by_file[name]["documentName"] == name
    assert by_file["baocao.pdf"]["componentIndex"] == 3
    assert by_file["baocao.pdf"]["documentName"] == "Báo cáo"
    assert any(c["fileName"] == "cccd.pdf" and c.get("skipped") for c in classified)
    assert not any("Danh sách đăng ký hành nghề" in w and "bắt buộc" in w for w in warnings)


def test_dang_ky_hanh_nghe_attach_llm_thay_doi_bo_sung_khong_lan_sang_dong_1():
    files = _files("ds.pdf", "thaydoi.pdf", "bosung.pdf", "la.pdf")
    ocr = [
        {"name": "ds.pdf", "text": DS_TEXT},
        {"name": "thaydoi.pdf", "text": DS_TEXT},
        {"name": "bosung.pdf", "text": DS_TEXT},
        {"name": "la.pdf", "text": "Hoá đơn bán hàng"},
    ]
    items, warnings, _ = build_plan_items(files, ocr, {0: "ds_lan_dau", 1: "ds_thay_doi", 2: "ds_bo_sung"})

    by_file = {item["fileName"]: item for item in items}
    assert by_file["ds.pdf"]["componentIndex"] == 1
    assert by_file["ds.pdf"]["documentName"].startswith("Danh sách đăng ký hành nghề (Mẫu 01")
    assert by_file["thaydoi.pdf"]["componentIndex"] == 2
    assert by_file["bosung.pdf"]["componentIndex"] == 4
    # componentName dòng 2/4 KHÔNG được chứa tên dòng 1, nếu không FE khớp "chứa nhau" sẽ rơi vào dòng 1.
    for name in ("thaydoi.pdf", "bosung.pdf"):
        assert "danh sách đăng ký hành nghề" not in by_file[name]["componentName"].lower()
    # File không xác định không bị đính bừa.
    assert "la.pdf" not in by_file
    assert any("la.pdf" in w for w in warnings)
    assert any("Báo cáo" in w for w in warnings)
