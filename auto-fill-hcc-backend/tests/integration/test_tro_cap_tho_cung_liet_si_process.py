"""Focused process tests cho trợ cấp thờ cúng liệt sĩ."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines.tro_cap_tho_cung_liet_si import process as agent


def _file(name: str):
    return {"name": name, "type": "application/pdf", "dataUrl": "data:x;base64,QUFB"}


def _mock_services(monkeypatch, output: dict):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "ocr_by_tiengnoi", False)
    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    respx.post(settings.ocr_raw_base_url.rstrip("/") + "/api/v1/ocr/raw").mock(
        return_value=httpx.Response(200, json={"fullText": "OCR TEXT"})
    )
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(output, ensure_ascii=False) + "\n```"
            }}]},
        )
    )


_OUTPUT = {
    "fields": {
        "ChuHoSo_HoTen": "Vũ Đình Tuyến",
        "ChuHoSo_NgaySinh": "08/03/1962",
        "ChuHoSo_SoDinhDanh": "034062017797",
        "ChuHoSo_NgayCap": "09/05/2021",
        "ChuHoSo_NoiCap": "Cục CSQLHC về TTXH",
        "ChuHoSo_QueQuan": {"tinh": "Hưng Yên", "xa": "Long Hưng", "diaChi": ""},
        "ChuHoSo_NoiCuTru": {
            "tinh": "Lâm Đồng",
            "xa": "Phường Lâm Viên",
            "diaChi": "2 Trương Văn Hoàn",
        },
        "ChuHoSo_DienThoai": "0982577867",
        "ToKhai_MoiQuanHeVoiLietSi": "Con trai",
        "ToKhai_LietSiThoCung": ["Vũ Đình Soang", "Vũ Đình Hải"],
        "ToKhai_ThanNhan": [
            {"hoTen": "Vũ Đình Tuyên", "namSinh": "1962", "moiQuanHe": "em trai"},
            {"hoTen": "Vũ Đình Tuyên", "namSinh": "", "moiQuanHe": "em trai"},
            {"hoTen": "Vũ Thị Duyên", "namSinh": "1965"},
            {"hoTen": "Vũ Thị Duyên", "namSinh": "1965"},
        ],
        # Field contract cũ phải bị validator loại bỏ.
        "Person1_HoTen": "Vũ Thị Duyên",
    }
}


@respx.mock
async def test_ui_mismatch_returns_owner_and_detail_only(monkeypatch):
    _mock_services(monkeypatch, _OUTPUT)

    result = await agent.run(
        {"doc": [_file("ho-so.pdf")]},
        {"formContext": {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        }},
    )
    mapped = {
        (field["name"], field.get("occurrence")): field["value"]
        for field in result["fields"]
    }

    assert mapped[("data[isOwnerDossierCheck]", None)] is False
    assert ("data[fullname]", 0) not in mapped
    assert mapped[("data[ownerFullname]", None)] == "Vũ Đình Tuyến"
    assert mapped[("data[ownerIdentityDate]", None)] == "09/05/2021"
    assert mapped[("data[fullname]", 1)] == "Vũ Đình Tuyến"
    assert mapped[("data[UqTcLs]", None)] == "Vũ Đình Soang và Vũ Đình Hải"
    assert mapped[("data[DataGrid][0][Ht]", None)] == "Vũ Đình Tuyên"
    assert mapped[("data[DataGrid][1][Ht]", None)] == "Vũ Thị Duyên"
    assert ("data[DataGrid][2][Ht]", None) not in mapped
    assert mapped[("data[ownerFullname]", None)] != "Vũ Thị Duyên"
    assert "không điền phần người nộp" in result["errors"][0]


@respx.mock
async def test_owner_self_submission_fills_explicit_owner_dates(monkeypatch):
    _mock_services(monkeypatch, _OUTPUT)

    result = await agent.run(
        {"doc": [_file("ho-so.pdf")]},
        {"formContext": {
            "applicantFullname": "Vũ Đình Tuyến",
            "applicantIdentityNumber": "034062017797",
        }},
    )
    mapped = {
        (field["name"], field.get("occurrence")): field["value"]
        for field in result["fields"]
    }

    assert mapped[("data[isOwnerDossierCheck]", None)] is True
    assert mapped[("data[fullname]", 0)] == "Vũ Đình Tuyến"
    assert mapped[("data[birthday]", 0)] == "08/03/1962"
    assert mapped[("data[ownerBirthday]", None)] == "08/03/1962"
    assert mapped[("data[ownerIdentityDate]", None)] == "09/05/2021"
    assert not result["errors"]
