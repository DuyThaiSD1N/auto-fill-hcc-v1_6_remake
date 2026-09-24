"""Unit test pipeline "Gia hạn Chứng chỉ hành nghề thú y" (2.001064): mapper + planner đính kèm."""

import asyncio

from app.attachments.schemas import AttachmentPlanItem
from app.pipelines.gia_han_chung_chi_hanh_nghe_thu_y.attach import planner
from app.pipelines.gia_han_chung_chi_hanh_nghe_thu_y.process import mapper, runner
from app.pipelines.gia_han_chung_chi_hanh_nghe_thu_y.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures import registry


def _fields(**values):
    return [{"name": k, "value": v} for k, v in values.items()]


def _by_name(out):
    result = {}
    for field in out:
        result.setdefault(field["name"], []).append(field)
    return result


_BASE = dict(
    NguoiDeNghi_HoTen="NGUYỄN THỊ AN",
    NguoiDeNghi_NgaySinh="05/03/1998",
    NguoiDeNghi_SoDinhDanh="001198000111",
    NguoiDeNghi_NgayCapCCCD="10/08/2021",
    NguoiDeNghi_GioiTinh="Nữ",
    NguoiDeNghi_NoiCapCCCD="Cục CS QLHC về TTXH",
    NguoiDeNghi_ThuongTru={"quocGia": "Việt Nam", "tinh": "Tỉnh Lào Cai", "xa": "Phường Cam Đường",
                           "diaChi": "Tổ 5"},
    NguoiDeNghi_DienThoai="0912 345 678",
    Don_KinhGui="Chi cục Chăn nuôi và Thú y tỉnh Lào Cai",
    Don_LaNguoiNuocNgoai="Không",
    Don_BangCapChuyenMon="Cao đẳng",
    Don_PhamViHanhNghe=(
        "Tiêm phòng, chữa bệnh, tiểu phẫu (thiến, cắt đuôi) động vật, tư vấn các hoạt động liên quan đến "
        "lĩnh vực thú y; Buôn bán thuốc thú y dùng trong thú y cho động vật trên cạn"
    ),
    Don_DiaDiem="Lào Cai",
    Don_NgayLamDon="02/02/2026",
    Don_NguoiLamDon="Nguyễn Thị An",
    CCHNCu_SoDangKy="45/CCHN-TY",
    CCHNCu_NgayHetHan="01/03/2026",
)


def test_schema_khong_co_o_ly_do_va_dang_ky_registry():
    assert "data[lyDo]" not in UI_COMP_BY_NAME
    assert not any("LyDo" in name for name in ALLOWED)
    assert registry._PIPELINE["gia-han-chung-chi-hanh-nghe-thu-y"] is runner.run
    assert registry._ATTACH_PIPELINE["gia-han-chung-chi-hanh-nghe-thu-y"] is planner.plan
    assert registry._BY_KEY["gia-han-chung-chi-hanh-nghe-thu-y"]["hasAttachmentStep"] is True


def test_detect_nhan_ra_ca_buoc_ke_khai_lan_buoc_thanh_phan_ho_so():
    # Popup đòi trang chứa ĐỦ mọi cụm textIncludes → mọi cụm phải có ở CẢ bước "Thành phần hồ sơ".
    detect = registry._BY_KEY["gia-han-chung-chi-hanh-nghe-thu-y"]["detect"]
    buoc_dinh_kem = (
        "gia hạn chứng chỉ hành nghề thú y sở nông nghiệp và môi trường thành phần hồ sơ "
        "giấy chứng nhận sức khỏe đơn đăng ký gia hạn theo mẫu số 02.hnty thêm giấy tờ"
    )
    buoc_ke_khai = "gia hạn chứng chỉ hành nghề thú y đơn đăng ký gia hạn cấp chứng chỉ hành nghề thú y"
    for body in (buoc_dinh_kem, buoc_ke_khai):
        assert all(phrase.lower() in body for phrase in detect["textIncludes"])
    cap_lai = registry._BY_KEY["cap-lai-chung-chi-hanh-nghe-thu-y"]["detect"]["textIncludes"]
    assert not all(phrase.lower() in buoc_dinh_kem for phrase in cap_lai)


def test_mapper_do_nguoi_de_nghi_vao_chu_ho_so_va_to_don_khong_cham_phan_i():
    out, warnings = mapper.enrich(_fields(**_BASE))
    by = _by_name(out)

    assert by["data[isOwnerDossierCheck]"][0]["value"] is False
    assert by["data[ownerFullname]"][0]["value"] == "NGUYỄN THỊ AN"
    assert by["data[ownerGender]"][0]["value"] == "Nữ"
    assert by["data[ownerIdentityNumber]"][0]["value"] == "001198000111"
    assert by["data[ownerIdIssuePlace]"][0]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by["data[ownerProvince]"][0]["value"] == "Tỉnh Lào Cai"
    assert by["data[ownerAddress]"][0]["value"] == "Tổ 5"
    assert by["data[ownerPhoneNumber]"][0]["value"] == "0912345678"

    # Ô tờ đơn trùng field-key Phần I → bắt buộc kèm scope tờ đơn.
    for key in ("data[fullname]", "data[birthday]", "data[identityNumber]", "data[province]", "data[address]"):
        assert by[key][0]["scope"].startswith(".formio-component-thongTinChung:has(")
        assert "data[chonDoiTuong]" in by[key][0]["scopeAway"]
    assert "data[chonDoiTuong]" not in by
    assert "data[lyDo]" not in by
    assert "data[toiLaNguoiNuocNgoai]" not in by

    labels = [f["optionLabel"] for f in by["data[deNghi][]"]]
    assert len(labels) == 2
    assert labels[1] == "Buôn bán thuốc thú y dùng trong thú y cho động vật trên cạn."
    assert by["data[soDK]"][0]["value"] == "45"
    assert by["data[ngayCC]"][0]["value"] == "01/03/2026"
    assert by["data[diaDiem]"][0]["value"] == "Lào Cai"
    assert by["data[thoiGian]"][0]["value"] == "02/02/2026"
    assert warnings == []


def test_mapper_dia_chi_chi_toi_phuong_va_thieu_cchn_cu_thi_canh_bao():
    values = dict(_BASE, NguoiDeNghi_ThuongTru="Phường Cam Đường - Tỉnh Lào Cai")
    values.pop("CCHNCu_SoDangKy")
    values.pop("CCHNCu_NgayHetHan")
    out, warnings = mapper.enrich(_fields(**values))
    by = _by_name(out)

    # "Phường X - Tỉnh Y" → phường vào ô xã, KHÔNG vào địa chỉ chi tiết.
    assert by["data[ownerDistrict]"][0]["value"] == "Phường Cam Đường"
    assert "data[ownerAddress]" not in by
    assert "data[soDK]" not in by
    assert any("Địa chỉ chi tiết" in w for w in warnings)
    assert any("Số đăng ký" in w for w in warnings)


def _plan(files, texts, llm_types=None):
    ocr = [{"name": f["name"], "text": texts.get(f["name"], "")} for f in files]
    items, warnings, classified = planner.build_plan_items(files, ocr, llm_types)
    # Response model KHÔNG được lược mất field mới (fallbackComponentName / untickRows).
    dumped = [AttachmentPlanItem(**item).model_dump(exclude_none=True) for item in items]
    return dumped, warnings, {c["fileName"]: c for c in classified}


_TEXTS = {
    "don.pdf": "ĐƠN ĐĂNG KÝ GIA HẠN CHỨNG CHỈ HÀNH NGHỀ THÚ Y Kính gửi Chi cục Tên tôi là Bằng cấp chuyên môn",
    "gksk.pdf": "GIẤY KHÁM SỨC KHOẺ Họ và tên Tiền sử bệnh KHÁM LÂM SÀNG KẾT LUẬN Lý do khám: cấp chứng chỉ hành nghề",
    "bang.pdf": "BẢN SAO BẰNG TỐT NGHIỆP CAO ĐẲNG HIỆU TRƯỞNG Số hiệu Số vào sổ gốc cấp bằng tốt nghiệp",
    "cccd.jpg": "CĂN CƯỚC CÔNG DÂN Số định danh cá nhân Họ và tên",
}
_FILES = [
    {"name": "don.pdf", "type": "application/pdf"},
    {"name": "gksk.pdf", "type": "application/pdf"},
    {"name": "bang.pdf", "type": "application/pdf"},
    {"name": "cccd.jpg", "type": "image/jpeg"},
]


def test_planner_rule_fallback_du_3_dong_va_bo_tick_giay_phep_lao_dong():
    # Văn bằng đứng ĐẦU danh sách: untickRows vẫn phải nằm trên item attp-row (chạy trước modal).
    items, warnings, classified = _plan([_FILES[2], _FILES[0], _FILES[1], _FILES[3]], _TEXTS)
    by_file = {item["fileName"]: item for item in items}

    assert warnings == []
    assert by_file["gksk.pdf"]["target"] == "attp-row"
    assert by_file["gksk.pdf"]["componentName"] == "Giấy chứng nhận sức khỏe"
    assert by_file["gksk.pdf"]["loaiBan"] == "Bản chính"
    assert by_file["don.pdf"]["componentName"].startswith("Đơn đăng ký gia hạn theo Mẫu số 02.HNTY")
    assert by_file["don.pdf"]["documentName"] == "don.pdf"

    bang = by_file["bang.pdf"]
    assert bang["target"] == "add-document-dialog"
    assert bang["needsAddComponent"] is True
    assert bang["loaiBan"] == "Bản sao"
    assert bang["componentName"].startswith("Văn bằng, chứng chỉ chuyên môn")
    assert bang["fallbackComponentName"] == by_file["don.pdf"]["componentName"]

    assert "cccd.jpg" not in by_file
    assert classified["cccd.jpg"]["skipped"] is True
    # Công dân Việt Nam → dòng Giấy phép lao động (cổng tick sẵn) phải được bỏ tick.
    carriers = [item for item in items if "untickRows" in item]
    assert len(carriers) == 1 and carriers[0]["target"] == "attp-row"
    assert carriers[0]["untickRows"] == [planner._ROWS["giay_phep_lao_dong"]["componentName"]]


def test_planner_llm_primary_va_giay_to_khac_dinh_chung_dong_don():
    files = _FILES + [{"name": "cchn.pdf", "type": "application/pdf"}, {"name": "la.pdf", "type": "application/pdf"}]
    texts = dict(_TEXTS, **{"cchn.pdf": "CHỨNG CHỈ HÀNH NGHỀ THÚ Y Số đăng ký", "la.pdf": "văn bản lạ"})
    # LLM phân loại nhầm bằng thành cchn_cu thì vẫn theo LLM (LLM-primary); other → rule dự phòng.
    llm = {0: "don_gia_han", 1: "gksk", 2: "van_bang", 3: "cccd", 4: "cchn_cu", 5: "other"}
    items, warnings, classified = _plan(files, texts, llm)
    by_file = {item["fileName"]: item for item in items}

    don_row = planner._ROWS["don_gia_han"]["componentName"]
    assert by_file["cchn.pdf"]["componentName"] == don_row
    assert by_file["cchn.pdf"]["documentName"] == "cchn.pdf"
    assert by_file["la.pdf"]["componentName"] == don_row
    assert classified["la.pdf"]["docType"] == "other"
    assert any("la.pdf" in w for w in warnings)


def test_planner_co_giay_phep_lao_dong_thi_khong_bo_tick_va_bao_thieu_gksk():
    files = [{"name": "don.pdf", "type": "application/pdf"}, {"name": "gpld.pdf", "type": "application/pdf"}]
    texts = {"don.pdf": _TEXTS["don.pdf"], "gpld.pdf": "GIẤY PHÉP LAO ĐỘNG Work permit"}
    items, warnings, _ = _plan(files, texts)

    assert all("untickRows" not in item for item in items)
    gpld = next(item for item in items if item["fileName"] == "gpld.pdf")
    assert gpld["componentName"].startswith("Giấy phép lao động")
    assert any("Giấy khám sức khỏe" in w for w in warnings)


def test_normalize_doc_type():
    assert planner._normalize_doc_type("giay_phep_lao_dong") == "giay_phep_lao_dong"
    assert planner._normalize_doc_type("Giấy khám sức khỏe") == "gksk"
    assert planner._normalize_doc_type("bang_tot_nghiep") == "van_bang"
    assert planner._normalize_doc_type("xyz") == "other"


def test_submitter_context_tach_nguoi_nop():
    docs = [{"text": "CĂN CƯỚC CÔNG DÂN Họ và tên TRẦN VĂN BÌNH Số 001090000222"}]
    ctx = asyncio.run(runner._submitter_context(
        docs, {"formContext": {"applicantFullname": "Trần Văn Bình", "applicantIdentityNumber": "001090000222"}}
    ))
    assert 'result="co_giay_to"' in ctx
    assert asyncio.run(runner._submitter_context(docs, {})) == ""
