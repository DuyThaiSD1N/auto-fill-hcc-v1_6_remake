"""Pipeline "Đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng" (1.013818): mapper eForm Mẫu TP-TSCC-10 +
planner đính kèm 3 dòng cố định.

Dữ liệu trong test là ví dụ bịa (tên, số giấy tờ, cơ quan) — không lấy từ hồ sơ thật.
"""

from app.pipelines.dang_ky_tham_du_kiem_tra_ket_qua_tap_su_hanh_nghe_cong_chung.attach import planner
from app.pipelines.dang_ky_tham_du_kiem_tra_ket_qua_tap_su_hanh_nghe_cong_chung.attach.planner import (
    build_plan_items,
    rule_types,
)
from app.pipelines.dang_ky_tham_du_kiem_tra_ket_qua_tap_su_hanh_nghe_cong_chung.process import runner as process_runner
from app.pipelines.dang_ky_tham_du_kiem_tra_ket_qua_tap_su_hanh_nghe_cong_chung.process.mapper import enrich
from app.pipelines.dang_ky_tham_du_kiem_tra_ket_qua_tap_su_hanh_nghe_cong_chung.process.schema import (
    LAM_TAI_OPTIONS,
    UI_COMP_BY_NAME,
)
from app.process.schemas import FileItem
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

_KEY = "dang-ky-tham-du-kiem-tra-ket-qua-tap-su-hanh-nghe-cong-chung"

REGISTRATION_TEXT = (
    "Mẫu TP-TSCC-10 Ban hành kèm theo Thông tư số 06/2025/TT-BTP CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM "
    "GIẤY ĐĂNG KÝ THAM DỰ KIỂM TRA KẾT QUẢ TẬP SỰ HÀNH NGHỀ CÔNG CHỨNG Kính gửi: Bộ Tư pháp "
    "Tôi tên là: NGUYỄN THỊ AN; Giới tính: Nữ; Ngày, tháng, năm sinh: 01/02/1990; "
    "Số thẻ căn cước: 001190000123; Thời gian tập sự: 12 tháng; "
    "Đã được công nhận hoàn thành tập sự theo quyết định số: 12/QĐ-STP ngày 01/03/2026 của Sở Tư pháp tỉnh Ninh Bình;"
)
DECISION_TEXT = (
    "UBND TỈNH NINH BÌNH SỞ TƯ PHÁP Số: 12/QĐ-STP BẢN SAO QUYẾT ĐỊNH "
    "Công nhận hoàn thành tập sự hành nghề công chứng GIÁM ĐỐC SỞ TƯ PHÁP "
    "Điều 1. Công nhận hoàn thành tập sự hành nghề công chứng đối với bà Nguyễn Thị An; Số thẻ căn cước công dân: "
    "001190000123. CHỨNG THỰC BẢN SAO ĐÚNG VỚI BẢN CHÍNH"
)
RECEIPT_TEXT = (
    "BIÊN LAI THU TIỀN PHÍ, LỆ PHÍ Tên loại phí: Phí thẩm định tiêu chuẩn, điều kiện hành nghề công chứng "
    "Số tiền: 3.500.000 đồng Người nộp: Nguyễn Thị An"
)
CCCD_TEXT = "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số định danh cá nhân 001190000123 Họ, chữ đệm và tên NGUYỄN THỊ AN"


def _files(*names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _rows(items):
    return {item["componentIndex"]: item for item in items if item["target"] == "existing"}


def _by_component(items):
    return {item["componentIndex"]: item for item in items}


def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.013818"
    assert link["needsAgencySelect"] is True and link["selectSo"] is True
    procedure = registry.get_procedure(_KEY)
    assert procedure["label"] == link["label"]
    assert procedure["mode"] == "agent" and procedure["hasAttachmentStep"] is True
    assert "maThuTuc=1.013818" in procedure["detect"]["urlIncludes"]
    assert registry.get_attach_pipeline(_KEY) is planner.plan
    assert registry.get_pipeline(_KEY) is process_runner.run


def test_rule_types_giay_dang_ky_nhac_quyet_dinh_van_la_giay_dang_ky():
    assert rule_types(REGISTRATION_TEXT) == ["registration"]
    assert rule_types(DECISION_TEXT) == ["decision"]
    assert rule_types(RECEIPT_TEXT) == ["fee_receipt"]
    assert rule_types(CCCD_TEXT) == []
    # File gộp: giấy chính là giấy có tiêu đề xuất hiện trước.
    assert rule_types(REGISTRATION_TEXT + " " + RECEIPT_TEXT) == ["registration", "fee_receipt"]


def test_thieu_chung_tu_nop_phi_dong_2_de_trong_va_canh_bao():
    items, classified, warnings = build_plan_items(
        _files("qd.pdf", "dk.pdf"), {0: DECISION_TEXT, 1: REGISTRATION_TEXT}, {})
    rows = _by_component(items)
    assert set(rows) == {1, None} and len(items) == 2
    assert rows[1]["fileIndex"] == 0 and rows[1]["needsAddComponent"] is False
    assert not any("sourceFileIndexes" in item for item in items)
    assert rows[1]["componentName"] == "Quyết định công nhận hoàn thành tập sự"
    # Dòng 3 là tờ khai điện tử cổng tự sinh (không có nút chọn tệp) → giấy đăng ký đã ký thêm thành phần mới,
    # không được nằm trong kế hoạch dòng 3 (engine không đính được, từng rơi nhầm sang dòng 2).
    registration = rows[None]
    assert registration["fileIndex"] == 1
    assert registration["target"] == "new" and registration["needsAddComponent"] is True
    assert registration["documentName"] == "Giấy đăng ký tham dự kiểm tra kết quả tập sự đã ký"
    assert warnings == [
        "Hồ sơ đã gửi không có giấy tờ chứng minh đã nộp phí thẩm định tiêu chuẩn, điều kiện hành nghề công chứng "
        "(dòng 2). Cần bổ sung.",
        "Dòng 3 là tờ khai điện tử do cổng tự sinh nên Giấy đăng ký đã ký được thêm thành phần hồ sơ mới: dk.pdf.",
    ]
    assert [c["componentIndexes"] for c in classified] == [[1], []]


def test_du_3_giay_khong_canh_bao():
    items, _, warnings = build_plan_items(
        _files("dk.pdf", "bl.jpg", "qd.pdf"), {0: REGISTRATION_TEXT, 1: RECEIPT_TEXT, 2: DECISION_TEXT}, {})
    rows = _by_component(items)
    assert [rows[r]["fileIndex"] for r in (1, 2, None)] == [2, 1, 0]
    assert [item["componentIndex"] for item in items] == [1, 2, None]
    assert len({item["documentName"] for item in items}) == 3
    assert not any("Cần bổ sung" in w for w in warnings)


def test_nhieu_file_cung_dong_gop_mot_pdf_theo_thu_tu_tai_len():
    items, _, _ = build_plan_items(
        _files("qd.pdf", "bl1.jpg", "dk.pdf", "bl2.jpg"),
        {0: DECISION_TEXT, 1: RECEIPT_TEXT, 2: REGISTRATION_TEXT, 3: RECEIPT_TEXT}, {})
    fee = _rows(items)[2]
    assert fee["fileIndex"] == 1 and fee["sourceFileIndexes"] == [1, 3]


def test_file_gop_dang_ky_kem_bien_lai_dinh_nguyen_file_vao_ca_dong_2():
    items, classified, warnings = build_plan_items(
        _files("qd.pdf", "dk_bl.pdf"), {0: DECISION_TEXT, 1: REGISTRATION_TEXT + " " + RECEIPT_TEXT}, {})
    rows = _by_component(items)
    assert rows[2]["fileIndex"] == 1 and rows[None]["fileIndex"] == 1
    assert 3 not in rows
    assert classified[1]["type"] == "registration" and classified[1]["componentIndexes"] == [2]
    assert any("dòng 2: dk_bl.pdf" in w for w in warnings)
    assert not any("Cần bổ sung" in w for w in warnings)


def test_file_gop_khong_dinh_lai_khi_dong_da_co_file_rieng():
    items, classified, warnings = build_plan_items(
        _files("dk_bl.pdf", "bl.jpg"), {0: REGISTRATION_TEXT + " " + RECEIPT_TEXT, 1: RECEIPT_TEXT}, {})
    rows = _rows(items)
    assert rows[2]["fileIndex"] == 1 and "sourceFileIndexes" not in rows[2]
    assert classified[0]["componentIndexes"] == []
    assert not any("nhiều giấy" in w for w in warnings)


def test_can_cuoc_va_giay_khac_them_thanh_phan_moi_khong_bo_file():
    llm = {2: {"type": "other", "documentName": "Giấy xác nhận thời gian tập sự"}, 3: {"type": "other",
                                                                                   "documentName": ""}}
    items, classified, warnings = build_plan_items(
        _files("qd.pdf", "cccd.jpg", "xn.pdf", "la.pdf"), {0: DECISION_TEXT, 1: CCCD_TEXT, 2: "", 3: ""}, llm)
    by_file = {item["fileIndex"]: item for item in items}
    assert set(by_file) == {0, 1, 2, 3}
    for index in (1, 2, 3):
        assert by_file[index]["target"] == "new" and by_file[index]["needsAddComponent"] is True
        assert by_file[index]["componentName"] == by_file[index]["documentName"]
    assert by_file[1]["detectedType"] == "identity" and by_file[1]["documentName"] == "Căn cước công dân"
    assert by_file[2]["documentName"] == "Giấy xác nhận thời gian tập sự"
    assert by_file[3]["documentName"] == "Tài liệu khác"
    assert [c["source"] for c in classified] == ["rule", "default", "llm", "llm"]
    assert any("cccd.jpg, xn.pdf, la.pdf" in w for w in warnings)


def test_llm_phan_loai_file_khong_co_tieu_de():
    items, _, warnings = build_plan_items(
        _files("anh_chuyen_khoan.jpg", "dk.pdf"), {0: "Vietcombank 3.500.000 VND", 1: REGISTRATION_TEXT},
        {0: {"type": "fee_receipt", "documentName": ""}})
    assert _rows(items)[2]["fileIndex"] == 0
    assert any("(dòng 1)" in w for w in warnings) and not any("(dòng 2)" in w for w in warnings)


def test_validated_classifications_bo_index_sai_va_chuan_hoa_type():
    out = planner._validated_classifications(
        [{"fileIndex": 0, "type": "bien_lai"}, {"fileIndex": 5, "type": "decision"}, {"fileIndex": 1, "type": "xyz"},
         {"fileIndex": 0, "type": "decision"}], 2)
    assert out == {0: {"type": "fee_receipt", "documentName": ""}, 1: {"type": "other", "documentName": ""}}


async def test_plan_chi_hoi_llm_file_tieu_de_khong_nhan_ra(monkeypatch):
    texts = {"qd.pdf": DECISION_TEXT, "dk.pdf": REGISTRATION_TEXT, "ck.jpg": "Giao dich 3.500.000"}
    asked: list[list[int]] = []

    async def fake_ocr(files, **_):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in files]

    async def fake_classify(documents):
        asked.append([doc["fileIndex"] for doc in documents])
        # Trả cả index của file rule đã nhận → phải bị bỏ qua.
        return [{"fileIndex": 2, "type": "fee_receipt"}, {"fileIndex": 0, "type": "other"}]

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)
    files = [FileItem(name=n, type="image/jpeg" if n.endswith(".jpg") else "application/pdf", dataUrl="data:,",
                      role="")
             for n in ("qd.pdf", "dk.pdf", "ck.jpg")]
    out = await planner.plan(files, {}, {"request_id": "req-test"})
    assert asked == [[2]]
    assert [(a["componentIndex"], a["fileIndex"]) for a in out["attachments"]] == [(1, 0), (2, 2), (None, 1)]
    assert out["errors"] == ["Dòng 3 là tờ khai điện tử do cổng tự sinh nên Giấy đăng ký đã ký được thêm thành phần hồ sơ mới: dk.pdf."]
    assert out["extracted"]["llmDocuments"] == ["ck.jpg"]
    assert out["extracted"]["attachmentMode"] == "preserve_files"


async def test_plan_llm_loi_van_giu_du_file(monkeypatch):
    async def fake_ocr(files, **_):
        return [{"name": f["name"], "text": CCCD_TEXT if f["name"] == "cccd.jpg" else ""} for f in files]

    async def boom(_documents):
        raise RuntimeError("llm down")

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", boom)
    files = [FileItem(name="cccd.jpg", type="image/jpeg", dataUrl="data:,", role=""),
             FileItem(name="la.pdf", type="application/pdf", dataUrl="data:,", role="")]
    out = await planner.plan(files)
    assert [a["detectedType"] for a in out["attachments"]] == ["identity", "other"]
    assert any(e.startswith("attachment_agent:") for e in out["errors"])
    assert sum("Cần bổ sung" in e for e in out["errors"]) == 2


def test_tro_ly_cung_key_chon_so_va_dien_to_khai():
    from app.channels.handfree.chat.field_review import registry as field_review_registry
    from app.channels.handfree.procedure_registry import get_attach_pipeline, get_pipeline, get_procedure

    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    proc = get_procedure(_KEY)
    lawyer = get_procedure("cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su")
    assert proc["mode"] == "agent" and proc["flowProfile"] == "tu-phap"
    assert proc["keKhaiUrl"] == link["url"]
    assert proc["agencyProvinceOnly"] is True and proc["agencySoFirst"] is True
    assert proc["agencyDeptLabel"] == "Sở Tư pháp"
    # Cùng luồng tờ khai eForm với thủ tục luật sư: chủ hồ sơ bật, không đi toàn trình attach-only.
    assert proc["ownerInfo"]["enabled"] is True and proc["ownerInfo"] == lawyer["ownerInfo"]
    assert proc.get("guidedSteps") == lawyer.get("guidedSteps")
    assert proc.get("requiresConsent") == lawyer.get("requiresConsent")
    assert "maThuTuc=1.013818" in proc["detect"]["urlIncludes"]
    assert [d["key"] for d in proc["requiredDocs"]] == ["quyet_dinh", "nop_phi", "giay_dang_ky", "cccd", "khac"]
    assert get_attach_pipeline(_KEY) is registry.get_attach_pipeline(_KEY)
    assert get_pipeline(_KEY) is registry.get_pipeline(_KEY)
    required = field_review_registry.get(_KEY)["required"]
    assert set(required) <= set(UI_COMP_BY_NAME)
    assert {"HoVaTenC", "ToChucTapSu", "SoQuyetDinhCongNhan", "SoTuPhapCongNhan", "LamTai"} <= set(required)
    assert "Email" not in required and "KyKiemTra" not in required


# ---------------------------------------------------------------- Tờ khai eForm Mẫu TP-TSCC-10 (process/mapper.py)

# Tên ô của eForm thật (crawl tokhaidientu.moj.gov.vn 11/11/2026), đúng loại control.
EFORM_COMPS = {
    "KyKiemTra": "x-input", "KinhGui": "x-input", "HoVaTenC": "x-input", "GioiTinhC": "x-select",
    "NgaySinhC": "x-date", "LoaiGiayToDinhDanhC": "x-select", "SoDinhDanhC": "x-input", "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input", "NO_SoNhaToDanPhoC": "x-input", "NO_TinhThanhC": "x-select", "NO_PhuongXaC": "x-select",
    "SoDienThoai": "x-input", "Email": "x-input", "ToChucTapSu": "x-input", "CongChungVienHuongDan": "x-input",
    "NgayBatDauTapSu": "x-date", "NgayKetThucTapSu": "x-date", "SoQuyetDinhCongNhan": "x-input",
    "NgayQuyetDinhCongNhan": "x-date", "SoTuPhapCongNhan": "x-select", "DaTungThamDuKyKiemTra": "x-input",
    "LamTai": "x-select", "Ngay": "x-input", "Thang": "x-input", "Nam": "x-input", "NguoiDeNghiKy": "x-input",
}
# Option thật của các dropdown (rút gọn những gì test cần).
GENDER_OPTIONS = {"Nam", "Nữ"}
ID_TYPE_OPTIONS = {
    "Giấy khai sinh", "Giấy chứng nhận căn cước", "Chứng minh nhân dân",
    "Giấy chứng minh sỹ quan quân đội nhân dân Việt Nam", "Giấy chứng minh công an nhân dân", "Căn cước công dân",
    "Hộ chiếu", "Sổ hộ khẩu", "Các loại giấy tờ tùy thân khác", "Thẻ căn cước",
}
NEW_PROVINCE_OPTIONS = {
    "Thành phố Bắc Ninh", "Thành phố Cần Thơ", "Thành phố Đà Nẵng", "Thành phố Đồng Nai", "Thành phố Hà Nội",
    "Thành phố Hải Phòng", "Thành phố Hồ Chí Minh", "Thành phố Huế", "Thành phố Quảng Ninh", "Tỉnh An Giang",
    "Tỉnh Cà Mau", "Tỉnh Cao Bằng", "Tỉnh Đắk Lắk", "Tỉnh Điện Biên", "Tỉnh Đồng Tháp", "Tỉnh Gia Lai", "Tỉnh Hà Tĩnh",
    "Tỉnh Hưng Yên", "Tỉnh Khánh Hòa", "Tỉnh Lai Châu", "Tỉnh Lâm Đồng", "Tỉnh Lạng Sơn", "Tỉnh Lào Cai",
    "Tỉnh Nghệ An", "Tỉnh Ninh Bình", "Tỉnh Phú Thọ", "Tỉnh Quảng Ngãi", "Tỉnh Quảng Trị", "Tỉnh Sơn La",
    "Tỉnh Tây Ninh", "Tỉnh Thái Nguyên", "Tỉnh Thanh Hóa", "Tỉnh Tuyên Quang", "Tỉnh Vĩnh Long",
}


def _compact(**values) -> list[dict]:
    return [{"name": name, "comp": "x-input", "value": value} for name, value in values.items()]


def _ui(fields: list[dict]) -> dict:
    return {f["name"]: f for f in fields}


def _facts(**extra) -> list[dict]:
    # Ví dụ bịa theo khuôn Giấy đăng ký + Quyết định công nhận.
    base = dict(
        KyKiemTra="lần thứ hai",
        KinhGui="Bộ Tư pháp",
        Ndn_HoTen="Nguyễn Thị An",
        Ndn_GioiTinh="Nữ",
        Ndn_NgaySinh="1/2/1990",
        Ndn_SoDinhDanh="001 190 000 123",
        Ndn_NgayCap="15/3/2021",
        Ndn_NoiCap="Cục Cảnh sát Quản lý hành chính về trật tự xã hội (đối với thẻ căn cước công dân/thẻ căn cước)",
        Ndn_NoiOHienTai={"quocGia": "Việt Nam", "tinh": "tỉnh Ninh Bình", "xa": "phường Hoa Lư",
                         "chiTietDuoiXa": "Số 9 đường Trần Hưng Đạo"},
        Ndn_DienThoai="0901.000.111",
        Ndn_Email="an.nguyen@example.com",
        TapSu_ToChuc="Văn phòng công chứng Bình An - Địa chỉ: Số 1 đường Lê Lợi, phường Hoa Lư, tỉnh Ninh Bình;",
        TapSu_CongChungVien="Công chứng viên Trần Văn Bình; Thẻ công chứng viên số 01/CCV tháng 01/2020;",
        TapSu_TuNgay="01/02/2025",
        TapSu_DenNgay="01/02/2026",
        TapSu_SoThang="12",
        QD_CongNhan={"so": "Số: 12 / QĐ-STP", "ngay": "1/3/2026", "tinh": "Sở Tư pháp tỉnh Ninh Bình"},
        DK_QuyetDinh={"so": "12/QĐ-STP", "ngay": "01/03/2026", "tinh": "Ninh Bình"},
        DaTungThamDu="Chưa tham dự kỳ kiểm tra kết quả tập sự hành nghề công chứng nào;",
        LamDon_NoiNgay={"diaDanh": "Ninh Bình", "ngay": "4/11/2026"},
    )
    base.update(extra)
    return _compact(**base)


def test_o_ui_dung_ten_va_loai_control_eform_that():
    assert UI_COMP_BY_NAME == EFORM_COMPS
    fields, _ = enrich(_facts(), {})
    assert {f["name"] for f in fields} == set(EFORM_COMPS), "hồ sơ đủ giấy thì điền đủ mọi ô của eForm"
    for field in fields:
        assert field["comp"] == EFORM_COMPS[field["name"]]
        assert field["value"] not in ("", None)


def test_nhan_than_nguoi_tap_su():
    fields, warnings = enrich(_facts(), {})
    ui = _ui(fields)
    assert ui["KyKiemTra"]["value"] == "lần thứ hai"
    assert ui["KinhGui"]["value"] == "Bộ Tư pháp" and "default" not in ui["KinhGui"]
    assert ui["HoVaTenC"]["value"] == "NGUYỄN THỊ AN"
    assert ui["GioiTinhC"]["value"] == "Nữ" and ui["GioiTinhC"]["value"] in GENDER_OPTIONS
    assert ui["NgaySinhC"]["value"] == "01/02/1990"
    assert ui["SoDinhDanhC"]["value"] == "001190000123"
    # CCCD cấp trước 01/7/2024: Căn cước công dân, nơi cấp Cục CSQLHC (bỏ phần hướng dẫn in nghiêng của mẫu).
    assert ui["LoaiGiayToDinhDanhC"]["value"] == "Căn cước công dân"
    assert ui["NgayCapDDC"]["value"] == "15/03/2021"
    assert ui["NoiCapDDC"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert ui["NO_TinhThanhC"]["value"] == "Tỉnh Ninh Bình" and ui["NO_TinhThanhC"]["value"] in NEW_PROVINCE_OPTIONS
    assert ui["NO_PhuongXaC"]["value"] == "Phường Hoa Lư"
    assert ui["NO_SoNhaToDanPhoC"]["value"] == "Số 9 đường Trần Hưng Đạo"
    assert ui["SoDienThoai"]["value"] == "0901000111"
    assert ui["Email"]["value"] == "an.nguyen@example.com"
    assert ui["NguoiDeNghiKy"]["value"] == "Nguyễn Thị An"
    assert warnings == []


def test_qua_trinh_tap_su_va_quyet_dinh_cong_nhan():
    ui = _ui(enrich(_facts(), {})[0])
    assert ui["ToChucTapSu"]["value"] == (
        "Văn phòng công chứng Bình An - Địa chỉ: Số 1 đường Lê Lợi, phường Hoa Lư, tỉnh Ninh Bình")
    assert ui["CongChungVienHuongDan"]["value"] == "Công chứng viên Trần Văn Bình; Thẻ công chứng viên số 01/CCV tháng 01/2020"
    assert (ui["NgayBatDauTapSu"]["value"], ui["NgayKetThucTapSu"]["value"]) == ("01/02/2025", "01/02/2026")
    assert ui["SoQuyetDinhCongNhan"]["value"] == "12/QĐ-STP"
    assert ui["NgayQuyetDinhCongNhan"]["value"] == "01/03/2026"
    assert ui["SoTuPhapCongNhan"]["value"] == "Tỉnh Ninh Bình"
    assert ui["DaTungThamDuKyKiemTra"]["value"] == "Chưa tham dự kỳ kiểm tra kết quả tập sự hành nghề công chứng nào"


def test_noi_ngay_lam_giay_chon_dung_option_lam_tai():
    ui = _ui(enrich(_facts(), {})[0])
    assert ui["LamTai"]["value"] == "Tỉnh Ninh Bình" and "default" not in ui["LamTai"]
    assert (ui["Ngay"]["value"], ui["Thang"]["value"], ui["Nam"]["value"]) == ("04", "11", "2026")


def test_lam_tai_danh_muc_cu_khac_danh_muc_tinh_moi():
    # LamTai ghi "Tỉnh Bắc Ninh" / "Tỉnh Thành phố Huế", ô tỉnh nơi ở + Sở Tư pháp ghi "Thành phố ...".
    cases = {"Bắc Ninh": ("Tỉnh Bắc Ninh", "Thành phố Bắc Ninh"), "TP. Huế": ("Tỉnh Thành phố Huế", "Thành phố Huế"),
             "Cần Thơ": ("Tỉnh Thành phố Cần Thơ", "Thành phố Cần Thơ"), "Hà Nội": ("Thành phố Hà Nội", "Thành phố Hà Nội"),
             "Quảng Ninh": ("Thành phố Quảng Ninh", "Thành phố Quảng Ninh")}
    for place, (lam_tai, new_label) in cases.items():
        ui = _ui(enrich(_facts(LamDon_NoiNgay={"diaDanh": place, "ngay": ""},
                               QD_CongNhan={"so": "1/QĐ-STP", "ngay": "", "tinh": f"Sở Tư pháp {place}"}), {})[0])
        assert ui["LamTai"]["value"] == lam_tai and lam_tai in LAM_TAI_OPTIONS, place
        assert ui["SoTuPhapCongNhan"]["value"] == new_label and new_label in NEW_PROVINCE_OPTIONS, place
        assert "Ngay" not in ui, "ngày làm giấy đọc không được thì để cổng giữ ngày hôm nay"


def test_lam_tai_khong_doc_duoc_lay_tinh_noi_o_va_danh_dau_mac_dinh():
    ui = _ui(enrich(_facts(LamDon_NoiNgay={"diaDanh": "", "ngay": "05/11/2026"}), {})[0])
    assert ui["LamTai"]["value"] == "Tỉnh Ninh Bình" and ui["LamTai"]["default"] is True
    assert ui["Ngay"]["value"] == "05"


def test_moi_option_lam_tai_deu_doi_ra_tinh_moi():
    for option in LAM_TAI_OPTIONS:
        ui = _ui(enrich(_facts(LamDon_NoiNgay={"diaDanh": option}), {})[0])
        assert ui["LamTai"]["value"] == option


def test_the_can_cuoc_cap_sau_01_7_2024_do_bo_cong_an_cap():
    ui = _ui(enrich(_facts(Ndn_NgayCap="10/08/2025", Ndn_NoiCap="Cục CSQLHC về TTXH",
                           Ndn_LoaiGiayTo="Căn cước công dân"), {})[0])
    assert ui["NoiCapDDC"]["value"] == "Bộ Công an"
    assert ui["LoaiGiayToDinhDanhC"]["value"] == "Thẻ căn cước" and ui["LoaiGiayToDinhDanhC"]["value"] in ID_TYPE_OPTIONS


def test_khong_doc_duoc_kinh_gui_dien_bo_tu_phap_mac_dinh():
    ui = _ui(enrich(_facts(KinhGui=""), {})[0])
    assert ui["KinhGui"]["value"] == "Bộ Tư pháp" and ui["KinhGui"]["default"] is True


def test_ky_kiem_tra_bo_chu_in_san_cua_mau():
    ui = _ui(enrich(_facts(KyKiemTra="(Kỳ kiểm tra kết quả tập sự hành nghề công chứng lần thứ hai)"), {})[0])
    assert ui["KyKiemTra"]["value"] == "lần thứ hai"
    assert "KyKiemTra" not in _ui(enrich(_facts(KyKiemTra=""), {})[0])


def test_so_quyet_dinh_viet_tay_khong_doc_duoc_lay_theo_giay_dang_ky():
    fields, warnings = enrich(_facts(QD_CongNhan={"so": "", "ngay": "01/03/2026", "tinh": "Ninh Bình"}), {})
    ui = _ui(fields)
    assert ui["SoQuyetDinhCongNhan"]["value"] == "12/QĐ-STP"
    assert warnings == []


def test_hai_nguon_quyet_dinh_lech_thi_canh_bao_va_theo_quyet_dinh():
    fields, warnings = enrich(_facts(DK_QuyetDinh={"so": "21/QĐ-STP", "ngay": "02/03/2026", "tinh": "Ninh Bình"}), {})
    ui = _ui(fields)
    assert ui["SoQuyetDinhCongNhan"]["value"] == "12/QĐ-STP"
    assert ui["NgayQuyetDinhCongNhan"]["value"] == "01/03/2026"
    assert any("Số quyết định công nhận" in w and "21/QĐ-STP" in w for w in warnings)
    assert any("Ngày quyết định công nhận" in w for w in warnings)


def test_so_quyet_dinh_chi_khac_khoang_trang_khong_canh_bao():
    _, warnings = enrich(_facts(DK_QuyetDinh={"so": "12 /QĐ-STP", "ngay": "01/03/2026", "tinh": "Ninh Bình"}), {})
    assert warnings == []


def test_thieu_ca_hai_nguon_quyet_dinh_thi_canh_bao_nhap_tay():
    fields, warnings = enrich(_facts(QD_CongNhan={}, DK_QuyetDinh={}), {})
    ui = _ui(fields)
    assert "SoQuyetDinhCongNhan" not in ui and "SoTuPhapCongNhan" not in ui
    assert any("Chưa đọc được số quyết định" in w for w in warnings)


def test_thoi_gian_tap_su_sai_thu_tu_hoac_khac_12_thang_thi_canh_bao():
    _, warnings = enrich(_facts(TapSu_TuNgay="01/02/2026", TapSu_DenNgay="01/02/2025"), {})
    assert any("Thời gian tập sự" in w for w in warnings)
    _, warnings = enrich(_facts(TapSu_SoThang="18"), {})
    assert any("18 tháng" in w for w in warnings)


def test_ngay_khong_day_du_thi_bo_trong():
    ui = _ui(enrich(_facts(Ndn_NgaySinh="1990", TapSu_TuNgay="02/2025"), {})[0])
    assert "NgaySinhC" not in ui and "NgayBatDauTapSu" not in ui


def test_gioi_tinh_suy_tu_ong_ba_cua_quyet_dinh():
    assert _ui(enrich(_facts(Ndn_GioiTinh="bà"), {})[0])["GioiTinhC"]["value"] == "Nữ"
    assert _ui(enrich(_facts(Ndn_GioiTinh="Ông"), {})[0])["GioiTinhC"]["value"] == "Nam"


def test_tai_khoan_khong_phai_nguoi_tap_su_thi_canh_bao():
    _, warnings = enrich(_facts(), {"formContext": {"applicantFullname": "Lê Văn Cường"}})
    assert any("không phải người tập sự" in w for w in warnings)
    _, warnings = enrich(_facts(), {"formContext": {"applicantFullname": "NGUYỄN THỊ AN",
                                                    "applicantIdentityNumber": "001190000123"}})
    assert warnings == []


def test_ho_so_rong_khong_bia_o_nao():
    fields, warnings = enrich([], {})
    # Chỉ dòng Kính gửi in sẵn "Bộ Tư pháp" của mẫu.
    assert [(f["name"], f["value"]) for f in fields] == [("KinhGui", "Bộ Tư pháp")]
    assert any("họ tên người tập sự" in w for w in warnings)


async def test_run_noi_mapper_va_gop_canh_bao(monkeypatch):
    captured = {}

    async def fake_run(files_by_role, **kwargs):
        captured.update(kwargs)
        return {"fields": _facts(DK_QuyetDinh={"so": "99/QĐ-STP", "ngay": "01/03/2026", "tinh": "Ninh Bình"}),
                "errors": ["ocr: chậm"]}

    monkeypatch.setattr(process_runner.runner, "run", fake_run)
    res = await process_runner.run({"": []}, {})
    assert {f["name"] for f in res["fields"]} == set(EFORM_COMPS)
    assert res["errors"][0] == "ocr: chậm" and any("99/QĐ-STP" in e for e in res["errors"][1:])
    assert "QD_CongNhan" in captured["allowed"] and captured["comp_by_name"]["Ndn_NoiOHienTai"] == "x-select-area"
    assert "Mẫu TP-TSCC-10" in captured["extra_rules"]
