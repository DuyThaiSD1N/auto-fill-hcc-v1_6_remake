"""Compact agent đăng ký lại khai sinh: short LLM output -> legacy UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines.khai_sinh_dang_ky_lai import process as agent
from app.pipelines.khai_sinh_dang_ky_lai.process import mapper, reason


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


async def _no_reasoning_context(*_args, **_kwargs):
    """Các test compact-agent cũ chỉ kiểm tra extraction/mapper, không kiểm tra call reasoning."""
    return ""


def test_dang_ky_lai_normalizes_all_domestic_address_fields():
    source_fields = [
        {
            "name": "Subject_BirthPlaceDomestic",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "TP. Hồ Chí Minh",
                "xa": "P. Tân Hưng",
                "diaChi": "Bệnh viện A",
            },
        },
        {
            "name": "Subject_HometownDomestic",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "TP Hồ Chí Minh",
                "xa": "P Tân Hưng",
                "diaChi": "",
            },
        },
        {
            "name": "Mother_ResidenceDomestic",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "TP. Hồ Chí Minh",
                "xa": "P. Tân Hưng",
                "diaChi": "861/27/4/3 Khu phố 4",
            },
        },
        {
            "name": "Father_ResidenceDomestic",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Lâm Đồng",
                "xa": "X. Xuân Trường",
                "diaChi": "Tổ 1",
            },
        },
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

    for name in (
        "nksNoiSinh_TrongNuoc",
        "nksQueQuan_TrongNuoc",
        "MeNoiCuTru_TrongNuoc",
    ):
        assert result[name]["tinh"] == "Thành phố Hồ Chí Minh"
        assert result[name]["xa"] == "Phường Tân Hưng"
    assert result["MeNoiCuTru_TrongNuoc"]["diaChi"] == "861/27/4/3 Khu phố 4"
    assert result["ChaNoiCuTru_TrongNuoc"]["tinh"] == "Lâm Đồng"
    # Xã Xuân Trường (Lâm Đồng) đã nhập vào Đà Lạt theo sáp nhập 2025 → nhãn xã mới trên cổng.
    assert result["ChaNoiCuTru_TrongNuoc"]["xa"] == "Phường Xuân Trường - Đà Lạt"


def test_dang_ky_lai_address_normalization_preserves_full_names_and_deceased_marker():
    source_fields = [
        {
            "name": "Subject_BirthPlaceDomestic",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Thành phố Hồ Chí Minh",
                "xa": "Phường Tân Hưng",
                "diaChi": "",
            },
        },
        {
            "name": "Mother_ResidenceDomestic",
            "value": {
                "quocGia": "",
                "tinh": "",
                "xa": "",
                "diaChi": "Đã chết",
            },
        },
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

    assert result["nksNoiSinh_TrongNuoc"] == source_fields[0]["value"]
    # Mẹ đã chết: nhánh "Trong nước" chỉ có dropdown → tick "Khác" và ghi chữ vào ô tự do.
    assert result["MeNoiCuTru"] == "Khác"
    assert result["MeNoiCuTru_NuocNgoai"] == "Đã chết"
    assert "MeNoiCuTru_TrongNuoc" not in result


def test_dang_ky_lai_does_not_default_book_number_or_copies():
    source_fields = [
        {"name": "PreviousRegistration_Number", "value": "245/1995"},
        {"name": "PreviousRegistration_Date", "value": "11/09/1995"},
    ]

    result = {field["name"]: field for field in mapper.enrich(source_fields)}

    assert result["soDKTruocDay"]["value"] == "245/1995"
    assert result["ngayDKTruocDay"]["value"] == "11/09/1995"
    assert "quyenSoDKTruocDay" not in result
    assert "CapBanSao" not in result
    assert "SoLuong" not in result


def test_dang_ky_lai_maps_explicit_book_number_and_copy_request_without_defaults():
    source_fields = [
        {"name": "PreviousRegistration_BookNumber", "value": "01/15"},
        {
            "name": "CopyRequest_SourceDocumentTitle",
            "value": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH",
        },
        {"name": "CopyRequest_WantsCopy", "value": "Có"},
        {"name": "CopyRequest_Quantity", "value": "10 bản"},
    ]

    result = {field["name"]: field for field in mapper.enrich(source_fields)}

    assert result["quyenSoDKTruocDay"]["value"] == "01/15"
    assert result["CapBanSao"]["value"] == "Có"
    assert result["SoLuong"]["value"] == "10"
    assert result["quyenSoDKTruocDay"].get("default") is not True
    assert result["CapBanSao"].get("default") is not True
    assert result["SoLuong"].get("default") is not True


def test_dang_ky_lai_maps_explicit_no_copy_without_quantity():
    source_fields = [
        {
            "name": "CopyRequest_SourceDocumentTitle",
            "value": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH",
        },
        {"name": "CopyRequest_WantsCopy", "value": "Không"},
        {"name": "CopyRequest_Quantity", "value": "10"},
    ]

    result = {field["name"]: field for field in mapper.enrich(source_fields)}

    assert result["CapBanSao"]["value"] == "Không"
    assert "SoLuong" not in result


def test_dang_ky_lai_rejects_copy_request_from_civil_status_extract_form():
    # Tái hiện req_daf32eb17591: số lượng nằm trên tờ khai cấp trích lục, không phải tờ khai đăng ký lại.
    source_fields = [
        {"name": "PreviousRegistration_BookNumber", "value": "01/2014"},
        {
            "name": "CopyRequest_SourceDocumentTitle",
            "value": "TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH",
        },
        {"name": "CopyRequest_WantsCopy", "value": "Có"},
        {"name": "CopyRequest_Quantity", "value": 10},
    ]

    result = {field["name"]: field for field in mapper.enrich(source_fields)}

    assert result["quyenSoDKTruocDay"]["value"] == "01/2014"
    assert "CapBanSao" not in result
    assert "SoLuong" not in result


def test_dang_ky_lai_rejects_unproven_copy_request_source():
    source_fields = [
        {"name": "CopyRequest_WantsCopy", "value": "Có"},
        {"name": "CopyRequest_Quantity", "value": 10},
    ]

    result = {field["name"]: field for field in mapper.enrich(source_fields)}

    assert "CapBanSao" not in result
    assert "SoLuong" not in result


@respx.mock
async def test_dang_ky_lai_compact_agent_derives_legacy_fields(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(reason, "build_context", _no_reasoning_context)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 20})
    )
    out = {
        "fields": {
            "Requester_RelationToSubject": "ChaDe",
            "Requester_FullName": "TRẦN THÀNH CÔNG",
            "Requester_IdNumber": "025203007360",
            "Requester_IdIssueDate": "12/06/2021",
            "Requester_IdIssuePlace": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Requester_BirthDate": "11/07/2003",
            "Requester_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Phú Thọ",
                "diaChi": "Khu 2",
            },
            "Father_FullName": "TRẦN THÀNH CÔNG",
            "Father_IdNumber": "025203007360",
            "Father_IdIssueDate": "12/06/2021",
            "Father_IdIssuePlace": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Father_BirthDateOrYear": "11/07/2003",
            "Father_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Phú Thọ",
                "diaChi": "Khu 2",
            },
            "Mother_FullName": "PHẠM NGỌC THỦY",
            "Mother_IdNumber": "012193000851",
            "Mother_IdIssueDate": "06/02/2024",
            "Mother_IdIssuePlace": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Subject_FullName": "Vàng A Phỉnh",
            "Subject_BirthDate": "6/5/2025",
            "Subject_Gender": "Nam",
            "Subject_Ethnicity": "Mông",
            "Subject_BirthPlaceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "diaChi": "TTYT Sìn Hồ",
            },
            "PreviousRegistration_AgencyProvince": "Lai Châu",
            "PreviousRegistration_Number": "47",
            "PreviousRegistration_Date": "7/5/2025",
            "FieldLa": "x",
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
        {"doc": [_file("cha.jpg"), _file("me.jpg"), _file("gks.pdf", "application/pdf")]}, {}
    )
    names = [f["name"] for f in res["fields"]]
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert names[:2] == ["LoaiDangKy", "nksLoaiKhaiSinh"]
    assert d["LoaiDangKy"] == "2"
    assert d["nksLoaiKhaiSinh"] == "Đã xác định được cả cha lẫn mẹ"
    assert d["QuanHe"] == "ChaDe"

    # Người yêu cầu là vai trò do agent suy luận, không mặc định theo giới tính.
    assert d["HoVaTenC"] == "TRẦN THÀNH CÔNG"
    assert d["SoDinhDanhC"] == "025203007360"
    assert d["SoGiayToDinhDanhC"] == "025203007360"
    assert d["NgayCapDDC"] == "12/06/2021"
    assert d["nycNoiCuTru"] == "1"
    assert d["nycNoiCuTru_TrongNuoc"]["tinh"] == "Phú Thọ"

    # Duplicate/default UI fields không cần LLM trả.
    assert d["HoTenChaKS"] == "TRẦN THÀNH CÔNG"
    assert d["HoTenMeKS"] == "PHẠM NGỌC THỦY"
    assert d["SoGiayToDinhDanhCha"] == "025203007360"
    assert d["SoGiayToDinhDanhMe"] == "012193000851"
    assert d["LoaiGiayToDinhDanhCha"] == "Căn cước công dân"
    assert d["NoiCapDDCha"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["NoiCapDDMe"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["ChaLoaiCuTru"] == "Thường trú"
    assert d["QuocTichChaKS"] == "Việt Nam"
    assert "DanTocChaKS" not in d

    assert d["NgaySinhChon"] == "06/05/2025"
    assert d["ngayDKTruocDay"] == "07/05/2025"
    assert d["nksNoiSinh"] == "1"
    assert d["soDKTruocDay"] == "47"
    assert "FieldLa" not in d
    assert not res["errors"]


@respx.mock
async def test_dang_ky_lai_compact_agent_defaults_cccd_issuer(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(reason, "build_context", _no_reasoning_context)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 20})
    )
    out = {
        "fields": {
            "Requester_RelationToSubject": "ChaDe",
            "Requester_FullName": "VŨ ĐÌNH THIẾT",
            "Requester_IdNumber": "040203015844",
            "Requester_IdIssueDate": "02/07/2021",
            "Father_FullName": "VŨ ĐÌNH THIẾT",
            "Father_IdNumber": "040203015844",
            "Father_IdIssueDate": "02/07/2021",
            "Father_BirthDateOrYear": "26/04/2003",
            "Mother_FullName": "PHẠM NGỌC THỦY",
            "Mother_IdNumber": "012193000851",
            "Mother_IdIssueDate": "06/02/2024",
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

    res = await agent.run({"doc": [_file("cha.jpg"), _file("me.jpg")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    issuer = "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["NoiCapDDC"] == issuer
    assert d["NoiCapDDCha"] == issuer
    assert d["NoiCapDDMe"] == issuer


@respx.mock
async def test_dang_ky_lai_compact_agent_rejects_legacy_ui_keys(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(reason, "build_context", _no_reasoning_context)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 20})
    )
    out = {
        "fields": {
            # Đây là kiểu sai: agent compact không được trả field UI trực tiếp.
            "HoTenChaKS": "VÀNG A THA",
            "SoDinhDanhCha": "0122019232",
            "HoTenMeKS": "LÝ THỊ LIA",
            "SoDinhDanhMe": "012193000851",
            "HoTenKS": "VÀNG A PHỈNH",
            "NgaySinhChon": "06/05/2025",
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

    res = await agent.run({"doc": [_file("cha.jpg"), _file("me.jpg"), _file("gks.pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert "HoTenChaKS" not in d
    assert "SoDinhDanhCha" not in d
    assert "HoVaTenC" not in d
    assert "HoTenMeKS" not in d
    assert "SoDinhDanhMe" not in d
    assert "HoTenKS" not in d
    assert "NgaySinhChon" not in d
    assert d["LoaiDangKy"] == "2"
    assert not res["errors"]


@respx.mock
async def test_dang_ky_lai_compact_agent_maps_self_requester_from_paper_declaration(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(reason, "build_context", _no_reasoning_context)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 20})
    )
    out = {
        "fields": {
            "Requester_RelationToSubject": "BanThan",
            "Requester_FullName": "NGUYỄN THỊ HOÀI MINH",
            "Requester_IdNumber": "012176000644",
            "Requester_IdIssueDate": "25/04/2021",
            "Requester_IdIssuePlace": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Requester_BirthDate": "17/11/1976",
            "Requester_Gender": "Nữ",
            "Requester_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "diaChi": "Tổ 2",
            },
            "Subject_FullName": "NGUYỄN THỊ HOÀI MINH",
            "Subject_BirthDate": "17/11/1976",
            "Subject_Gender": "Nữ",
            "Subject_Ethnicity": "Kinh",
            "Subject_Nationality": "Việt Nam",
            "Subject_HometownDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Hà Nam",
                "diaChi": "Trác Văn",
            },
            "Father_FullName": "NGUYỄN ĐỨC NGUYÊN",
            "Father_BirthDateOrYear": "1920",
            "Father_Ethnicity": "Kinh",
            "Father_Nationality": "Việt Nam",
            "Father_ResidenceDomestic": {
                "quocGia": "",
                "tinh": "",
                "xa": "",
                "diaChi": "Đã chết",
            },
            "Mother_FullName": "NGUYỄN THỊ THÔNG",
            "Mother_BirthDateOrYear": "1932",
            "Mother_Ethnicity": "Kinh",
            "Mother_Nationality": "Việt Nam",
            "Mother_ResidenceDomestic": {
                "quocGia": "",
                "tinh": "",
                "xa": "",
                "diaChi": "Đã chết",
            },
            "PreviousRegistration_AgencyProvince": "Lai Châu",
            "PreviousRegistration_Number": "7",
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
        {"doc": [_file("cccd.pdf", "application/pdf"), _file("to-khai.pdf", "application/pdf")]},
        {},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["QuanHe"] == "BanThan"
    assert d["HoVaTenC"] == "NGUYỄN THỊ HOÀI MINH"
    assert d["SoDinhDanhC"] == "012176000644"
    assert d["NgayCapDDC"] == "25/04/2021"
    assert d["nycNoiCuTru_TrongNuoc"]["tinh"] == "Lai Châu"
    assert d["HoTenKS"] == "NGUYỄN THỊ HOÀI MINH"
    assert d["NgaySinhChon"] == "17/11/1976"
    assert d["GioiTinhKS"] == "Nữ"
    assert d["DanTocKS"] == "Kinh"
    assert d["nksQueQuan"] == "1"
    # Hà Nam đã nhập vào Ninh Bình theo sáp nhập 2025.
    assert d["nksQueQuan_TrongNuoc"]["tinh"] == "Ninh Bình"
    assert d["HoTenChaKS"] == "NGUYỄN ĐỨC NGUYÊN"
    assert d["NamSinhChaKS"] == "1920"
    # "Đã chết" trơn (không tỉnh/xã) từ LLM chỉ được nhận khi khối reasoning chốt cha/mẹ đã chết;
    # test này tắt reasoning nên sanitizer bỏ mục nơi cư trú, không tự điền "Đã chết".
    assert "ChaNoiCuTru" not in d
    assert "ChaNoiCuTru_NuocNgoai" not in d
    assert "ChaNoiCuTru_TrongNuoc" not in d
    assert d["HoTenMeKS"] == "NGUYỄN THỊ THÔNG"
    assert d["NamSinhMeKS"] == "1932"
    assert "MeNoiCuTru" not in d
    assert "MeNoiCuTru_NuocNgoai" not in d
    assert "MeNoiCuTru_TrongNuoc" not in d
    # Không có số định danh cha/mẹ → chỉ phát lệnh xoá ô cổng điền sẵn, không điền số.
    by_name = {f["name"]: f for f in res["fields"]}
    for name in ("SoDinhDanhCha", "SoDinhDanhMe"):
        assert by_name[name]["value"] == ""
        assert by_name[name].get("clear") is True
    assert "soDKTruocDay" not in d
    assert not res["errors"]
