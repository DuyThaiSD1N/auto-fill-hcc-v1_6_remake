"""Compact agent trích lục khai sinh: short LLM output -> legacy x-* UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.trich_luc import process as agent
from app.pipelines.trich_luc.process import mapper, runner as trich_luc_runner
from app.pipelines.trich_luc.process.prompt import EXTRA_RULES
from app.pipelines.trich_luc.process.schema import FIELDS
from app.procedures.registry import get_pipeline


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def test_trich_luc_maps_explicit_copy_quantity_and_does_not_default_three():
    source_fields = [
        {"name": "CopyRequest_Quantity", "value": "10 bản"},
    ]

    result = {field["name"]: field for field in mapper.enrich(source_fields)}

    assert result["SoLuong"]["value"] == "10"
    assert result["SoLuong"].get("default") is not True
    assert "CapBanSao" not in result


def test_trich_luc_normalizes_noisy_copy_quantity_as_integer():
    result = {
        field["name"]: field
        for field in mapper.enrich(
            [{"name": "CopyRequest_Quantity", "value": "0,5.......bản"}]
        )
    }

    assert result["SoLuong"]["value"] == "5"


def test_trich_luc_maps_civil_status_header_number_to_form_number():
    source_fields = [
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_TenGiayTo", "value": "Giấy khai sinh"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGƯỜI ĐƯỢC KHAI SINH"},
        {"name": "HoTich_So", "value": "402/2026"},
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

    assert result["HoSo_So"] == "402/2026"


def test_trich_luc_declaration_rejects_same_person_wrong_document_type():
    source_fields = [
        # Model có thể phân loại nhầm theo file đính kèm; tên giấy ở mục (4) là mỏ neo tất định.
        {"name": "ToKhai_LoaiSuKien", "value": "death"},
        {"name": "ToKhai_TenGiayTo", "value": "Giấy khai sinh"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "Nguyễn Thành Chung"},
        {"name": "ToKhai_NgaySinh", "value": "12/12/1965"},
        {"name": "ToKhai_SoDinhDanh", "value": "023284413"},
        {"name": "ToKhai_LoaiGiayToTuyThan", "value": "CMND"},
        {"name": "ToKhai_SoGiayToTuyThan", "value": "023284413"},
        {"name": "ToKhai_NgayCapGiayToTuyThan", "value": "02/06/1999"},
        {"name": "ToKhai_NoiCapGiayToTuyThan", "value": "Công an thành phố Hà Nội"},
        {"name": "ToKhai_CoQuanDangKy", "value": "Ủy ban nhân dân phường 1, thành phố Đà Lạt, tỉnh Lâm Đồng"},
        {"name": "ToKhai_So", "value": "24"},
        {"name": "ToKhai_NgayDangKy", "value": "13/02/1956"},
        # Giấy chứng tử đúng người nhưng sai loại: tuyệt đối không được làm nguồn bổ sung.
        {"name": "HoTich_LoaiSuKien", "value": "death"},
        {"name": "HoTich_TenGiayTo", "value": "Giấy chứng tử"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN THÀNH CHUNG"},
        {"name": "HoTich_So", "value": "81"},
        {"name": "HoTich_QuyenSo", "value": "01/2013"},
        {"name": "HoTich_NgayDangKy", "value": "17/10/2013"},
        {"name": "HoTich_CoQuanDangKy", "value": "Ủy ban nhân dân Phường 14, Quận 10"},
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

    assert result["HoSo_LoaiYeuCau"].startswith("Giấy khai sinh bản sao")
    assert result["NDK_HoVaTen"] == "Nguyễn Thành Chung"
    assert "NDK_SoDinhDanh" not in result
    assert result["NDK_LoaiGiayToTuyThan"] == "Chứng minh nhân dân"
    assert result["NDK_SoGiayToTuyThan"] == "023284413"
    assert result["NDK_NgayCap"] == "02/06/1999"
    assert result["NDK_NoiCap"] == "Công an thành phố Hà Nội"
    assert result["HoSo_TenGiayTo"] == "Giấy khai sinh"
    assert result["HoSo_So"] == "24"
    assert result["HoSo_NgayCapSo"] == "13/02/1956"
    assert result["HoSo_CoQuanDangKy"].startswith("Ủy ban nhân dân phường 1")
    assert "HoSo_QuyenSo" not in result


def test_trich_luc_declaration_allows_matching_document_to_fill_blank_field():
    source_fields = [
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_TenGiayTo", "value": "Giấy khai sinh"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "TRẦN BÉ"},
        {"name": "ToKhai_SoDinhDanh", "value": "012345678901"},
        {"name": "ToKhai_LoaiGiayToTuyThan", "value": "Căn cước"},
        {"name": "ToKhai_SoGiayToTuyThan", "value": "012345678901"},
        {"name": "ToKhai_So", "value": "24"},
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_TenGiayTo", "value": "Giấy khai sinh"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "TRẦN BÉ"},
        {"name": "HoTich_So", "value": "55/2026"},
        {"name": "HoTich_QuyenSo", "value": "01/2026"},
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

    assert result["HoSo_So"] == "24"
    assert result["HoSo_QuyenSo"] == "01/2026"
    assert result["NDK_SoDinhDanh"] == "012345678901"
    assert result["NDK_SoGiayToTuyThan"] == "012345678901"


def test_trich_luc_runner_does_not_use_number_fallback():
    """Số hộ tịch phải do LLM chọn đúng nguồn, runner không được quét chéo tài liệu.

    Runner CÓ chốt chứng cứ sau LLM, nhưng nó chỉ được phép LOẠI field không có nguồn —
    tuyệt đối không thêm field mới hay sửa giá trị (đó mới là "quét chéo tài liệu").
    """
    documents = [{"name": "gks.pdf", "text": "GIẤY KHAI SINH Số: 999/2020 TRẦN BÉ"}]
    raw = {
        "HoTich_LoaiSuKien": "birth",
        "HoTich_HoTenNguoiDuocDangKy": "TRẦN BÉ",
    }

    kept = trich_luc_runner._compact_field_fallback(dict(raw), documents)

    assert kept == raw
    assert "HoTich_So" not in kept


def test_trich_luc_ignores_copy_choice_without_quantity():
    yes = {
        field["name"]: field
        for field in mapper.enrich([{"name": "CopyRequest_WantsCopy", "value": "Có"}])
    }
    no = {
        field["name"]: field
        for field in mapper.enrich([{"name": "CopyRequest_WantsCopy", "value": "Không"}])
    }

    assert "CapBanSao" not in yes
    assert "SoLuong" not in yes
    assert "CapBanSao" not in no
    assert "SoLuong" not in no


def test_trich_luc_death_extract_maps_deceased_identity_issue_details():
    source_fields = [
        {"name": "HoTich_LoaiSuKien", "value": "death"},
        {"name": "HoTich_TenGiayTo", "value": "Trích lục khai tử"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN VĂN MẪU"},
        {"name": "HoTich_SoDinhDanh", "value": "052038000054"},
        {"name": "HoTich_LoaiGiayToTuyThan", "value": "Thẻ căn cước công dân"},
        {"name": "HoTich_SoGiayToTuyThan", "value": "052038000054"},
        {"name": "HoTich_NgayCapGiayToTuyThan", "value": "27/03/2021"},
        {
            "name": "HoTich_NoiCapGiayToTuyThan",
            "value": "Cục CS QLHC về trật tự xã hội",
        },
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

    assert result["NDK_SoGiayToTuyThan"] == "052038000054"
    assert result["NDK_NgayCap"] == "27/03/2021"
    assert result["NDK_NoiCap"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert result["NDK_LoaiGiayToTuyThan"] == "Thẻ căn cước công dân"


def test_trich_luc_birth_declaration_maps_subject_identity_document():
    source_fields = [
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "ĐỖ QUỐC THÁI"},
        {"name": "HoTich_SoDinhDanh", "value": "037218005053"},
        {"name": "HoTich_LoaiGiayToTuyThan", "value": "Thẻ căn cước"},
        {"name": "HoTich_SoGiayToTuyThan", "value": "037218005053"},
        {"name": "HoTich_NgayCapGiayToTuyThan", "value": "20/06/2025"},
        {"name": "HoTich_NoiCapGiayToTuyThan", "value": "Bộ Công an"},
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

    assert result["NDK_SoDinhDanh"] == "037218005053"
    assert result["NDK_LoaiGiayToTuyThan"] == "Thẻ Căn cước"
    assert result["NDK_SoGiayToTuyThan"] == "037218005053"
    assert result["NDK_NgayCap"] == "20/06/2025"
    assert result["NDK_NoiCap"] == "Bộ Công an"


def test_trich_luc_self_request_keeps_identity_from_both_declaration_blocks():
    """Hai block trùng giấy tờ vẫn độc lập; OCR lệch tên không được làm mất giấy tờ mục II."""
    source_fields = [
        {"name": "Nyc_HoTen", "value": "LÊ NGÔ TRỌNG NGUYÊN"},
        {"name": "Nyc_SoDinhDanh", "value": "068308008269"},
        {"name": "Nyc_NgaySinh", "value": "01/04/2008"},
        {"name": "Nyc_NgayCap", "value": "26/06/2026"},
        {"name": "Nyc_NoiCap", "value": "Bộ Công an"},
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_TenGiayTo", "value": "Trích lục khai sinh"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "LÊ NỘI TRỌNG NGUYÊN"},
        {"name": "HoTich_SoDinhDanh", "value": "068308008269"},
        # Tờ khai chỉ ghi "Giấy tờ tùy thân: <số>", không ghi rõ CCCD/Căn cước.
        {"name": "HoTich_SoGiayToTuyThan", "value": "068308008269"},
        {"name": "HoTich_NgayCapGiayToTuyThan", "value": "26/06/2026"},
        {"name": "HoTich_NoiCapGiayToTuyThan", "value": "Bộ Công an"},
    ]
    options = {
        "formContext": {
            "applicantFullname": "LÊ NGÔ TRỌNG NGUYÊN",
            "applicantIdentityNumber": "068308008269",
        }
    }

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields, options)}

    assert result["SoDinhDanhC"] == "068308008269"
    assert result["NYC_SoGiayToTuyThan"] == "068308008269"
    assert result["NgayCapDDC"] == "26/06/2026"
    assert result["NoiCapDDC"] == "Bộ Công an"
    assert result["NDK_SoDinhDanh"] == "068308008269"
    assert result["NDK_LoaiGiayToTuyThan"] == "Thẻ Căn cước"
    assert result["NDK_SoGiayToTuyThan"] == "068308008269"
    assert result["NDK_NgayCap"] == "26/06/2026"
    assert result["NDK_NoiCap"] == "Bộ Công an"


def test_trich_luc_birth_certificate_with_only_personal_id_does_not_invent_id_document():
    source_fields = [
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "TRẺ CHỈ CÓ SỐ ĐỊNH DANH"},
        {"name": "HoTich_SoDinhDanh", "value": "012345678905"},
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

    assert result["NDK_SoDinhDanh"] == "012345678905"
    for name in (
        "NDK_LoaiGiayToTuyThan",
        "NDK_SoGiayToTuyThan",
        "NDK_NgayCap",
        "NDK_NoiCap",
    ):
        assert name not in result


def test_trich_luc_subject_card_identity_has_priority_over_declaration_identity():
    source_fields = [
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGƯỜI ĐƯỢC CẤP"},
        {"name": "HoTich_SoDinhDanh", "value": "012345678906"},
        {"name": "HoTich_LoaiGiayToTuyThan", "value": "Căn cước công dân"},
        {"name": "HoTich_SoGiayToTuyThan", "value": "012345678900"},
        {"name": "HoTich_NgayCapGiayToTuyThan", "value": "10/01/2021"},
        {
            "name": "HoTich_NoiCapGiayToTuyThan",
            "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        },
        {"name": "ChuThe_HoTen", "value": "NGƯỜI ĐƯỢC CẤP"},
        {"name": "ChuThe_LoaiGiayTo", "value": "Thẻ căn cước"},
        {"name": "ChuThe_SoDinhDanh", "value": "012345678906"},
        {"name": "ChuThe_NgayCap", "value": "12/08/2025"},
        {"name": "ChuThe_NoiCap", "value": "Bộ Công an"},
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

    assert result["NDK_SoDinhDanh"] == "012345678906"
    assert result["NDK_SoGiayToTuyThan"] == "012345678906"
    assert result["NDK_NgayCap"] == "12/08/2025"
    assert result["NDK_NoiCap"] == "Bộ Công an"
    assert result["NDK_LoaiGiayToTuyThan"] == "Thẻ Căn cước"


def test_trich_luc_normalizes_ho_chi_minh_province_aliases():
    aliases = (
        "TP.HCM",
        "TP HCM",
        "TP. Hồ Chí Minh",
        "TP Hồ Chí Minh",
        "TPHCM",
        "HCM",
        "Hồ Chí Minh",
        "Thành phố Hồ Chí Minh",
    )

    for alias in aliases:
        source_fields = [
            {"name": "HoTich_LoaiSuKien", "value": "birth"},
            {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGƯỜI Ở THÀNH PHỐ"},
            {
                "name": "HoTich_NoiCuTru",
                "value": {
                    "quocGia": "Việt Nam",
                    "tinh": alias,
                    "xa": "Tân Hưng",
                    "diaChi": "Khu dân cư Mẫu",
                },
            },
        ]

        result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

        assert result["NDK_NoiCuTru_TrongNuoc"]["tinh"] == "Thành phố Hồ Chí Minh"


def test_trich_luc_maps_unlisted_ethnicity_to_other_text_input():
    source_fields = [
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGƯỜI DÂN TỘC KHÁC"},
        {"name": "HoTich_DanToc", "value": "Cill"},
    ]

    result = {field["name"]: field for field in mapper.enrich(source_fields)}

    assert result["NDK_DanToc"]["comp"] == "x-select"
    assert result["NDK_DanToc"]["value"] == "Khác"
    assert result["NDK_DanTocKhac"]["comp"] == "x-select-area"
    assert result["NDK_DanTocKhac"]["value"] == "Cill"


def test_trich_luc_keeps_dropdown_ethnicity_without_other_text_input():
    source_fields = [
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGƯỜI DÂN TỘC KINH"},
        {"name": "HoTich_DanToc", "value": "Kinh"},
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

    assert result["NDK_DanToc"] == "Kinh"
    assert "NDK_DanTocKhac" not in result

    hmong_result = {
        field["name"]: field["value"]
        for field in mapper.enrich([
            {"name": "HoTich_LoaiSuKien", "value": "birth"},
            {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGƯỜI DÂN TỘC HMÔNG"},
            {"name": "HoTich_DanToc", "value": "H'Mông"},
        ])
    }
    assert hmong_result["NDK_DanToc"] == "Mông (Hmông)"
    assert "NDK_DanTocKhac" not in hmong_result


def test_trich_luc_separates_requester_cccd_from_ct01_subject():
    source_fields = [
        {"name": "Nyc_HoTen", "value": "NGUYỄN VĂN NGƯỜI YÊU CẦU"},
        {"name": "Nyc_SoDinhDanh", "value": "012345678901"},
        {"name": "Nyc_NgaySinh", "value": "10/11/1992"},
        {"name": "Nyc_NgayCap", "value": "12/08/2021"},
        {"name": "Nyc_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
        {
            "name": "Nyc_NoiCuTru",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Lâm Đồng",
                "xa": "Phường 8",
                "diaChi": "20 Đường Mẫu",
            },
        },
        {"name": "NguoiDuocCap_HoTen", "value": "NGUYỄN MINH AN"},
        {"name": "NguoiDuocCap_NgaySinh", "value": "26/05/2026"},
        {"name": "NguoiDuocCap_GioiTinh", "value": "Nam"},
    ]
    options = {
        "formContext": {
            "applicantFullname": "NGUYỄN VĂN NGƯỜI YÊU CẦU",
            "applicantIdentityNumber": "012345678901",
        }
    }

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields, options)}

    assert result["HoVaTenC"] == "NGUYỄN VĂN NGƯỜI YÊU CẦU"
    assert result["SoDinhDanhC"] == "012345678901"
    assert result["NDK_HoVaTen"] == "NGUYỄN MINH AN"
    assert result["NDK_NgaySinh"] == "26/05/2026"
    assert result["NDK_GioiTinh"] == "Nam"
    assert result["NDK_QuocTich"] == "Việt Nam"
    # CT01 chỉ chứng minh thông tin cơ bản của người con; không được chép giấy tờ/địa chỉ của cha.
    for name in (
        "NDK_SoDinhDanh",
        "NDK_LoaiGiayToTuyThan",
        "NDK_SoGiayToTuyThan",
        "NDK_NgayCap",
        "NDK_NoiCap",
        "NDK_NoiCuTru_TrongNuoc",
    ):
        assert name not in result


def test_trich_luc_single_matching_requester_is_also_subject():
    source_fields = [
        {"name": "Nyc_HoTen", "value": "TRẦN VĂN NGƯỜI YÊU CẦU"},
        {"name": "Nyc_SoDinhDanh", "value": "012345678902"},
        {"name": "Nyc_NgaySinh", "value": "01/02/1990"},
    ]
    options = {
        "formContext": {
            "applicantFullname": "TRẦN VĂN NGƯỜI YÊU CẦU",
            "applicantIdentityNumber": "012345678902",
        }
    }

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields, options)}

    assert result["HoVaTenC"] == "TRẦN VĂN NGƯỜI YÊU CẦU"
    assert result["SoDinhDanhC"] == "012345678902"
    assert result["NDK_HoVaTen"] == "TRẦN VĂN NGƯỜI YÊU CẦU"
    assert result["NDK_SoDinhDanh"] == "012345678902"


def test_trich_luc_without_requester_anchor_preserves_single_cccd_subject_fallback():
    source_fields = [
        {"name": "ChuThe_HoTen", "value": "LÊ THỊ NGƯỜI ĐƯỢC CẤP"},
        {"name": "ChuThe_SoDinhDanh", "value": "012345678903"},
        {"name": "ChuThe_NgaySinh", "value": "03/04/1985"},
        {"name": "ChuThe_GioiTinh", "value": "Nữ"},
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

    assert result["NDK_HoVaTen"] == "LÊ THỊ NGƯỜI ĐƯỢC CẤP"
    assert result["NDK_SoDinhDanh"] == "012345678903"
    assert "HoVaTenC" not in result


def test_trich_luc_cccd_mismatching_requester_anchor_is_kept_as_subject():
    source_fields = [
        {"name": "ChuThe_HoTen", "value": "PHẠM THỊ NGƯỜI ĐƯỢC CẤP"},
        {"name": "ChuThe_SoDinhDanh", "value": "012345678904"},
        {"name": "ChuThe_NgaySinh", "value": "05/06/1986"},
    ]
    options = {
        "formContext": {
            "applicantFullname": "NGƯỜI YÊU CẦU KHÁC",
            "applicantIdentityNumber": "012345678999",
        }
    }

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields, options)}

    assert result["NDK_HoVaTen"] == "PHẠM THỊ NGƯỜI ĐƯỢC CẤP"
    assert result["NDK_SoDinhDanh"] == "012345678904"
    assert "HoVaTenC" not in result


def test_trich_luc_does_not_fill_copy_fields_without_declaration():
    result = {
        field["name"]: field
        for field in mapper.enrich([{"name": "HoTich_LoaiSuKien", "value": "birth"}])
    }

    assert "CapBanSao" not in result
    assert "SoLuong" not in result


def test_trich_luc_replaces_declaration_title_with_civil_status_document_name():
    source_fields = [
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_TenGiayTo", "value": "Tờ khai đăng ký lại khai sinh"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN VĂN A"},
    ]

    result = {field["name"]: field for field in mapper.enrich(source_fields)}

    assert result["HoSo_TenGiayTo"]["value"] == "Giấy khai sinh"


def test_trich_luc_preserves_xuan_huong_ward_prefix_for_form_option():
    source_fields = [
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN VĂN A"},
        {
            "name": "HoTich_NoiCuTru",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Lâm Đồng",
                "xa": "Phường Xuân Hương",
                "diaChi": "10/4 Đường A",
            },
        },
    ]

    result = {field["name"]: field for field in mapper.enrich(source_fields)}

    assert result["NDK_NoiCuTru_TrongNuoc"]["value"]["xa"] == "Phường Xuân Hương"


@respx.mock
async def test_trich_luc_compact_agent_derives_ui_fields(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 20})
    )
    out = {
        "fields": {
            "Nyc_HoTen": "TRẦN THÀNH CÔNG",
            "Nyc_SoDinhDanh": "025203007360",
            "Nyc_NgayCap": "12/6/2021",
            "Nyc_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Nyc_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Phú Thọ",
                "diaChi": "Khu 2",
            },
            "HoTich_LoaiSuKien": "birth",
            "HoTich_TenGiayTo": "Giấy khai sinh",
            "HoTich_HoTenNguoiDuocDangKy": "VÀNG A PHỈNH",
            "HoTich_NgaySinh": "6/5/2025",
            "HoTich_GioiTinh": "Nam",
            "HoTich_DanToc": "Mông",
            "HoTich_SoDinhDanh": "012225001150",
            "HoTich_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "diaChi": "Tổ 3",
            },
            "HoTich_CoQuanDangKy": "UBND xã Lản Nhì Thàng",
            "HoTich_So": "47",
            "HoTich_QuyenSo": "01/2025",
            "HoTich_NgayDangKy": "7/5/2025",
            "HoVaTenC": "SAI_FIELD_UI",
        }
    }
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )

    res = await agent.run(
        {"doc": [_file("cccd truoc.jpg"), _file("cccd sau.jpg"), _file("gks.pdf", "application/pdf")]},
        {},
    )
    by_name = {f["name"]: f for f in res["fields"]}
    d = {name: f["value"] for name, f in by_name.items()}

    assert d["HoVaTenC"] == "TRẦN THÀNH CÔNG"
    assert by_name["HoVaTenC"]["aliases"] == ["NYC_HoVaTen"]
    assert d["SoDinhDanhC"] == "025203007360"
    assert by_name["SoDinhDanhC"]["aliases"] == ["NYC_SoDinhDanh"]
    assert d["LoaiGiayToDinhDanhC"] == "Căn cước công dân"
    assert by_name["LoaiGiayToDinhDanhC"]["aliases"] == ["NYC_LoaiGiayToTuyThan"]
    assert d["NYC_SoGiayToTuyThan"] == "025203007360"
    assert d["NgayCapDDC"] == "12/06/2021"
    assert by_name["NgayCapDDC"]["aliases"] == ["NYC_NgayCap"]
    assert d["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by_name["NoiCapDDC"]["aliases"] == ["NYC_NoiCap"]
    assert d["NYC_LoaiCuTru"] == "Thường trú"
    assert d["NYC_NoiCuTru"] == "1"
    assert d["NYC_NoiCuTru_TrongNuoc"]["tinh"] == "Phú Thọ"

    assert d["NDK_HoVaTen"] == "VÀNG A PHỈNH"
    assert d["NDK_NgaySinh"] == "06/05/2025"
    assert d["NDK_GioiTinh"] == "Nam"
    assert d["NDK_DanToc"] == "Mông"
    assert d["NDK_QuocTich"] == "Việt Nam"
    assert d["NDK_SoDinhDanh"] == "012225001150"
    assert d["NDK_LoaiCuTru"] == "Thường trú"
    assert d["NDK_NoiCuTru"] == "1"
    assert d["NDK_NoiCuTru_TrongNuoc"]["diaChi"] == "Tổ 3"

    assert d["HoSo_LoaiYeuCau"].startswith("Giấy khai sinh bản sao")
    assert d["HoSo_CoQuanDangKy"] == "UBND xã Lản Nhì Thàng"
    assert d["HoSo_TenGiayTo"] == "Giấy khai sinh"
    assert d["HoSo_So"] == "47"
    assert d["HoSo_QuyenSo"] == "01/2025"
    assert d["HoSo_NgayCapSo"] == "07/05/2025"
    assert d["PhuongThucNhanKQ"] == "2"

    assert "NYC_HoVaTen" not in d
    # Không có dòng quan hệ trên tờ khai: mapper đối chiếu người yêu cầu với người được đăng ký,
    # khác người nên tick "Khác" và đánh dấu default để cán bộ soát lại.
    assert d["NYC_QuanHe"] == "Khác"
    assert by_name["NYC_QuanHe"].get("default") is True
    assert not res["errors"]


def test_trich_luc_compact_prompt_rejects_ui_fields():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    field_names = {field["name"] for field in FIELDS}

    assert "Nyc_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND" in system_prompt
    assert "Nyc_NgayCap/Nyc_NoiCap từ mặt sau CCCD" in system_prompt
    assert "Nyc_NoiCap = \"Cục Cảnh sát quản lý hành chính về trật tự xã hội\"" in system_prompt
    assert "áp cuối = huyện và PHẢI BỎ" in system_prompt
    assert "vị trí áp cuối vẫn là cấp huyện, KHÔNG được chọn làm xa" in system_prompt
    assert 'xa="Tân Phú", tinh="Vĩnh Phúc"' in system_prompt
    assert "Nếu có đúng 2 CCCD khác nhau" in system_prompt
    assert "thẻ còn lại BẮT BUỘC vào ChuThe_*" in system_prompt
    assert not any(name.startswith("Cccd_") for name in field_names)
    assert {
        "Nyc_HoTen",
        "Nyc_SoDinhDanh",
        "Nyc_NgayCap",
        "Nyc_NoiCap",
        "ChuThe_HoTen",
        "ChuThe_SoDinhDanh",
        "ChuThe_NgaySinh",
        "ChuThe_NgayCap",
        "ChuThe_NoiCap",
        "ChuThe_NoiCuTru",
    }.issubset(field_names)
    assert 'HoTich_LoaiSuKien = "marriage"' in system_prompt
    assert "TỜ KHAI CẤP BẢN SAO chỉ sinh ToKhai_*" in system_prompt
    assert "LOẠI GIẤY ĐƯỢC YÊU CẦU, NGƯỜI ĐƯỢC CẤP" in system_prompt
    assert "khớp CẢ loại giấy được yêu cầu VÀ người được cấp" in system_prompt
    assert "đúng người nhưng sai loại" in system_prompt
    assert "Không trộn số/quyển/ngày/nơi đăng ký" in system_prompt
    assert "ToKhai_LoaiSuKien" in field_names
    assert "ToKhai_HoTenNguoiDuocCap" in field_names
    assert "ToKhai_SoDinhDanh" in field_names
    assert "ToKhai_CoQuanDangKy" in field_names
    assert "ToKhai_So" in field_names
    assert "ToKhai_NgayDangKy" in field_names
    assert 'block sau "cho người có tên dưới đây"' in system_prompt
    assert "HoTich_NoiCuTru trên TỜ KHAI CẤP BẢN SAO" in system_prompt
    assert 'không lấy dòng "Nơi cư trú" của người yêu cầu' in system_prompt
    assert "Xuống dòng không cắt block" in system_prompt
    assert "KHÔNG coi là field không chắc chắn" in system_prompt
    assert '"Thành phố Hồ Chí Minh"' in system_prompt
    assert "BẮT BUỘC trả đủ HoTich_LoaiGiayToTuyThan" in system_prompt
    assert "TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH có HAI BLOCK ĐỘC LẬP" in system_prompt
    assert "TUYỆT ĐỐI KHÔNG KHỬ TRÙNG giữa Nyc_* và HoTich_*" in system_prompt
    assert "Xác định vai trò theo VỊ TRÍ BLOCK" in system_prompt
    assert "OCR có thể đọc sai một vài ký tự trong tên" in system_prompt
    assert 'không ghi rõ chữ "CCCD"/"Căn cước"' in system_prompt
    assert "HoTich_SoDinhDanh = <12 chữ số>" in system_prompt
    assert "block 2 THỰC SỰ có dòng" in system_prompt
    assert "CopyRequest_QuanHe lấy từ TỜ KHAI" in system_prompt
    assert "CopyRequest_QuanHe" in field_names
    assert "HoSo_LoaiYeuCau" in system_prompt
    assert "PhuongThucNhanKQ" in system_prompt
    assert "CopyRequest_Quantity=10" in system_prompt
    assert "KHÔNG diễn giải thành số thập phân" in system_prompt
    assert "không trả CapBanSao" in system_prompt
    assert "CopyRequest_WantsCopy" not in field_names
    assert {
        "NguoiDuocCap_HoTen",
        "NguoiDuocCap_NgaySinh",
        "NguoiDuocCap_GioiTinh",
    }.issubset(field_names)
    assert "GIẤY CHỨNG SINH và TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ (CT01)" in system_prompt
    assert 'NguoiDuocCap_HoTen lấy ở "Dự định đặt tên con"' in system_prompt
    assert "Không lấy chủ hộ ở mục 7" in system_prompt
    assert "Không sao chép Nyc_SoDinhDanh/Nyc_NgayCap/" in system_prompt
    assert 'HoTich_So ưu tiên số trong block "Đã đăng ký tại" của TỜ KHAI' in system_prompt
    assert 'Dòng "Số: <mã>/<năm>" ở phần đầu' in system_prompt
    assert "BỎ toàn bộ NguoiDuocCap_*" in system_prompt
    assert 'không tự trả "Khác"' in system_prompt
    assert '"Số bộ 123"' in system_prompt


@respx.mock
async def test_trich_luc_compact_agent_ignores_direct_ui_values(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    # OCR phải có ĐÚNG hai người mà LLM trả về: chốt chứng cứ ở runner loại nhóm thẻ của
    # người không hề xuất hiện trong hồ sơ.
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [
            {"text": "CĂN CƯỚC CÔNG DÂN 012345678901 NGUYỄN VĂN A. GIẤY KHAI SINH TRẦN BÉ"}
        ] * 20})
    )
    out = {
        "fields": {
            "NYC_HoVaTen": "UI_SAI",
            "HoSo_LoaiYeuCau": "SAI_DEFAULT",
            "NYC_QuanHe": "Bố Đẻ",
            "Nyc_HoTen": "NGUYỄN VĂN A",
            "Nyc_SoDinhDanh": "012345678901",
            "HoTich_LoaiSuKien": "birth",
            "HoTich_HoTenNguoiDuocDangKy": "TRẦN BÉ",
            "HoTich_NgaySinh": "10/04/2022",
        }
    }
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )

    res = await agent.run({"doc": [_file("cccd.jpg"), _file("gks.pdf", "application/pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["HoVaTenC"] == "NGUYỄN VĂN A"
    assert d["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["NDK_HoVaTen"] == "TRẦN BÉ"
    assert d["HoSo_LoaiYeuCau"].startswith("Giấy khai sinh bản sao")
    # Giá trị UI do LLM trả thẳng bị bỏ; ô tích chỉ đến từ suy luận của mapper.
    assert d["NYC_QuanHe"] == "Khác"
    assert not res["errors"]


@respx.mock
async def test_trich_luc_compact_agent_maps_marriage_extract(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "GIẤY CHỨNG NHẬN KẾT HÔN"}] * 20})
    )
    out = {
        "fields": {
            "Nyc_HoTen": "TRẦN THÀNH CÔNG",
            "Nyc_SoDinhDanh": "025203007360",
            "HoTich_LoaiSuKien": "marriage",
            "HoTich_TenGiayTo": "Giấy chứng nhận kết hôn",
            "HoTich_HoTenNguoiDuocDangKy": "MÃ THỊ SỐ; SUNG A CO",
            "HoTich_NgaySinh": "01/01/1986",
            "HoTich_DanToc": "H'Mông",
            "HoTich_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Đoàn Kết",
                "diaChi": "Tổ dân phố Cư Nhà La",
            },
            "HoTich_LoaiGiayToTuyThan": "Thẻ căn cước công dân",
            "HoTich_SoGiayToTuyThan": "012086005221",
            "HoTich_NgayCapGiayToTuyThan": "06/01/2026",
            "HoTich_NoiCapGiayToTuyThan": "Bộ Công an",
            "HoTich_CoQuanDangKy": "Ủy ban nhân dân phường Đoàn Kết, tỉnh Lai Châu",
            "HoTich_So": "40/2026",
            "HoTich_NgayDangKy": "01/04/2026",
        }
    }
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )

    res = await agent.run({"doc": [_file("cccd.pdf", "application/pdf"), _file("ket-hon.jpg")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["HoSo_LoaiYeuCau"] == "Trích lục kết hôn (bản sao)/ Trích lục ghi chú kết hôn (bản sao)"
    assert d["HoSo_TenGiayTo"] == "Giấy chứng nhận kết hôn"
    assert d["HoSo_CoQuanDangKy"] == "Ủy ban nhân dân phường Đoàn Kết, tỉnh Lai Châu"
    assert d["HoSo_So"] == "40/2026"
    assert d["HoSo_NgayCapSo"] == "01/04/2026"
    assert d["PhuongThucNhanKQ"] == "2"
    assert d["NDK_HoVaTen"] == "SUNG A CO"
    assert d["NDK_NgaySinh"] == "01/01/1986"
    assert d["NDK_GioiTinh"] == "Nam"
    assert d["NDK_DanToc"] == "Mông (Hmông)"
    assert d["NDK_SoDinhDanh"] == "012086005221"
    assert d["NDK_LoaiGiayToTuyThan"] == "Căn cước công dân"
    assert d["NDK_SoGiayToTuyThan"] == "012086005221"
    assert d["NDK_NgayCap"] == "06/01/2026"
    assert d["NDK_NoiCap"] == "Bộ Công an"
    assert d["NDK_NoiCuTru"] == "1"
    assert d["NDK_NoiCuTru_TrongNuoc"]["tinh"] == "Lai Châu"
    assert d["NDK_NoiCuTru_TrongNuoc"]["xa"] == "Đoàn Kết"
    assert d["NDK_NoiCuTru_TrongNuoc"]["diaChi"] == "Tổ dân phố Cư Nhà La"
    assert "HoSo_QuyenSo" not in d
    assert not res["errors"]


def test_registry_uses_trich_luc_compact_pipeline():
    assert get_pipeline("trich-luc-ks") is agent.run
