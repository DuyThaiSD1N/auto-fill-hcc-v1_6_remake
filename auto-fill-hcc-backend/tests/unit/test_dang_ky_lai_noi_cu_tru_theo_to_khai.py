# -*- coding: utf-8 -*-
"""Nơi cư trú cha/mẹ phải theo TỜ KHAI, không theo CCCD.

<uu_tien_nguon> mục 1 đã quy định tờ khai là nguồn số 1 cho nơi cư trú, nhưng CCCD cũng IN
"Nơi thường trú" nên agent rất hay lấy nhầm theo thẻ — và lấy nhầm KHÔNG ĐỀU giữa hai vai
(req_e783af63a58e: cha lấy đúng tờ khai, mẹ lại lấy CCCD của chính mẹ). Hậu kiểm Python chốt lại.
"""

from app.pipelines.khai_sinh_dang_ky_lai.process import reason


def _section(residence: str, *, basis: str | None = None) -> str:
    """Khối vai như _person_from_declaration_block dựng ra từ tờ khai."""
    return "\n".join([
        "Họ tên: LÊ THỊ BÉ",
        "Số CCCD/CMND: 001160050084",
        "Ngày sinh: 1960",
        "Giới tính: Nữ",
        "Dân tộc: Kinh",
        "Quốc tịch: Việt Nam",
        f"{reason._RESIDENCE_LABEL}: {residence}",
        "Trạng thái: còn sống",
        "Nguồn: tk dang ky lai khai sinh.pdf",
        f"Căn cứ phân vai: {basis if basis is not None else reason._DECLARATION_ROLE_BASIS}",
    ])


def _mother_fields(residence: dict) -> list[dict]:
    return [
        {"name": "Mother_FullName", "comp": "x-input", "value": "LÊ THỊ BÉ"},
        {"name": "Mother_IdNumber", "comp": "x-input", "value": "001160050084"},
        {"name": "Mother_Gender", "comp": "x-select", "value": "Nữ"},
        {"name": "Mother_ResidenceDomestic", "comp": "x-select-area", "value": residence},
    ]


def _mother_residence(fields: list[dict]):
    return next(
        (f["value"] for f in fields if f["name"] == "Mother_ResidenceDomestic"),
        None,
    )


# Nơi cư trú CCCD của mẹ: xã cũ "Hoài Đức" huyện Lâm Hà, agent còn tách nhầm thôn làm xã.
_CCCD_RESIDENCE = {
    "quocGia": "Việt Nam",
    "tinh": "Lâm Đồng",
    "xa": "Thôn Đức Long",
    "diaChi": "",
}


def test_mother_residence_follows_declaration_not_id_card():
    context = "<me>\n" + _section("Tân Hà - Lâm Hà, tỉnh Lâm Đồng") + "\n</me>"

    result = reason.sanitize_extracted_fields(_mother_fields(_CCCD_RESIDENCE), context)

    assert _mother_residence(result) == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Xã Tân Hà Lâm Hà",
        "diaChi": "",
    }


def test_declaration_residence_added_when_agent_omits_the_field():
    """Agent bỏ sót hẳn ô nơi cư trú thì vẫn phải điền theo tờ khai."""
    context = "<me>\n" + _section("Tân Hà - Lâm Hà, tỉnh Lâm Đồng") + "\n</me>"
    fields = [f for f in _mother_fields(_CCCD_RESIDENCE) if f["name"] != "Mother_ResidenceDomestic"]

    result = reason.sanitize_extracted_fields(fields, context)

    assert _mother_residence(result) == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Xã Tân Hà Lâm Hà",
        "diaChi": "",
    }


def test_declaration_without_residence_leaves_extracted_value_alone():
    """Tờ khai bỏ trống ô nơi cư trú -> giữ nguyên kết quả trích xuất (CCCD là nguồn bù)."""
    context = "<me>\n" + _section("Không xác định") + "\n</me>"

    result = reason.sanitize_extracted_fields(_mother_fields(_CCCD_RESIDENCE), context)

    assert _mother_residence(result) == _CCCD_RESIDENCE


def test_role_not_built_from_declaration_is_not_overridden():
    """Khối vai suy từ nguồn khác (không phải tờ khai) thì không đủ chắc để lật kết quả."""
    context = "<me>\n" + _section(
        "Tân Hà - Lâm Hà, tỉnh Lâm Đồng",
        basis="Suy theo thế hệ từ CCCD.",
    ) + "\n</me>"

    result = reason.sanitize_extracted_fields(_mother_fields(_CCCD_RESIDENCE), context)

    assert _mother_residence(result) == _CCCD_RESIDENCE


def test_dead_parent_residence_is_left_to_the_death_branch():
    """"Nơi cư trú: Đã chết" là cách tờ khai ghi người đã mất, không phải một địa chỉ.

    KIỂM TRA 5 sẵn có đã xoá hẳn ô này; bước hậu kiểm mới không được dựng nó dậy.
    """
    context = "<me>\n" + _section("Đã chết") + "\n</me>"
    residence = {"quocGia": "", "tinh": "", "xa": "", "diaChi": "Đã chết"}

    result = reason.sanitize_extracted_fields(_mother_fields(residence), context)

    assert _mother_residence(result) is None


def test_declaration_line_that_yields_no_catalog_ward_is_ignored():
    """Tách ra một xã KHÔNG có trong danh mục -> thà giữ nguyên còn hơn điền ô chết."""
    context = "<me>\n" + _section("Xã Không Có Thật, tỉnh Lâm Đồng") + "\n</me>"

    result = reason.sanitize_extracted_fields(_mother_fields(_CCCD_RESIDENCE), context)

    assert _mother_residence(result) == _CCCD_RESIDENCE


def test_residence_line_parsing_variants():
    """Các dạng dòng "Nơi cư trú" hay gặp trên tờ khai."""
    parse = reason._residence_from_declaration_line

    # Tờ khai 2 cấp (xã – tỉnh), hậu tố cấp huyện viết kèm dấu gạch.
    assert parse("Tân Hà - Lâm Hà, tỉnh Lâm Đồng") == {
        "quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Xã Tân Hà Lâm Hà", "diaChi": "",
    }
    # Có phần chi tiết đứng trước.
    assert parse("Số nhà 29/48/3/6 đường Kim Đồng, phường Cam Ly - Đà Lạt, tỉnh Lâm Đồng") == {
        "quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường Cam Ly - Đà Lạt",
        "diaChi": "Số nhà 29/48/3/6 đường Kim Đồng",
    }
    # Tờ khai cũ 3 cấp, cấp huyện có nhãn rõ -> bỏ cụm huyện.
    assert parse("Xã Hưng Đạo, huyện Quốc Oai, TP Hà Nội") == {
        "quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Xã Hưng Đạo", "diaChi": "",
    }
    # Dạng CCCD (3 cấp, không nhãn) cũng tách đúng nhờ nhịp tra danh mục thứ hai.
    assert parse("Thôn Đức Long, Hoài Đức, Lâm Hà, Lâm Đồng") == {
        "quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Xã Tân Hà Lâm Hà",
        "diaChi": "Thôn Đức Long",
    }
    # Không đủ căn cứ.
    for line in ("", "Đã chết", "Không xác định", "Lâm Đồng"):
        assert parse(line) is None, line


def _section_with_id_card(residence: str) -> str:
    """Khối vai của hồ sơ CÓ CCCD đúng người: _stamp_identity_card đã gắn thêm 3 ô giấy tờ."""
    return _section(residence) + "\n".join([
        "",
        "Ngày cấp: 26/05/2022",
        "Nơi cấp: Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        f"{reason._ID_CARD_SOURCE_LABEL}: CCCD CHA MẸ.pdf (trang 1)",
    ])


def test_id_card_in_dossier_does_not_disable_the_declaration_residence():
    """Hồ sơ đủ 3 CCCD (con + cha + mẹ) vẫn phải lấy nơi cư trú theo tờ khai.

    Có CCCD đúng người thì khối vai được gắn thêm "Nguồn giấy tờ tùy thân" — BƯỚC 5 dùng nó để
    chốt số/ngày/nơi cấp theo thẻ. Đó là đúng phạm vi mục 6 của <uu_tien_nguon>; nơi cư trú KHÔNG
    nằm trong phạm vi đó nên vẫn theo tờ khai.
    """
    context = "<me>\n" + _section_with_id_card("Tân Hà - Lâm Hà, tỉnh Lâm Đồng") + "\n</me>"

    result = reason.sanitize_extracted_fields(_mother_fields(_CCCD_RESIDENCE), context)

    assert _mother_residence(result) == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Xã Tân Hà Lâm Hà",
        "diaChi": "",
    }


def test_role_block_built_from_id_card_keeps_the_id_card_residence():
    """Hồ sơ CHỈ có CCCD (không tờ khai): khối vai dựng từ thẻ, không có gì để ghi đè.

    _person_from_document() không sinh nhãn "Nơi cư trú" và căn cứ phân vai không phải tờ khai,
    nên bước hậu kiểm bỏ qua — CCCD vẫn là nguồn duy nhất, đúng mục 2 của <uu_tien_nguon>.
    """
    card_section = "\n".join([
        "Họ tên: LÊ THỊ BÉ",
        "Số CCCD/CMND: 001160050084",
        "Ngày sinh: 01/01/1960",
        "Giới tính: Nữ",
        "Dân tộc: Không xác định",
        "Quốc tịch: Việt Nam",
        "Trạng thái: không xác định",
        "Nguồn: CCCD CHA MẸ.pdf (trang 1)",
        "Căn cứ phân vai: Nhân thân chính đọc trực tiếp từ OCR của tài liệu.",
    ])
    assert not reason._labeled_value(card_section, reason._RESIDENCE_LABEL)
    context = "<me>\n" + card_section + "\n</me>"

    result = reason.sanitize_extracted_fields(_mother_fields(_CCCD_RESIDENCE), context)

    assert _mother_residence(result) == _CCCD_RESIDENCE
