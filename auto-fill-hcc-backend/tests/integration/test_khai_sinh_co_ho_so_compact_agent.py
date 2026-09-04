"""Mapper + registry của "Đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân" (1.004772)."""

from app.pipelines.khai_sinh_co_ho_so.process import mapper, reason
from app.pipelines.khai_sinh_co_ho_so.process.schema import ALLOWED
from app.procedures.registry import (
    get_attach_pipeline,
    get_pipeline,
    get_procedure,
)
from app.procedures.ke_khai_links import KE_KHAI_LINKS


def _by_name(fields):
    return {field["name"]: field["value"] for field in fields}


def test_registry_wires_procedure_pipelines_and_ke_khai_link():
    procedure = get_procedure("khai-sinh-da-co-ho-so")
    assert procedure["detect"]["urlIncludes"] == ["maThuTuc=1.004772"]
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert get_pipeline("khai-sinh-da-co-ho-so") is not None
    assert get_attach_pipeline("khai-sinh-da-co-ho-so") is not None

    # Key thủ tục phải trùng key trong danh mục link kê khai, nếu không popup mở link xong sẽ
    # không nhận diện được thủ tục để chạy pipeline điền tự động.
    link = next(item for item in KE_KHAI_LINKS if item["key"] == "khai-sinh-da-co-ho-so")
    assert link["code"] == "1.004772"


def test_schema_has_no_previous_registration_fields():
    """Người được khai sinh CHƯA TỪNG đăng ký khai sinh → không có khối "đăng ký trước đây"."""
    assert not any(name.startswith("PreviousRegistration_") for name in ALLOWED)
    assert "Subject_BirthDateInWords" in ALLOWED


def test_structural_defaults_use_loai_dang_ky_label():
    fields = mapper.enrich([{"name": "Subject_FullName", "value": "SÙNG A TỦA"}])
    values = _by_name(fields)
    assert values["LoaiDangKy"] == "Đăng ký cho người đã có hồ sơ, giấy tờ cá nhân"
    assert values["nksLoaiKhaiSinh"] == "Đã xác định được cả cha lẫn mẹ"
    # Ô "Loại đăng ký" là radio: gửi nhãn để fill-legacy khớp theo text, không đoán thứ tự option.
    assert fields[0]["comp"] == "x-radio"


def test_never_emits_previous_registration_ui_fields():
    fields = mapper.enrich([
        {"name": "Subject_FullName", "value": "SÙNG A TỦA"},
        # Kể cả khi agent lỡ trả field ngoài schema, mapper không được dựng khối đăng ký trước đây.
        {"name": "PreviousRegistration_Number", "value": "12"},
        {"name": "PreviousRegistration_Date", "value": "01/01/1990"},
    ])
    values = _by_name(fields)
    for name in ("soDKTruocDay", "quyenSoDKTruocDay", "ngayDKTruocDay", "coQuanDKTruocDay_filter"):
        assert name not in values


def test_self_requester_ticks_ban_than_and_fills_block_from_own_cccd():
    """Ca phổ biến nhất của thủ tục: người đã trưởng thành tự đi làm khai sinh cho chính mình.

    Ô "(5) Quan hệ với người được khai sinh" có đủ bốn lựa chọn Bản Thân / Cha / Mẹ / Khác, nên
    phải tick "BanThan" — tick "Khác" là khai sai quan hệ với cơ quan hộ tịch.
    """
    fields = mapper.enrich([
        {"name": "Requester_RelationToSubject", "value": "Bản thân"},
        {"name": "Requester_FullName", "value": "SÙNG A TỦA"},
        {"name": "Requester_SourceDocumentTitle", "value": "TỜ KHAI ĐĂNG KÝ KHAI SINH"},
        {"name": "Subject_FullName", "value": "SÙNG A TỦA"},
        {"name": "Subject_BirthDate", "value": "09/11/1973"},
        {"name": "Subject_Gender", "value": "Nam"},
        {"name": "Subject_IdNumber", "value": "062073000123"},
        {"name": "Subject_IdIssueDate", "value": "03/12/2021"},
        {"name": "Subject_IdIssuePlace", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    ])
    values = _by_name(fields)

    assert values["QuanHe"] == "BanThan"
    assert values["HoVaTenC"] == "SÙNG A TỦA"
    assert values["SoDinhDanhC"] == "062073000123"
    assert values["SoGiayToDinhDanhC"] == "062073000123"
    assert values["LoaiGiayToDinhDanhC"] == "Căn cước công dân"
    assert values["NgayCapDDC"] == "03/12/2021"
    assert values["HoTenKS"] == "SÙNG A TỦA"
    assert values["NgaySinhChon"] == "09/11/1973"
    assert values["GioiTinhKS"] == "Nam"

    # Ô tích quan hệ phải được phát TRƯỚC khối nhân thân: eForm dựng lại cả khối mỗi lần đổi ô tích.
    names = [field["name"] for field in fields]
    assert names.index("QuanHe") < names.index("HoVaTenC")


def test_father_requester_keeps_cha_de_tick():
    fields = mapper.enrich([
        {"name": "Requester_RelationToSubject", "value": "Cha"},
        {"name": "Requester_FullName", "value": "SÙNG A XANG"},
        {"name": "Subject_FullName", "value": "SÙNG A TỦA"},
        {"name": "Father_FullName", "value": "SÙNG A XANG"},
        {"name": "Father_Gender", "value": "Nam"},
        {"name": "Father_IdNumber", "value": "062052000456"},
    ])
    values = _by_name(fields)
    assert values["QuanHe"] == "ChaDe"
    assert values["HoTenChaKS"] == "SÙNG A XANG"


def test_birth_date_in_words_goes_to_bang_chu_field():
    fields = mapper.enrich([
        {"name": "Subject_FullName", "value": "SÙNG A TỦA"},
        {"name": "Subject_BirthDate", "value": "09/11/1973"},
        {
            "name": "Subject_BirthDateInWords",
            "value": "Mùng chín tháng mười một năm một nghìn chín trăm bảy mươi ba",
        },
    ])
    values = _by_name(fields)
    assert values["NgaySinhChonBangChu"] == (
        "Mùng chín tháng mười một năm một nghìn chín trăm bảy mươi ba"
    )


def test_year_only_parents_and_deceased_father():
    """Ca mẫu của thủ tục: tờ khai chỉ ghi NĂM sinh cha/mẹ, cha đã mất nên không có CCCD."""
    fields = mapper.enrich([
        {"name": "Subject_FullName", "value": "SÙNG A TỦA"},
        {"name": "Mother_FullName", "value": "HẦU THỊ SÁU"},
        {"name": "Mother_Gender", "value": "Nữ"},
        {"name": "Mother_BirthDateOrYear", "value": "1953"},
        {"name": "Mother_Ethnicity", "value": "Mông"},
        {
            "name": "Mother_ResidenceDomestic",
            "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Nùng Nàng", "diaChi": ""},
        },
        {"name": "Father_FullName", "value": "SÙNG A XANG"},
        {"name": "Father_Gender", "value": "Nam"},
        {"name": "Father_BirthDateOrYear", "value": "1952"},
        {
            "name": "Father_ResidenceDomestic",
            "value": {"quocGia": "", "tinh": "", "xa": "", "diaChi": "Đã chết"},
        },
    ])
    values = _by_name(fields)

    assert values["NamSinhMeKS"] == "1953"
    assert values["NamSinhChaKS"] == "1952"
    assert values["DanTocMeKS"] == "Mông"
    assert values["MeNoiCuTru"] == "1"
    # Xã cũ được remap theo sắp xếp đơn vị hành chính 2025 (Nùng Nàng, Tam Đường → Lai Châu).
    assert values["MeNoiCuTru_TrongNuoc"]["tinh"] == "Lai Châu"
    assert values["MeNoiCuTru_TrongNuoc"]["xa"]
    # Cha đã mất: nhánh "Trong nước" chỉ có dropdown → phải tick "Khác" rồi gõ chữ vào ô tự do.
    assert values["ChaNoiCuTru"] == "Khác"
    assert values["ChaNoiCuTru_NuocNgoai"] == "Đã chết"
    assert "ChaLoaiCuTru" not in values


def test_reasoning_context_tag_is_shared_between_reason_and_mapper():
    """reason.py đổi tên khối <to_khai_dang_ky_khai_sinh> thì mapper phải đọc đúng tên đó.

    Hai module ghép với nhau bằng CHUỖI tên khối; lệch tên không gây lỗi import mà chỉ âm thầm làm
    mapper tưởng hồ sơ không có tờ khai rồi bỏ trống cả khối người yêu cầu.
    """
    context = "\n".join([
        "<phan_vai_da_xac_dinh>",
        "<cha>",
        "Họ tên: SÙNG A XANG",
        "Trạng thái: đã chết",
        "</cha>",
        "<to_khai_dang_ky_khai_sinh>",
        "Có tờ khai đăng ký khai sinh: Có",
        "</to_khai_dang_ky_khai_sinh>",
        "</phan_vai_da_xac_dinh>",
    ])
    assert mapper._has_declaration({}, context) is True

    values = _by_name(mapper.enrich(
        [
            {"name": "Subject_FullName", "value": "SÙNG A TỦA"},
            {"name": "Father_FullName", "value": "SÙNG A XANG"},
            {"name": "Father_BirthDateOrYear", "value": "1952"},
        ],
        {"_reasoning_context": context},
    ))
    # Cha đã chết đọc từ context (tờ khai không ghi địa chỉ) → vẫn phải tick "Khác" + ghi "Đã chết".
    assert values["ChaNoiCuTru"] == "Khác"
    assert values["ChaNoiCuTru_NuocNgoai"] == "Đã chết"


def _context(con_id: str, con_name: str = "Giàng Thị Sai") -> str:
    return "\n".join([
        "<phan_vai_da_xac_dinh>",
        "<con>",
        f"Họ tên: {con_name}",
        f"Số CCCD/CMND: {con_id}",
        "Ngày sinh: 23/6/1998",
        "Giới tính: Nữ",
        "Trạng thái: còn sống",
        "</con>",
        "<me>",
        "Họ tên: Không xác định",
        "</me>",
        "<cha>",
        "Họ tên: Không xác định",
        "</cha>",
        "</phan_vai_da_xac_dinh>",
    ])


_SUBJECT_FIELDS = [
    {"name": "Subject_FullName", "value": "Giàng Thị Sai"},
    {"name": "Subject_BirthDate", "value": "23/06/1998"},
    {"name": "Subject_Gender", "value": "Nữ"},
    # Số đọc từ THẺ CCCD; số trong khối phân vai đọc từ tờ khai viết tay.
    {"name": "Subject_IdNumber", "value": "012198007016"},
]


def test_subject_block_survives_ocr_typo_in_declaration_id():
    """Ca thật: tờ khai viết tay ghi 012198001016, thẻ ghi 012198007016 — lệch đúng 1 chữ số.

    Trước đây phép so số định danh tuyệt đối làm rơi CẢ 12 field Subject_*, khối "người được đăng ký
    khai sinh" trên cổng trắng trơn dù hồ sơ có đủ giấy tờ (18/26 trường then chốt).
    """
    context = _context("012198001016")
    assert reason._identity_matches(
        {f["name"]: f["value"] for f in _SUBJECT_FIELDS}, context, "con"
    ) is True

    kept = reason.sanitize_extracted_fields(list(_SUBJECT_FIELDS), context)
    assert {f["name"] for f in kept} == {f["name"] for f in _SUBJECT_FIELDS}

    values = _by_name(mapper.enrich(kept, {"_reasoning_context": context}))
    assert values["HoTenKS"] == "Giàng Thị Sai"
    assert values["NgaySinhChon"] == "23/06/1998"
    assert values["GioiTinhKS"] == "Nữ"


def test_role_still_dropped_when_id_and_name_both_differ():
    """Nới lỏng phép so số KHÔNG được làm mất lớp chặn gán nhầm người."""
    context = _context("012198001016", con_name="Thào A Phong")
    assert reason._identity_matches(
        {f["name"]: f["value"] for f in _SUBJECT_FIELDS}, context, "con"
    ) is False

    kept = reason.sanitize_extracted_fields(list(_SUBJECT_FIELDS), context)
    assert not any(f["name"].startswith("Subject_") for f in kept)


def test_nationality_written_into_ethnicity_slot_is_not_filled():
    """Tờ khai hay ghi nhầm "Dân tộc: Việt Nam" — dropdown không có option đó."""
    values = _by_name(mapper.enrich([
        {"name": "Subject_FullName", "value": "Giàng Thị Sai"},
        {"name": "Subject_Ethnicity", "value": "Việt Nam"},
        {"name": "Mother_FullName", "value": "Thào Trí Ca"},
        {"name": "Mother_Ethnicity", "value": "mông"},
    ]))
    assert "DanTocKS" not in values
    assert values["DanTocMeKS"] == "Mông"


def test_copy_request_only_from_birth_declaration():
    fields = mapper.enrich([
        {"name": "Subject_FullName", "value": "SÙNG A TỦA"},
        {"name": "CopyRequest_SourceDocumentTitle", "value": "TỜ KHAI ĐĂNG KÝ KHAI SINH"},
        {"name": "CopyRequest_WantsCopy", "value": "Có"},
        {"name": "CopyRequest_Quantity", "value": "2"},
    ])
    values = _by_name(fields)
    assert values["CapBanSao"] == "Có"
    assert values["SoLuong"] == "2"

    ignored = _by_name(mapper.enrich([
        {"name": "Subject_FullName", "value": "SÙNG A TỦA"},
        {"name": "CopyRequest_SourceDocumentTitle", "value": "TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH"},
        {"name": "CopyRequest_WantsCopy", "value": "Có"},
    ]))
    assert "CapBanSao" not in ignored
