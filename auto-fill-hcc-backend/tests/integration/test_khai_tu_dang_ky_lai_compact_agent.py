"""Compact agent đăng ký lại khai tử: OCR text -> source facts -> legacy UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.khai_tu_dang_ky_lai import process as agent
from app.pipelines.khai_tu_dang_ky_lai.process import mapper
from app.pipelines.khai_tu_dang_ky_lai.process.prompt import EXTRA_RULES
from app.pipelines.khai_tu_dang_ky_lai.process.schema import FIELDS
from app.procedures.registry import get_pipeline, get_procedure


def _file(name, typ="application/pdf"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


@respx.mock
async def test_khai_tu_dang_ky_lai_derives_ui_fields(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")

    async def fake_ocr_per_file(files):
        return [
            {
                "name": f.get("name"),
                "type": f.get("type"),
                "text": "OCR text",
                "provider": "tiengnoi",
            }
            for f in files
        ]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Requester_FullName": "CHẨU VẦN MINH",
            "Requester_IdNumber": "012097004596",
            "Requester_IdIssueDate": "07/08/2023",
            "Requester_IdIssuePlace": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Requester_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Phường Tân Phong",
                "diaChi": "Tổ dân phố Tân Phú Nhiêu",
            },
            "Requester_Relationship": "Con trai",
            "Deceased_FullName": "CHẨU A PÓC",
            "Deceased_BirthDate": "08/07/1966",
            "Deceased_Gender": "Nam",
            "Deceased_Ethnicity": "Dao",
            "Deceased_Nationality": "Việt Nam",
            "Deceased_IdNumber": "012066002534",
            "Deceased_IdIssueDate": "04/05/2023",
            "Deceased_IdIssuePlace": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Deceased_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Tân Phong",
                "diaChi": "Tổ dân phố Tân Phú Nhiêu",
            },
            "Deceased_DeathDate": "03/08/2024",
            "Deceased_DeathTime": "09 giờ 40 phút",
            "Deceased_DeathPlaceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Tân Phong",
                "diaChi": "Tổ dân phố Tân Phú Nhiêu tại nhà",
            },
            "Deceased_DeathCause": "Ốm chết",
            "CopyRequest_WantsCopy": "Có",
            "CopyRequest_Quantity": "01",
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
        {"doc": [_file("to khai dang ky lai khai tu.pdf"), _file("cccd hai nguoi.pdf")]},
        {"formContext": {"applicantFullname": "NGƯỜI ĐĂNG NHẬP", "applicantIdentityNumber": "000000000000"}},
    )
    by_name = {f["name"]: f for f in res["fields"]}
    d = {name: f["value"] for name, f in by_name.items()}

    assert d["loaiDangKy"] == "2"
    assert d["HoVaTenC"] == "CHẨU VẦN MINH"
    assert d["SoDinhDanhC"] == "012097004596"
    assert d["SoGiayToDinhDanhC"] == "012097004596"
    assert d["LoaiGiayToDinhDanhC"] == "Thẻ căn cước công dân"
    assert d["NgayCapDDC"] == "07/08/2023"
    assert d["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["nycLoaiCuTru"] == "Thường trú"
    assert d["nycNoiCuTru"] == "1"
    assert d["nycNoiCuTru_TrongNuoc"]["tinh"] == "Lai Châu"
    assert d["nycNoiCuTru_TrongNuoc"]["xa"] == "Tân Phong"
    assert d["QuanHe"] == "Con trai"

    assert d["HoTen"] == "CHẨU A PÓC"
    assert d["NgaySinh"] == "08/07/1966"
    assert d["GioiTinh"] == "Nam"
    assert d["nktDanToc"] == "Dao"
    assert d["nktQuocTich"] == "Việt Nam"
    assert d["SoDinhDanh"] == "012066002534"
    assert d["SoGiayToDinhDanh"] == "012066002534"
    assert d["LoaiGiayToDinhDanh"] == "Thẻ căn cước công dân"
    assert d["NgayCapDD"] == "04/05/2023"
    assert d["NoiCapDD"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["nktLoaiCuTru"] == "Thường trú"
    assert d["nktNoiCuTru"] == "1"
    assert d["nktNoiCuTru_TrongNuoc"]["diaChi"] == "Tổ dân phố Tân Phú Nhiêu"

    assert d["NgayMat"] == "03/08/2024"
    assert d["GioMat"] == "09"
    assert d["PhutMat"] == "40"
    assert by_name["GioMat"]["comp"] == "raw"
    assert by_name["PhutMat"]["comp"] == "raw"
    assert d["nktNoiChet"] == "1"
    assert d["nktNoiChet_TrongNuoc"]["diaChi"] == "Tổ dân phố Tân Phú Nhiêu tại nhà"
    assert d["NguyenNhanMat"] == "Ốm chết"
    assert d["CapBanSao"] == "Có"
    assert d["SoLuong"] == "01"

    assert "coQuanDKTruocDay" not in d
    assert "soDKTruocDay" not in d
    assert not res["errors"]


@respx.mock
async def test_khai_tu_dang_ky_lai_corrects_multi_cccd_back_side_pairing(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    ocr_text = """
TỜ KHAI ĐĂNG KÝ KHAI TỬ
Họ, chữ đệm, tên người yêu cầu: Châu Văn Minh
Nơi cư trú: Tổ dân phố Tân phú nhiều, phường Tân phong, tỉnh Lai Châu
CCCD 012097004596
Quan hệ với người đã chết: Con trai
Họ, chữ đệm, tên: Châu A Páo
Ngày, tháng, năm sinh: 08/07/1966
Giới tính: Nam, Dân tộc: Dao, Quốc tịch: Việt Nam
CCCD 012066002534
Đã chết vào lúc: 09 giờ 40 phút, ngày 03 tháng 08 năm 2024
---
CĂN CƯỚC CÔNG DÂN
Số / No.: 012066002534
Họ và tên / Full name:
CHÂU A PÓC
Ngày sinh / Date of birth: 08/07/1966
Giới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam
Nơi thường trú / Place of residence: Tẩn Phủ Nhiêu
Bản Giang, Tam Đường, Lai Châu

CĂN CƯỚC CÔNG DÂN
Số / No.: 012097004596
Họ và tên / Full name:
CHÂU VĂN MINH
Ngày sinh / Date of birth: 02/02/1997
Giới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam
Nơi thường trú / Place of residence: Tẩn Phủ Nhiêu
Bản Giang, Tam Đường, Lai Châu

Đặc điểm nhận dạng / Personal identification:
Ngày, tháng, năm / Date, month, year: 04/05/2023
CỤC TRƯỞNG CỤC CẢNH SÁT
QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI
IDVNM0660025344012066002534<<9
6607087M2607089VNM<<<<<<<<<<<<4
CHAU<<A<POC<<<<<<<<<<<<<<<<<<<

Đặc điểm nhận dạng / Personal identification:
Ngày, tháng, năm / Date, month, year: 07/08/2023
CỤC TRƯỞNG CỤC CẢNH SÁT
QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI
IDVNM0970045966012097004596<<1
9702020M3702028VNM<<<<<<<<<<<<4
CHAU<<VAN<MINH<<<<<<<<<<<<<<<<
"""

    async def fake_ocr_per_file(files):
        return [
            {"name": f.get("name"), "type": f.get("type"), "text": ocr_text, "provider": "tiengnoi"}
            for f in files
        ]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Requester_FullName": "Châu Văn Minh",
            "Requester_IdNumber": "012097004596",
            # Sai như log thực tế: ngày cấp này thuộc CCCD người chết.
            "Requester_IdIssueDate": "04/05/2023",
            "Requester_IdIssuePlace": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Requester_Relationship": "Con trai",
            "Deceased_FullName": "Châu A Páo",
            "Deceased_BirthDate": "08/07/1966",
            "Deceased_Gender": "Nam",
            "Deceased_Ethnicity": "Dao",
            "Deceased_Nationality": "Việt Nam",
            "Deceased_IdNumber": "012066002534",
            "Deceased_DeathDate": "03/08/2024",
            "Deceased_DeathTime": "09:40",
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

    res = await agent.run({"doc": [_file("1_To khai.pdf"), _file("2_Giay to.pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["HoVaTenC"] == "CHÂU VĂN MINH"
    assert d["NgayCapDDC"] == "07/08/2023"
    assert d["HoTen"] == "CHÂU A PÓC"
    assert d["NgayCapDD"] == "04/05/2023"
    assert d["NoiCapDD"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["GioMat"] == "09"
    assert d["PhutMat"] == "40"


def test_khai_tu_dang_ky_lai_maps_previous_registration_only_when_present():
    fields = [
        {"name": "PreviousDeathRegistration_AgencyProvince", "comp": "x-input", "value": "Lai Châu"},
        {"name": "PreviousDeathRegistration_AgencyCommune", "comp": "x-input", "value": "UBND phường Tân Phong"},
        {"name": "PreviousDeathRegistration_Number", "comp": "x-input", "value": "15"},
        {"name": "PreviousDeathRegistration_BookNumber", "comp": "x-input", "value": "01"},
        {"name": "PreviousDeathRegistration_Date", "comp": "x-date", "value": "4/12/2019"},
    ]

    d = {f["name"]: f["value"] for f in mapper.enrich(fields)}

    assert d["loaiDangKy"] == "2"
    assert d["coQuanDKTruocDay_filter"] == "Lai Châu"
    assert d["coQuanDKTruocDay"] == "UBND phường Tân Phong"
    assert d["soDKTruocDay"] == "15"
    assert d["quyenSoDKTruocDay"] == "01"
    assert d["ngayDKTruocDay"] == "04/12/2019"


def test_khai_tu_dang_ky_lai_does_not_default_deceased_identity_issue_place_without_doc():
    fields = [
        {"name": "Deceased_FullName", "comp": "x-input", "value": "Trịnh Thị Én"},
        {"name": "Deceased_BirthDate", "comp": "x-input", "value": "1945"},
        {"name": "Deceased_Gender", "comp": "x-input", "value": "Nữ"},
        {"name": "Deceased_Ethnicity", "comp": "x-input", "value": "Kinh"},
        {"name": "Deceased_Nationality", "comp": "x-input", "value": "Việt Nam"},
        {
            "name": "Deceased_DeathPlaceDomestic",
            "comp": "x-select-area",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Đoàn Kết",
                "diaChi": "số nhà 03F đường Trần Hưng Đạo, tổ 4",
            },
        },
    ]

    d = {f["name"]: f["value"] for f in mapper.enrich(fields)}

    assert d["HoTen"] == "Trịnh Thị Én"
    assert d["NgaySinh"] == "1945"
    assert "LoaiGiayToDinhDanh" not in d
    assert "SoGiayToDinhDanh" not in d
    assert "NgayCapDD" not in d
    assert "NoiCapDD" not in d
    assert d["nktNoiChet"] == "1"
    assert d["nktNoiChet_TrongNuoc"]["xa"] == "Đoàn Kết"
    assert d["nktNoiChet_TrongNuoc"]["diaChi"] == "số nhà 03F đường Trần Hưng Đạo, tổ 4"


def test_khai_tu_dang_ky_lai_compact_prompt_instructs_role_split_and_no_guessing():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Thủ tục: Đăng ký lại khai tử" in system_prompt
    assert "Không bịa thông tin đăng ký khai tử trước đây" in system_prompt
    assert "CCCD trùng người yêu cầu → Requester_*" in system_prompt
    assert "CCCD trùng người chết → Deceased_*" in system_prompt
    assert "ghép mặt sau theo số CCCD trong dòng MRZ/IDVNM" in system_prompt
    assert "ưu tiên họ tên pháp lý" in system_prompt
    assert "trên CCCD" in system_prompt
    assert "ưu tiên địa chỉ ghi trên tờ khai" in system_prompt
    assert 'xa="Bản Giang"' in system_prompt
    assert 'diaChi="Tẩn Phủ Nhiêu"' in system_prompt
    assert 'Deceased_DeathPlaceDomestic bắt buộc lấy từ nhãn "Nơi chết"' in system_prompt
    assert "OCR có thể xuống dòng giữa tên phường/xã" in system_prompt
    assert "PreviousDeathRegistration_Number = số đăng ký khai tử trước đây" in system_prompt
    assert "không nhầm với ngày chết hoặc ngày lập tờ khai" in system_prompt
    assert "Không trả field UI/default" in system_prompt


def test_registry_uses_khai_tu_dang_ky_lai_compact_agent_mode():
    proc = get_procedure("khai-tu-dang-ky-lai")

    assert get_pipeline("khai-tu-dang-ky-lai") is agent.run
    assert proc["mode"] == "agent"
    assert proc["roles"] == []
    assert proc["useDangKyBy"] is False
    assert "maThuTuc=1.005461" in proc["detect"]["urlIncludes"]
    assert "thông tin đăng ký trước đây" in proc["uploadHint"]
