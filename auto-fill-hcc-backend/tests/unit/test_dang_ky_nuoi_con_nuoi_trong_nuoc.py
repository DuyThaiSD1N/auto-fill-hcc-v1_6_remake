"""Tests for "Đăng ký việc nuôi con nuôi trong nước" (process mapper + attachment planner)."""

from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc import process as agent
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.attach import plan as attach_plan
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.attach import planner
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.process import mapper
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "dang-ky-nuoi-con-nuoi-trong-nuoc"

FATHER_ID = "001090012345"
MOTHER_ID = "001190067890"
CHILD_ID = "001325000111"
BIRTH_MOTHER_ID = "012305000999"


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _by_name(mapped: list[dict]) -> dict:
    return {f["name"]: f for f in mapped}


def _values(mapped: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in mapped}


def _couple_fields() -> list[dict]:
    home = {"quocGia": "Việt Nam", "tinh": "Tỉnh Ninh Bình", "xa": "Phường Hoa Lư", "diaChi": "Tổ 7"}
    return [
        _field("AdoptiveFather_FullName", "Trần Văn Bình"),
        _field("AdoptiveFather_BirthDate", "5/3/1985"),
        _field("AdoptiveFather_Ethnicity", "Kinh"),
        _field("AdoptiveFather_IdNumber", FATHER_ID),
        _field("AdoptiveFather_IdIssueDate", "10/08/2021"),
        _field("AdoptiveFather_IdIssuePlace", "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"),
        _field("AdoptiveFather_Residence", home),
        _field("AdoptiveFather_Phone", "0900000001"),
        _field("AdoptiveMother_FullName", "Nguyễn Thị Hoa"),
        _field("AdoptiveMother_BirthDate", "20/11/1987"),
        _field("AdoptiveMother_IdNumber", MOTHER_ID),
        _field("AdoptiveMother_IdIssueDate", "15/09/2024"),
        _field("AdoptiveMother_Residence", home),
        _field("AdoptiveMother_Phone", "0900000002"),
        _field("Child_FullName", "Trần Minh An"),
        _field("Child_BirthDate", "01/02/2026"),
        _field("Child_Gender", "Nữ"),
        _field("Child_Ethnicity", "Kinh"),
        _field("Child_IdNumber", CHILD_ID),
        _field("Child_BirthPlace", {
            "quocGia": "Việt Nam", "tinh": "Tỉnh Ninh Bình", "xa": "Phường Hoa Lư",
            "diaChi": "Bệnh viện Đa khoa tỉnh Ninh Bình",
        }),
        _field("Child_Residence", {"quocGia": "Việt Nam", "tinh": "Tỉnh Ninh Bình", "xa": "Xã Gia Viễn", "diaChi": "Thôn 3"}),
        _field("LivingWith_Type", "Gia đình"),
        _field("LivingWith_FullName", "Nguyễn Thị Hoa, Trần Văn Bình"),
        _field("LivingWith_Phone", "0900000002"),
        _field("Registration_Agency", "Ủy ban nhân dân phường Hoa Lư, tỉnh Ninh Bình"),
    ]


def test_registered():
    proc = get_procedure(KEY)

    assert proc
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["label"] == "Đăng ký việc nuôi con nuôi trong nước"
    assert get_pipeline(KEY) is agent.run
    assert get_attach_pipeline(KEY) is attach_plan


def test_schema_compact_fields_are_not_ui_names():
    assert not ALLOWED & set(UI_COMP_BY_NAME)


def test_couple_maps_requester_child_and_both_adopters():
    mapped = mapper.enrich(_couple_fields(), {})
    values = _values(mapped)
    fields = _by_name(mapped)

    # I. Người yêu cầu = cha nuôi.
    assert values["HoVaTenC"] == "TRẦN VĂN BÌNH"
    assert values["SoDinhDanhC"] == FATHER_ID
    assert values["LoaiGiayToDinhDanhC"] == "Căn cước công dân"
    assert values["NoiCapDDC"] == "Cục trưởng Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["TT_TinhThanhC"] == "Tỉnh Ninh Bình"
    assert values["TT_PhuongXaC"] == "Phường Hoa Lư"
    assert values["TT_SoNhaToDanPhoC"] == "Tổ 7"

    # II. Con nuôi.
    assert values["HoVaTenCN"] == "TRẦN MINH AN"
    assert values["NgaySinhCN"] == "01/02/2026"
    assert values["QuocTichCN"] == "Việt Nam"
    assert values["SoDinhDanhCN"] == CHILD_ID
    # Trẻ chưa có thẻ căn cước → mục (11) giấy tờ tùy thân để trống.
    for name in ("LoaiGiayToDinhDanhCN", "SoGiayToTuyThanCN", "NgayCapDDCN", "NoiCapDDCN"):
        assert name not in values
    assert values["NoiCuTruCN"] == "Trong Nước"
    assert values["NoiCuTruCN_TrongNuoc"]["diaChi"] == "Thôn 3"
    assert values["NoiSinhCN_TrongNuoc"]["diaChi"] == "Bệnh viện Đa khoa tỉnh Ninh Bình"
    # Đơn để trống "Thuộc đối tượng" nhưng trẻ sống tại gia đình → suy ra, tô vàng.
    assert values["ncDoiTuong"] == "Trẻ em sống tại gia đình"
    assert fields["ncDoiTuong"]["default"] is True

    # III/IV. Vợ chồng cùng nhận: khối VoChongNhanNuoi, địa chỉ là ô chữ.
    assert values["truongHopNhanNuoi"] == "Vợ, chồng nhận nuôi con nuôi"
    assert "ChonNguoiDonThanNhanNuoi" not in values
    assert values["HoVaTenM"] == "NGUYỄN THỊ HOA"
    assert values["NgaySinhM"] == "20/11/1987"
    assert values["SoGiayToDinhDanhM"] == MOTHER_ID
    # Ngày cấp sau 01/7/2024, không đọc được nơi cấp → thẻ căn cước mới của Bộ Công an.
    assert values["LoaiGiayToDinhDanhM"] == "Thẻ căn cước"
    assert values["NoiCapDDM"] == "Bộ Công an"
    assert values["DiaChiM"] == "Tổ 7, Phường Hoa Lư, Tỉnh Ninh Bình"
    assert values["NoiCuTruM_QuocGia"] == "Việt Nam"
    assert "NoiCuTruM_TrongNuoc" not in values
    assert values["HoVaTenCha"] == "TRẦN VĂN BÌNH"
    assert values["NgaySinhCha"] == "05/03/1985"
    assert values["DanTocCha"] == "Kinh"
    assert values["MeDoiTuong"] == "Khác" and fields["MeDoiTuong"]["default"] is True
    assert values["ChaDoiTuong"] == "Khác"
    assert fields["HoVaTenM"]["comp"] == "raw"
    assert fields["DanTocCha"]["comp"] == "x-select"

    # Nơi trẻ đang sống: gia đình cha mẹ nuôi, địa chỉ lấy theo cha mẹ nuôi.
    assert values["hienSongTai"] == "Gia đình của Ông/Bà"
    assert values["gdHoTen"] == "Nguyễn Thị Hoa, Trần Văn Bình"
    assert "gdGioiTinh" not in values  # hai người → không chọn được một giới tính
    assert values["gdDienthoai"] == "0900000002"
    assert values["gdNoiCuTru_TrongNuoc"]["xa"] == "Phường Hoa Lư"

    # V. (27) Nơi đăng ký việc nuôi con nuôi.
    assert values["TenCQDKNhanChaMe"] == "Ủy ban nhân dân phường Hoa Lư, tỉnh Ninh Bình"
    assert values["TenQuocGiaDK"] == "Việt Nam"


def test_driver_fields_come_before_dependent_blocks():
    names = [f["name"] for f in mapper.enrich(_couple_fields(), {})]

    assert names.index("truongHopNhanNuoi") < names.index("HoVaTenM")
    assert names.index("NoiCuTruCN") < names.index("NoiCuTruCN_TrongNuoc")
    assert names.index("hienSongTai") < names.index("gdHoTen")
    assert names.index("gdNoiCuTru") < names.index("gdNoiCuTru_TrongNuoc")


def test_single_mother_uses_own_block_and_residence_area():
    fields = [
        _field("AdoptiveMother_FullName", "Nguyễn Thị Hoa"),
        _field("AdoptiveMother_IdNumber", MOTHER_ID),
        _field("AdoptiveMother_IdIssueDate", "10/08/2021"),
        _field("AdoptiveMother_Residence", "Tổ 7, phường Hoa Lư, tỉnh Ninh Bình"),
        _field("AdoptiveMother_Relation", "dì ruột"),
        _field("Child_FullName", "Trần Minh An"),
        _field("Child_Category", "Cháu ruột"),
        _field("LivingWith_Type", "Gia đình"),
        _field("LivingWith_FullName", "Nguyễn Thị Hoa"),
    ]
    mapped = mapper.enrich(fields, {})
    values = _values(mapped)
    by_name = _by_name(mapped)

    assert values["HoVaTenC"] == "NGUYỄN THỊ HOA"
    assert values["truongHopNhanNuoi"] == "Người đơn thân nhận nuôi con nuôi"
    assert values["ChonNguoiDonThanNhanNuoi"] == "Mẹ Nuôi"
    assert values["NoiCuTruM"] == "Trong Nước"
    assert values["NoiCuTruM_TrongNuoc"] == {
        "quocGia": "Việt Nam", "tinh": "Tỉnh Ninh Bình", "xa": "Phường Hoa Lư", "diaChi": "Tổ 7",
    }
    assert "DiaChiM" not in values
    assert values["MeDoiTuong"] == "Cô, dì, bác ruột"
    assert "default" not in by_name["MeDoiTuong"]
    assert values["ncDoiTuong"] == "Cháu ruột"
    assert "default" not in by_name["ncDoiTuong"]
    assert not any(name.endswith("Cha") for name in values)
    # Trẻ sống với đúng một người là mẹ nuôi → giới tính và địa chỉ theo mẹ nuôi.
    assert values["gdGioiTinh"] == "Nữ"
    assert values["gdNoiCuTru_TrongNuoc"]["diaChi"] == "Tổ 7"


def test_child_with_own_card_fills_identity_document():
    fields = [
        _field("AdoptiveMother_FullName", "Nguyễn Thị Hoa"),
        _field("Child_FullName", "Trần Minh An"),
        _field("Child_IdNumber", CHILD_ID),
        _field("Child_IdIssueDate", "02/03/2025"),
    ]
    values = _values(mapper.enrich(fields, {}))

    assert values["LoaiGiayToDinhDanhCN"] == "Thẻ căn cước"
    assert values["SoGiayToTuyThanCN"] == CHILD_ID
    assert values["NgayCapDDCN"] == "02/03/2025"
    assert values["NoiCapDDCN"] == "Bộ Công an"


def test_facility_and_copy_request():
    fields = [
        _field("AdoptiveFather_FullName", "Trần Văn Bình"),
        _field("Child_FullName", "Trần Minh An"),
        _field("LivingWith_Type", "Cơ sở nuôi dưỡng"),
        _field("LivingWith_FacilityName", "Trung tâm bảo trợ xã hội tỉnh Ninh Bình"),
        _field("CopyRequest_WantsCopy", "Có"),
        _field("CopyRequest_Quantity", "02 bản"),
    ]
    values = _values(mapper.enrich(fields, {}))

    assert values["ChonNguoiDonThanNhanNuoi"] == "Cha Nuôi"
    assert values["hienSongTai"] == "Tại Cơ sở nuôi dưỡng"
    assert values["tenCoSoNuoiDuong"] == "Trung tâm bảo trợ xã hội tỉnh Ninh Bình"
    assert values["ncDoiTuong"] == "Trẻ em sống tại cơ sở nuôi dưỡng"
    assert values["CapBanSao"] == "Có"
    assert values["SoLuong"] == "2"


def test_empty_input_maps_nothing():
    assert mapper.enrich([], {}) == []


# ---------------------------------------------------------------- attachment planner

_APPLICATION_TEXT = (
    "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN XIN NHẬN CON NUÔI TRONG NƯỚC\n"
    "1. Phần khai về người nhận con nuôi\n"
    f"Căn cước công dân số | {FATHER_ID} | {MOTHER_ID}\n"
    "2. Phần khai về người được nhận làm con nuôi\n"
    f"Họ, chữ đệm, tên: Trần Minh An\nSố định danh cá nhân: {CHILD_ID}\n"
)

_OCR_TEXTS = {
    "don.pdf": _APPLICATION_TEXT,
    "cccd-cha-me-nuoi.pdf": (
        f"CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số / No.: {FATHER_ID}\n"
        f"CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số / No.: {MOTHER_ID}"
    ),
    "cccd-me-de.pdf": f"CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số / No.: {BIRTH_MOTHER_ID}",
    "gksk-nguoi-lon.pdf": f"GIẤY KHÁM SỨC KHỎE Số CMND/CCCD: {FATHER_ID} Lý do khám: nhận con nuôi",
    "gksk-tre.pdf": (
        "GIẤY KHÁM SỨC KHỎE (dùng cho người chưa đủ 18 tuổi) Họ và tên: TRẦN MINH AN "
        "Lý do khám sức khỏe: nhận con nuôi"
    ),
    "so-do.pdf": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT QUYỀN SỞ HỮU NHÀ Ở VÀ TÀI SẢN KHÁC GẮN LIỀN VỚI ĐẤT",
    "thu-nhap.pdf": "XÁC NHẬN THU NHẬP HÀNG THÁNG Thu nhập hàng tháng: 10.000.000 VNĐ",
    "ket-hon.pdf": (
        "GIẤY CHỨNG NHẬN KẾT HÔN Họ và tên chồng: TRẦN VĂN BÌNH Họ và tên vợ: NGUYỄN THỊ HOA\n"
        "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN Họ, chữ đệm, tên: LÒ THỊ MAI"
    ),
    "xn-tthn-me-de.pdf": (
        f"GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN Họ, chữ đệm, tên: LÒ THỊ MAI Thẻ CCCD số {BIRTH_MOTHER_ID}"
    ),
    "lltp.pdf": "PHIẾU LÝ LỊCH TƯ PHÁP SỐ 1 Họ và tên: TRẦN VĂN BÌNH",
    "khai-sinh.pdf": "GIẤY KHAI SINH Họ, chữ đệm, tên: TRẦN MINH AN Nơi đăng ký khai sinh: UBND xã Gia Viễn",
    "anh-be.pdf": "",
}


def _plan_items():
    files = [{"name": name, "type": "application/pdf"} for name in _OCR_TEXTS]
    ocr_results = [{"name": name, "text": text} for name, text in _OCR_TEXTS.items()]
    attachments, classified = planner.build_plan_items(files, ocr_results, {})
    names = list(_OCR_TEXTS)
    by_file = {}
    for item in attachments:
        for idx in item.get("sourceFileIndexes") or [item["fileIndex"]]:
            by_file[names[idx]] = item
    return attachments, classified, by_file


def test_attachment_routes_existing_rows_by_subject():
    attachments, classified, by_file = _plan_items()

    assert by_file["cccd-cha-me-nuoi.pdf"]["componentIndex"] == 1
    assert by_file["gksk-nguoi-lon.pdf"]["componentIndex"] == 2
    assert by_file["so-do.pdf"]["componentIndex"] == 3
    assert by_file["thu-nhap.pdf"] is by_file["so-do.pdf"]  # dòng 3 nhận một file gộp
    assert by_file["ket-hon.pdf"]["componentIndex"] == 4
    assert by_file["ket-hon.pdf"]["documentName"] == "Giấy chứng nhận kết hôn"
    # Mỗi dòng có sẵn chỉ một item.
    existing = [a["componentIndex"] for a in attachments if a["target"] == "existing"]
    assert sorted(existing) == [1, 2, 3, 4]


def test_attachment_application_is_eform_not_file():
    _, classified, by_file = _plan_items()

    assert "don.pdf" not in by_file
    entry = next(c for c in classified if c["fileName"] == "don.pdf")
    assert entry["target"] == "skip"


def test_attachment_child_and_birth_mother_documents_go_to_new_components():
    _, _, by_file = _plan_items()

    birth_parent = by_file["cccd-me-de.pdf"]
    assert birth_parent["target"] == "new"
    assert birth_parent["documentName"] == "Giấy tờ của cha mẹ đẻ"
    assert by_file["xn-tthn-me-de.pdf"] is birth_parent
    assert by_file["gksk-tre.pdf"]["documentName"] == "Giấy khám sức khỏe của trẻ"
    assert by_file["khai-sinh.pdf"]["documentName"] == "Giấy khai sinh của trẻ"
    assert by_file["anh-be.pdf"]["documentName"] == "Ảnh toàn thân của trẻ"
    assert by_file["lltp.pdf"]["documentName"] == "Phiếu lý lịch tư pháp"
    for name in ("gksk-tre.pdf", "khai-sinh.pdf", "anh-be.pdf", "lltp.pdf"):
        assert by_file[name]["target"] == "new"
        assert by_file[name]["needsAddComponent"] is True


def _page(number: int, total: int, text: str) -> str:
    return f"───── Trang {number}/{total} ─────\n{text}\n"


def test_attachment_splits_combined_files_by_page():
    texts = {
        "don.pdf": _APPLICATION_TEXT,
        "cccd-gop.pdf": (
            _page(1, 4, f"CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số / No.: {FATHER_ID}")
            + _page(2, 4, "Đặc điểm nhận dạng / Personal identification: sẹo chấm")
            + _page(3, 4, f"CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số / No.: {BIRTH_MOTHER_ID}")
            + _page(4, 4, "Đặc điểm nhận dạng / Personal identification: nốt ruồi")
        ),
        "gksk-gop.pdf": (
            _page(1, 4, "GIẤY KHÁM SỨC KHỎE (dùng cho người chưa đủ 18 tuổi) Họ và tên: TRẦN MINH AN")
            + _page(2, 4, "Kết quả khám thính lực ... Phân loại sức khỏe: bình thường")
            + _page(3, 4, f"GIẤY KHÁM SỨC KHỎE (dùng cho người từ đủ 18 tuổi trở lên) Số CCCD: {FATHER_ID}")
            + _page(4, 4, "Kết luận: Phân loại sức khỏe: Loại I")
        ),
        "ket-hon-gop.pdf": (
            _page(1, 2, "GIẤY CHỨNG NHẬN KẾT HÔN Họ và tên chồng: TRẦN VĂN BÌNH")
            + _page(2, 2, "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN Họ, chữ đệm, tên: LÒ THỊ MAI")
        ),
    }
    files = [{"name": name, "type": "application/pdf"} for name in texts]
    ocr_results = [{"name": name, "text": text} for name, text in texts.items()]
    attachments, _ = planner.build_plan_items(files, ocr_results, {})
    by_name = {item["documentName"]: item for item in attachments}

    assert by_name["Căn cước công dân của cha mẹ nuôi"]["componentIndex"] == 1
    assert by_name["Căn cước công dân của cha mẹ nuôi"]["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": [0, 1]}]
    assert by_name["Giấy khám sức khỏe của cha mẹ nuôi"]["sourceSegments"] == [{"fileIndex": 2, "pageIndexes": [2, 3]}]
    assert by_name["Giấy chứng nhận kết hôn"]["sourceSegments"] == [{"fileIndex": 3, "pageIndexes": [0]}]
    assert by_name["Giấy khám sức khỏe của trẻ"]["sourceSegments"] == [{"fileIndex": 2, "pageIndexes": [0, 1]}]
    # CCCD mẹ đẻ (trang 3–4) và giấy xác nhận tình trạng hôn nhân mẹ đẻ ghép chung một thành phần mới.
    assert by_name["Giấy tờ của cha mẹ đẻ"]["target"] == "new"
    assert by_name["Giấy tờ của cha mẹ đẻ"]["sourceSegments"] == [
        {"fileIndex": 1, "pageIndexes": [2, 3]},
        {"fileIndex": 3, "pageIndexes": [1]},
    ]


def test_photo_with_scribbled_initials_is_child_photo_not_llm_name():
    files = [{"name": "anh.pdf", "type": "application/pdf"}]
    attachments, classified = planner.build_plan_items(
        files, [{"name": "anh.pdf", "text": "Abcd"}], {0: {"type": "other", "documentName": "Abcd"}},
    )

    assert attachments[0]["documentName"] == "Ảnh toàn thân của trẻ"
    assert classified[0]["docType"] == "child_photo"


def test_single_adopter_marital_status_goes_to_row_4():
    texts = {
        "don.pdf": f"ĐƠN XIN NHẬN CON NUÔI TRONG NƯỚC\nCăn cước công dân số {MOTHER_ID}\n",
        "xn-tthn.pdf": f"GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN Thẻ CCCD số {MOTHER_ID}",
    }
    files = [{"name": name, "type": "application/pdf"} for name in texts]
    ocr_results = [{"name": name, "text": text} for name, text in texts.items()]
    attachments, _ = planner.build_plan_items(files, ocr_results, {})

    assert len(attachments) == 1
    assert attachments[0]["componentIndex"] == 4
    assert attachments[0]["documentName"] == "Giấy xác nhận tình trạng hôn nhân"


async def test_plan_uses_llm_only_for_unrecognised_files(monkeypatch):
    async def fake_ocr_per_file(files):
        texts = {"don.pdf": _APPLICATION_TEXT, "la.pdf": "Biên bản họp gia đình về việc nhận nuôi"}
        return [{"name": f["name"], "text": texts[f["name"]]} for f in files]

    seen = {}

    async def fake_classify(documents):
        seen["indexes"] = [doc["index"] for doc in documents]
        return {1: {"type": "other", "documentName": "Biên bản họp gia đình"}}

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)

    files = [
        FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")
        for name in ("don.pdf", "la.pdf")
    ]
    result = await planner.plan(files, {}, {"request_id": "req_test"})

    assert seen["indexes"] == [1]
    assert result["attachments"] == [{
        "fileIndex": 1,
        "fileName": "la.pdf",
        "documentName": "Biên bản họp gia đình",
        "componentName": "Biên bản họp gia đình",
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
        "detectedType": "Biên bản họp gia đình",
    }]
    assert result["errors"] == []
