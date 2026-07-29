"""Compact agent xét tuyển viên chức: Phiếu đăng ký + CCCD -> Form.io actions."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines.xet_tuyen_vien_chuc import process as agent
from app.procedures.registry import get_pipeline, get_procedure


def _file(name, typ="application/pdf"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")


def _mock_services(out):
    respx.post(settings.ocr_raw_base_url.rstrip("/") + "/api/v1/ocr/raw").mock(
        return_value=httpx.Response(200, json={"fullText": "OCR TEXT"})
    )
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )


def test_xet_tuyen_vien_chuc_registered():
    proc = get_procedure("xet-tuyen-vien-chuc")
    assert proc
    assert proc["label"] == "Thủ tục xét tuyển Viên chức (85/2023/NĐ-CP)"
    assert get_pipeline("xet-tuyen-vien-chuc") is agent.run


@respx.mock
async def test_xet_tuyen_vien_chuc_different_requester(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            "Phieu_HoTen": "LÒ THỊ XUYÊN",
            "Phieu_SoDinhDanh": "012345678901",
            "Phieu_NgaySinh": "02/02/1995",
            "Phieu_GioiTinh": "Nữ",
            "Phieu_HoKhau": {"tinh": "Lai Châu", "xa": "Tân Phong", "diaChi": "Tổ 3"},
            "Person1_HoTen": "VŨ ĐÌNH THIẾT",
            "Person1_SoDinhDanh": "040203015844",
            "Person1_NgaySinh": "26/04/2003",
            "Person1_GioiTinh": "Nam",
            "Person1_NgayCap": "25/04/2021",
            "Person1_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Person1_NoiCuTru": {"tinh": "Phú Thọ", "xa": "Hoàng Cương", "diaChi": "Khu 2"},
        }
    })

    res = await agent.run(
        {"doc": [_file("LoThiXuyen_signed_60_1764209575.pdf"), _file("00_CCD_H_I.pdf")]},
        {"formContext": {"applicantFullname": "Vũ Đình Thiết", "applicantIdentityNumber": "040203015844"}},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert res["fields"][0] == {"name": "data[isOwnerDossierCheck]", "comp": "dom-checkbox", "value": False}
    assert d["data[fullname]"] == "VŨ ĐÌNH THIẾT"
    assert d["data[identityNumber]"] == "040203015844"
    assert d["data[ownerFullname]"] == "LÒ THỊ XUYÊN"
    assert d["data[ownerIdentityNumber]"] == "012345678901"
    assert d["data[ownerProvince]"] == "Lai Châu"
    assert not res["errors"]
