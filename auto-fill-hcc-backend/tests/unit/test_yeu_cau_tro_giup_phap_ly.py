"""Pipeline "Thủ tục yêu cầu trợ giúp pháp lý" (2.000829): mapper eForm id 1899 + planner bước 3."""

from app.pipelines.yeu_cau_tro_giup_phap_ly.attach.planner import build_plan_items
from app.pipelines.yeu_cau_tro_giup_phap_ly.process.mapper import enrich
from app.pipelines.yeu_cau_tro_giup_phap_ly.process.schema import UI_COMP_BY_NAME
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

_KEY = "yeu-cau-tro-giup-phap-ly"


def _compact(**values) -> list[dict]:
    return [{"name": name, "comp": "x-input", "value": value} for name, value in values.items()]


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f for f in fields}


def _notice_facts(**extra) -> list[dict]:
    """Thông báo của Cơ quan CSĐT đề nghị cử người trợ giúp cho người chưa thành niên bị buộc tội."""
    base = dict(
        Ndd_HoTen="Lê Văn An",
        Ndd_NgaySinh="05/03/2009",
        Ndd_GioiTinh="Nam",
        Ndd_SoDinhDanh="001209012345",
        Ndd_LoaiGiayTo="Thẻ CCCD",
        Ndd_NgayCap="20/05/2023",
        Ndd_NoiCap="Bộ Công an",
        Ndd_DiaChiLienHe={"quocGia": "Việt Nam", "tinh": "TP. Đà Nẵng", "xa": "xã Hòa Vang",
                          "diaChi": "Trại tạm giam số 1, thôn Đông"},
        Ndd_ThuongTru={"quocGia": "Việt Nam", "tinh": "tỉnh Quảng Trị", "xa": "xã Tân Mỹ", "diaChi": "thôn Bắc"},
        Ndd_Dien="Người bị buộc tội từ 16 tuổi đến dưới 18 tuổi",
        TheCCCD_SoDinhDanh="001209012345",
        TB_TenVanBan="Thông báo về trợ giúp pháp lý",
        TB_So="15/TB-VPCQCSĐT",
        TB_Ngay="01/10/2026",
        TB_CoQuan="Cơ quan Cảnh sát điều tra Công an thành phố Đà Nẵng",
        YeuCau_ToChucTGPL="Trung tâm Trợ giúp pháp lý Nhà nước TP Đà Nẵng",
        YeuCau_DeNghi=("Cơ quan CSĐT Công an TP. Đà Nẵng thông báo và đề nghị Trung tâm Trợ giúp pháp lý Nhà nước "
                       "TP Đà Nẵng cử người thực hiện trợ giúp pháp lý cho Người bị buộc tội: LÊ VĂN AN"),
        YeuCau_GiaiDoan=["Điều tra", "Truy tố", "Xét xử", "Cho đến khi vụ việc kết thúc"],
        YeuCau_VuViec="Trộm cắp tài sản, xảy ra vào ngày 01/6/2026 tại phường Hải Châu, TP. Đà Nẵng",
    )
    base.update(extra)
    return _compact(**base)


def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "2.000829"
    # Nộp tại Sở: khối "Chọn cơ quan thực hiện" tích radio Sở thay vì chọn Phường/Xã.
    assert link["needsAgencySelect"] is True and link["selectSo"] is True
    assert registry.get_procedure(_KEY)["label"] == link["label"]
    assert registry.get_pipeline(_KEY) is not None
    assert registry.get_attach_pipeline(_KEY) is not None


def test_ui_fields_exist_in_eform_template():
    fields, _ = enrich(_notice_facts(), {"formContext": {"applicantFullname": "Trần Thị Bình"}})
    assert fields
    for field in fields:
        assert field["comp"] == UI_COMP_BY_NAME[field["name"]]


def test_beneficiary_section_from_notice_and_card():
    fields, warnings = enrich(_notice_facts(), {"formContext": {"applicantFullname": "Trần Thị Bình"}})
    ui = _by_name(fields)
    assert ui["NguoiDuocTGPL_HoVaTen"]["value"] == "LÊ VĂN AN"
    assert ui["NguoiDuocTGPL_NgaySinh"]["value"] == "05/03/2009"
    assert ui["NguoiDuocTGPL_GioiTinh"]["value"] == "Nam"
    assert ui["NguoiDuocTGPL_SoDinhDanh"]["value"] == "001209012345"
    # Thẻ cấp năm 2023 là CCCD cũ dù Thông báo ghi nơi cấp "Bộ Công an".
    assert ui["NguoiDuocTGPL_LoaiGiayToDinhDanh"]["value"] == "Căn cước công dân"
    # Địa chỉ liên hệ = nơi đang ở (Nơi cư trú), không phải nơi thường trú.
    assert ui["NguoiDuocTGPL_TinhThanh"]["value"] == "Thành phố Đà Nẵng"
    assert ui["NguoiDuocTGPL_PhuongXa"]["value"] == "Xã Hòa Vang"
    assert ui["NguoiDuocTGPL_DiaChi"]["value"] == "Trại tạm giam số 1, thôn Đông"
    assert ui["NguoiDuocTGPL_DienDoiTuong"]["value"] == "Người từ đủ 16 tuổi đến dưới 18 tuổi là người bị buộc tội"
    assert "default" not in ui["NguoiDuocTGPL_DienDoiTuong"]
    assert not any("CCCD/căn cước" in w for w in warnings)


def test_case_content_from_notice():
    fields, _ = enrich(_notice_facts(), {"formContext": {"applicantFullname": "Trần Thị Bình"}})
    ui = _by_name(fields)
    assert ui["KinhGui"]["value"] == "Trung tâm Trợ giúp pháp lý Nhà nước TP Đà Nẵng"
    assert ui["ToChucTGPL_ToChucTiepNhan"]["value"] == ui["KinhGui"]["value"]
    summary = ui["VuViec_TomTatYeuCau"]["value"]
    assert summary.startswith("Cơ quan CSĐT Công an TP. Đà Nẵng thông báo và đề nghị")
    assert "Đề nghị trợ giúp pháp lý ở giai đoạn: Điều tra, Truy tố, Xét xử, Cho đến khi vụ việc kết thúc." in summary
    assert summary.endswith("Thuộc vụ án: Trộm cắp tài sản, xảy ra vào ngày 01/6/2026 tại phường Hải Châu, TP. Đà Nẵng.")
    assert ui["VuViec_HinhThucTGPL"]["value"] == "Tham gia tố tụng"
    assert ui["VuViec_TaiLieuKemTheo"]["value"] == (
        "a) Thông báo về trợ giúp pháp lý số 15/TB-VPCQCSĐT ngày 01/10/2026 của Cơ quan Cảnh sát điều tra "
        "Công an thành phố Đà Nẵng; b) Bản chụp Thẻ căn cước công dân số 001209012345 của Lê Văn An"
    )
    assert ui["LamTai"]["value"] == "Thành phố Đà Nẵng"
    assert ui["KyTen"]["value"] == "TRẦN THỊ BÌNH"
    assert {"Ngay", "Thang", "Nam"} <= set(ui)


def test_requester_prefilled_by_portal_is_not_overwritten():
    fields, warnings = enrich(_notice_facts(), {"formContext": {"applicantFullname": "Trần Thị Bình",
                                                                 "applicantIdentityNumber": "001190054321"}})
    ui = _by_name(fields)
    assert "HoVaTenC" not in ui and "SoDinhDanhC" not in ui
    # Không có Đơn bản giấy → không bịa quan hệ, nhắc cán bộ nhập.
    assert "QuanHe" not in ui
    assert any("Mối quan hệ" in w for w in warnings)


def test_requester_is_beneficiary_relation_self():
    fields, _ = enrich(_notice_facts(), {"formContext": {"applicantFullname": "LÊ VĂN AN",
                                                         "applicantIdentityNumber": "001209012345"}})
    ui = _by_name(fields)
    assert ui["QuanHe"]["value"] == "Bản thân"
    # Cổng đổ sẵn địa chỉ/điện thoại người yêu cầu theo VNeID — không ghi đè bằng nơi người được trợ giúp đang ở.
    assert not {"TT_TinhThanhC", "TT_PhuongXaC", "TT_SoNhaToDanPhoC", "SoDienThoai"} & set(ui)


def test_proof_line_normalizes_ocr_title_and_number():
    fields, _ = enrich(_notice_facts(TB_TenVanBan="THÔNG BÁO VỀ TRỢ GIÚP PHÁP LÝ", TB_So="15 /TB-VPCQCSĐT"), {})
    assert _by_name(fields)["VuViec_TaiLieuKemTheo"]["value"].startswith(
        "a) Thông báo về trợ giúp pháp lý số 15/TB-VPCQCSĐT ngày 01/10/2026"
    )


def test_paper_request_overrides_summary_and_form():
    facts = _notice_facts(
        Nyc_HoTen="Trần Thị Bình", Nyc_QuanHe="Mẹ", Nyc_DienThoai="0901234567",
        YeuCau_HinhThuc="Tư vấn pháp luật", YeuCau_TomTat="Đề nghị tư vấn về quyền của người bị tạm giữ.",
    )
    fields, _ = enrich(facts, {"formContext": {"applicantFullname": "Trần Thị Bình"}})
    ui = _by_name(fields)
    assert ui["QuanHe"]["value"] == "Mẹ"
    assert ui["SoDienThoai"]["value"] == "0901234567"
    assert ui["VuViec_HinhThucTGPL"]["value"] == "Tư vấn pháp luật"
    assert ui["VuViec_TomTatYeuCau"]["value"] == "Đề nghị tư vấn về quyền của người bị tạm giữ."


def test_dien_guessed_from_age_when_notice_omits_it():
    fields, _ = enrich(_notice_facts(Ndd_Dien=""), {})
    ui = _by_name(fields)
    assert ui["NguoiDuocTGPL_DienDoiTuong"]["value"] == "Người từ đủ 16 tuổi đến dưới 18 tuổi là người bị buộc tội"
    assert ui["NguoiDuocTGPL_DienDoiTuong"]["default"] is True


def test_other_dien_categories():
    for text, label in (
        ("Người thuộc hộ cận nghèo, bị buộc tội", "Người bị buộc tội thuộc hộ cận nghèo"),
        ("Người thuộc hộ nghèo", "Người thuộc hộ nghèo"),
        ("Người khuyết tật có khó khăn về tài chính", "Người khuyết tật có khó khăn về tài chính"),
    ):
        fields, _ = enrich(_notice_facts(Ndd_Dien=text), {})
        assert _by_name(fields)["NguoiDuocTGPL_DienDoiTuong"]["value"] == label


def test_prompt_lists_every_portal_dien_option_and_exact_label_passes_through():
    from app.pipelines.yeu_cau_tro_giup_phap_ly.process.prompt import EXTRA_RULES
    from app.pipelines.yeu_cau_tro_giup_phap_ly.process.schema import DIEN_OPTIONS

    for label in DIEN_OPTIONS.values():
        assert f"  - {label}\n" in EXTRA_RULES
    victim = DIEN_OPTIONS["20"]
    fields, _ = enrich(_notice_facts(Ndd_Dien=victim), {})
    field = _by_name(fields)["NguoiDuocTGPL_DienDoiTuong"]
    assert field["value"] == victim and "default" not in field


def test_missing_card_warns_and_skips_card_line():
    fields, warnings = enrich(_notice_facts(TheCCCD_SoDinhDanh=""), {})
    ui = _by_name(fields)
    assert "b)" not in ui["VuViec_TaiLieuKemTheo"]["value"]
    assert any("CCCD/căn cước" in w for w in warnings)


# ---- Bước 3: Thành phần hồ sơ ----

_NOTICE_OCR = ("CÔNG AN TỈNH X CƠ QUAN CẢNH SÁT ĐIỀU TRA THÔNG BÁO VỀ TRỢ GIÚP PHÁP LÝ Kính gửi: Trung tâm Trợ giúp "
               "pháp lý Nhà nước. Thẻ CCCD: 001209012345 Thuộc diện trợ giúp pháp lý: Người bị buộc tội")
_FRONT_OCR = "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số / No.: 001209012345 Họ và tên / Full name: LÊ VĂN AN"
_BACK_OCR = "Đặc điểm nhân dạng / Personal identification IDVNM2090123451001209012345<<8"


def test_plan_merges_notice_and_card_into_row_one():
    files = [{"name": "mat-sau.jpg"}, {"name": "thong-bao.pdf"}, {"name": "mat-truoc.jpg"}]
    ocr = {0: _BACK_OCR, 1: _NOTICE_OCR, 2: _FRONT_OCR}
    attachments, _, warnings = build_plan_items(files, ocr, {})
    assert len(attachments) == 1
    row = attachments[0]
    assert row["target"] == "existing" and row["componentIndex"] == 1
    assert row["componentName"] == "Giấy tờ chứng minh người thuộc diện trợ giúp pháp lý"
    # Tên tệp PDF gộp (FE đặt theo documentName) ngắn gọn, khác chữ của dòng dùng để khớp.
    assert row["documentName"] == "Trợ giúp pháp lý"
    # Thông báo trước, rồi CCCD mặt trước → mặt sau.
    assert row["sourceFileIndexes"] == [1, 2, 0]
    assert warnings == []


def test_plan_never_targets_eform_row_and_adds_paper_request_as_new():
    files = [{"name": "thong-bao.pdf"}, {"name": "don.pdf"}]
    llm = {
        0: {"type": "proof", "documentName": "", "subjectName": ""},
        1: {"type": "paper_request", "documentName": "", "subjectName": ""},
    }
    attachments, _, warnings = build_plan_items(files, {0: _NOTICE_OCR, 1: ""}, llm)
    assert [a["componentIndex"] for a in attachments] == [1, None]
    assert attachments[1]["needsAddComponent"] is True
    assert attachments[1]["componentName"] == "Đơn yêu cầu trợ giúp pháp lý bản giấy"
    assert "sourceFileIndexes" not in attachments[0]
    assert any("CCCD" in w for w in warnings)


def test_rule_fallback_does_not_mistake_notice_for_card():
    attachments, classified, _ = build_plan_items([{"name": "a.pdf"}], {0: _NOTICE_OCR}, {})
    assert classified[0]["type"] == "proof"
    assert attachments[0]["componentIndex"] == 1
