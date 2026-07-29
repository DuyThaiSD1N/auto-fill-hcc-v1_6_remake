"""Compact agent mai táng phí dân công hỏa tuyến: bản khai + CCCD -> Form.io actions."""

import base64
import io
import json
import zipfile

import httpx
import respx

from app.config import settings
from app.pipelines.mai_tang_dan_cong import process as agent
from app.procedures.registry import get_pipeline, get_procedure


def _file(name, typ="application/pdf"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def _docx_file(name, text):
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", xml)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {
        "name": name,
        "type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "dataUrl": "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64," + b64,
    }


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


def test_mai_tang_dan_cong_registered():
    proc = get_procedure("mai-tang-dan-cong-hoa-tuyen")
    assert proc
    assert "dân công hỏa tuyến" in proc["label"]
    assert get_pipeline("mai-tang-dan-cong-hoa-tuyen") is agent.run


@respx.mock
async def test_mai_tang_dan_cong_same_owner(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            "ToKhai_ThanNhanHoTen": "Vũ Đình Thiết",
            "ToKhai_ThanNhanNgaySinh": "26/04/2003",
            "ToKhai_ThanNhanSoDienThoai": "0976134251",
            "ToKhai_ThanNhanTruQuan": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Tân Phong",
                "diaChi": "Tổ dân phố Tả Làn Than",
            },
            "Person1_HoTen": "VŨ ĐÌNH THIẾT",
            "Person1_SoDinhDanh": "040203015844",
            "Person1_GioiTinh": "Nam",
            "Person1_NgayCap": "25/04/2021",
            "Person1_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        }
    })

    res = await agent.run(
        {"doc": [_docx_file("TorKhai_VuDinhThiet.docx", "Bản khai của thân nhân"), _file("cccd_thiet.pdf")]},
        {"formContext": {"applicantFullname": "Vũ Đình Thiết", "applicantIdentityNumber": "040203015844"}},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert res["fields"][0] == {"name": "data[isOwnerDossierCheck]", "comp": "dom-checkbox", "value": True}
    assert d["data[fullname]"] == "Vũ Đình Thiết"
    assert d["data[birthday]"] == "26/04/2003"
    assert d["data[phoneNumber]"] == "0976134251"
    assert d["data[identityNumber]"] == "040203015844"
    assert d["data[identityDate]"] == "25/04/2021"
    assert d["data[province]"] == "Lai Châu"
    assert "data[ownerFullname]" not in d
    assert not res["errors"]
