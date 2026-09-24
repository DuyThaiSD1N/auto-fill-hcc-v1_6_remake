"""Compact agent đăng ký lại khai sinh: short LLM output -> legacy UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.khai_sinh_dang_ky_lai import process as agent
from app.pipelines.khai_sinh_dang_ky_lai.process import mapper, reason
from app.pipelines.khai_sinh_dang_ky_lai.process.prompt import EXTRA_RULES
from app.pipelines.khai_sinh_dang_ky_lai.process.schema import FIELDS


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
    assert result["ChaNoiCuTru_TrongNuoc"]["xa"] == "Xã Xuân Trường"


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
    assert result["MeNoiCuTru_TrongNuoc"] == source_fields[1]["value"]


def test_dang_ky_lai_id_doc_type_follows_issuer_not_number_length():
    """Số 12 chữ số chưa nói được loại thẻ: thẻ Căn cước mới do Bộ Công an cấp, CCCD chip cũ do Cục."""
    source_fields = [
        {"name": "Mother_FullName", "value": "Trần Thị Mẫu"},
        {"name": "Mother_IdNumber", "value": "001155000001"},
        {"name": "Mother_IdIssueDate", "value": "08/08/2024"},
        {"name": "Mother_IdIssuePlace", "value": "Bộ Công an"},
        {"name": "Father_FullName", "value": "Lê Văn Mẫu"},
        {"name": "Father_IdNumber", "value": "001058000002"},
        {"name": "Father_IdIssueDate", "value": "12/06/2021"},
    ]
    result = {field["name"]: field["value"] for field in mapper.enrich(source_fields)}

    assert result["LoaiGiayToDinhDanhMe"] == "Thẻ Căn cước"
    # Không đọc được nơi cấp, ngày cấp trước 01/7/2024 → CCCD gắn chip cũ.
    assert result["LoaiGiayToDinhDanhCha"] == "Thẻ căn cước công dân"
    assert mapper._id_doc_type("024086001950", "Bộ Công an") == "Thẻ Căn cước"
    assert mapper._id_doc_type("121609105", "Bộ Công an") == "Chứng minh nhân dân"


def test_dang_ky_lai_prompt_requires_full_administrative_unit_names():
    assert 'luôn trả "Thành phố Hồ Chí Minh"' in EXTRA_RULES
    assert 'không trả "X.", "P.", "TT."' in EXTRA_RULES


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
    # Ngày cấp 2021, nơi cấp Cục Cảnh sát → CCCD gắn chip cũ, không phải thẻ Căn cước mới.
    assert d["LoaiGiayToDinhDanhCha"] == "Thẻ căn cước công dân"
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


def test_dang_ky_lai_compact_prompt_instructs_issuer_detection():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "<critical_rules>" in system_prompt
    assert "<output_contract>" in system_prompt
    assert "<role_assignment>" in system_prompt
    assert "<source_priority>" in system_prompt
    assert "Requester_*" in system_prompt
    assert "Subject_*" in system_prompt
    assert "Father_*" in system_prompt
    assert "Mother_*" in system_prompt
    assert "một schema duy nhất" in system_prompt
    assert "không theo giới tính giấy tờ" in system_prompt
    assert "Cục Cảnh sát quản lý hành chính về trật tự xã hội" in system_prompt
    assert "HoTenKS là field UI" in system_prompt
    assert "không trả wrapper dài" in system_prompt.lower()
    assert "Không lấy số thứ tự mục" in system_prompt
    assert "Bản cam đoan là nguồn phụ" in system_prompt
    assert "Father_ResidenceDomestic" in system_prompt
    assert "Da Chet" in system_prompt
    assert "D.d. Chat" in system_prompt
    assert "L.D.d. Chat" in system_prompt
    assert 'diaChi":"Đã chết' in system_prompt
    assert "trước nhãn \"Họ, chữ đệm, tên người cha\"" in system_prompt
    assert '"Subject_BirthDate":"17/11/1976"' in system_prompt
    assert '{"fields":{"Subject_BirthDate":"1976"}}' in system_prompt
    assert "ghi bằng chữ" in system_prompt


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
    assert d["nksQueQuan_TrongNuoc"]["tinh"] == "Hà Nam"
    assert d["HoTenChaKS"] == "NGUYỄN ĐỨC NGUYÊN"
    assert d["NamSinhChaKS"] == "1920"
    assert d["ChaNoiCuTru"] == "1"
    assert d["ChaNoiCuTru_TrongNuoc"]["diaChi"] == "Đã chết"
    assert d["ChaNoiCuTru_TrongNuoc"]["tinh"] == ""
    assert d["HoTenMeKS"] == "NGUYỄN THỊ THÔNG"
    assert d["NamSinhMeKS"] == "1932"
    assert d["MeNoiCuTru"] == "1"
    assert d["MeNoiCuTru_TrongNuoc"]["diaChi"] == "Đã chết"
    assert d["MeNoiCuTru_TrongNuoc"]["tinh"] == ""
    assert "SoDinhDanhCha" not in d
    assert "SoDinhDanhMe" not in d
    assert "soDKTruocDay" not in d
    assert not res["errors"]
