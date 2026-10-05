"""Focused process tests cho mai táng người hưởng hưu trí xã hội."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi import process as agent


def _file(name: str):
    return {"name": name, "type": "image/jpeg", "dataUrl": "data:x;base64,QUFB"}


def _mock_services(monkeypatch, output: dict):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "OCR TEXT"}] * 20})
    )
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(output, ensure_ascii=False) + "\n```"
            }}]},
        )
    )


_OWNER = {
    "ChuHoSo_HoTen": "ĐẶNG VĂN LÂM",
    "ChuHoSo_NgaySinh": "03/03/1980",
    "ChuHoSo_SoDinhDanh": "068080000292",
    "ChuHoSo_NgayCap": "08/07/2022",
    "ChuHoSo_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "ChuHoSo_NoiCuTru": {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Đơn Dương",
        "diaChi": "Thạnh Nghĩa",
    },
    "ChuHoSo_DienThoai": "0974814031",
}


@respx.mock
async def test_owner_self_submission_ticks_and_explicitly_fills_owner_birthday(monkeypatch):
    _mock_services(monkeypatch, {"fields": {
        **_OWNER,
        "Person2_HoTen": "ĐẶNG VĂN LONG",
    }})

    result = await agent.run(
        {"doc": [_file("to-khai.jpg"), _file("trich-luc.jpg")]},
        {"formContext": {
            "applicantFullname": "ĐẶNG VĂN LÂM",
            "applicantIdentityNumber": "068080000292",
        }},
    )
    fields = {field["name"]: field["value"] for field in result["fields"]}

    assert fields["data[isOwnerDossierCheck]"] is True
    assert fields["data[fullname]"] == "ĐẶNG VĂN LÂM"
    assert fields["data[ownerBirthday]"] == "03/03/1980"
    assert fields["data[phoneNumber]"] == "0974814031"
    assert "data[ownerFullname]" not in fields
    assert "ĐẶNG VĂN LONG" not in fields.values()
    assert not result["errors"]


@respx.mock
async def test_unmatched_ui_returns_owner_only(monkeypatch):
    _mock_services(monkeypatch, {"fields": _OWNER})

    result = await agent.run(
        {"doc": [_file("to-khai.jpg"), _file("trich-luc.jpg")]},
        {"formContext": {
            "applicantFullname": "VŨ ĐÌNH THIẾT",
            "applicantIdentityNumber": "040203015844",
        }},
    )
    fields = {field["name"]: field["value"] for field in result["fields"]}

    assert fields["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in fields
    assert fields["data[ownerFullname]"] == "ĐẶNG VĂN LÂM"
    assert fields["data[ownerBirthday]"] == "03/03/1980"
    assert "không điền phần người nộp" in result["errors"][0]


_DECEASED = {
    "NguoiMat_HoTen": "LÊ THỊ HOA",
    "NguoiMat_NgaySinh": "05/05/1945",
    "NguoiMat_GioiTinh": "Nữ",
    "NguoiMat_SoDinhDanh": "035145009876",
}


@respx.mock
async def test_deceased_as_owner_flag_requests_and_fills_deceased(monkeypatch):
    """Cờ Cam Đường: prompt có nhóm NguoiMat_* và người chết vào khối chủ hồ sơ."""
    _mock_services(monkeypatch, {"fields": {**_OWNER, **_DECEASED}})

    result = await agent.run(
        {"doc": [_file("to-khai.jpg"), _file("trich-luc.jpg")]},
        {"deceasedAsOwner": True, "formContext": {
            "applicantFullname": "ĐẶNG VĂN LÂM",
            "applicantIdentityNumber": "068080000292",
        }},
    )
    fields = {field["name"]: field["value"] for field in result["fields"]}
    system_prompt = json.loads(respx.calls.last.request.content)["messages"][0]["content"]

    assert "NguoiMat_HoTen" in system_prompt
    assert fields["data[isOwnerDossierCheck]"] is False
    assert fields["data[fullname]"] == "ĐẶNG VĂN LÂM"
    assert fields["data[ownerFullname]"] == "LÊ THỊ HOA"
    assert fields["data[ownerIdentityNumber]"] == "035145009876"
    assert not result["errors"]


@respx.mock
async def test_without_flag_deceased_fields_are_dropped(monkeypatch):
    _mock_services(monkeypatch, {"fields": {**_OWNER, **_DECEASED}})

    result = await agent.run({"doc": [_file("to-khai.jpg")]}, {"formContext": {}})
    fields = {field["name"]: field["value"] for field in result["fields"]}
    system_prompt = json.loads(respx.calls.last.request.content)["messages"][0]["content"]

    assert "NguoiMat_HoTen" not in system_prompt
    assert fields["data[ownerFullname]"] == "ĐẶNG VĂN LÂM"
    assert "LÊ THỊ HOA" not in fields.values()
