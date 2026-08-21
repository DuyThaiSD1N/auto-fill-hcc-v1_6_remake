"""Compact agent xác định mức độ khuyết tật: đơn đề nghị + CCCD -> Form.io fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.khuyet_tat import process as agent
from app.pipelines.khuyet_tat.process.prompt import EXTRA_RULES
from app.pipelines.khuyet_tat.process.schema import FIELDS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name, typ="application/pdf"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")


@respx.mock
async def test_khuyet_tat_compact_agent_maps_application_and_cccd(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "OCR TEXT"}] * 20})
    )
    llm_out = {
        "fields": {
            "Cccd_HoTen": "LẠI NGỌC MINH",
            "Cccd_SoDinhDanh": "012084000160",
            "Cccd_NgaySinh": "01/01/1984",
            "Cccd_GioiTinh": "Nam",
            "Cccd_NgayCap": "25/04/2021",
            "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Cccd_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh Lai Châu",
                "xa": "Phường Tân Phong",
                "diaChi": "Số nhà 003, phố Yết Kiêu, Tổ 16",
            },
            "DeNghi_NoiDung": "xac_dinh",
            "Nkt_HoTen": "LẠI MINH QUANG",
            "Nkt_NgaySinh": "27/10/2019",
            "Nkt_SoDinhDanh": "012219003077",
            "Nkt_GioiTinh": "Nam",
            "Nkt_ThuongTru": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Tân Phong",
                "diaChi": "Số nhà 003, phố Yết Kiêu, Tổ 16",
            },
            "Nkt_NoiOHienNay": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Tân Phong",
                "diaChi": "Số nhà 003, phố Yết Kiêu, Tổ 16",
            },
            "Ndd_HoTen": "LẠI NGỌC MINH",
            "Ndd_SoDinhDanh": "012084000160",
            "Ndd_QuanHe": "bố đẻ",
            "Ndd_SoDienThoai": "0984456132",
            "Ndd_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Tân Phong",
                "diaChi": "Số nhà 003, phố Yết Kiêu, Tổ 16",
            },
            "KhuyetTat_DanhMuc": ["kt5"],
            "KhuyetTat_ChiTiet": ["kt5_1", "kt5_3"],
            "MucDo_HoatDong": {
                "1": "THD",
                "2": "THD",
                "3": "THD",
                "4": "CTG",
                "5": "THD",
                "6": "THD",
                "7": "THD",
                "8": "KTHD",
                "9": "CTG",
                "10": "CTG",
            },
        }
    }
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(llm_out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )

    res = await agent.run({"doc": [_file("khuyết tật quang.pdf"), _file("cccd.pdf")]}, {})
    fields = res["fields"]
    d = {f["name"]: f["value"] for f in fields}

    assert fields[0] == {"name": "data[isOwnerDossierCheck]", "comp": "dom-checkbox", "value": True}
    assert d["data[fullname]"] == "LẠI NGỌC MINH"
    assert d["data[identityNumber]"] == "012084000160"
    assert d["data[identityDate]"] == "25/04/2021"
    assert d["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["data[province]"] == "Lai Châu"
    assert d["data[district]"] == "Tân Phong"
    assert d["data[address]"] == "Số nhà 003, phố Yết Kiêu, Tổ 16"
    assert d["data[phoneNumber]"] == "0984456132"

    assert d["data[chonNoiDungDeNghi][]"] is True
    assert d["data[NktHoTen]"] == "LẠI MINH QUANG"
    assert d["data[NktNgaySinh]"] == "27/10/2019"
    assert d["data[NktSoDinhdanh]"] == "012219003077"
    assert d["data[NktGioiTinh]"] == "Nam"
    assert d["data[NktMaTinh]"] == "Lai Châu"
    assert d["data[NktMaXa]"] == "Tân Phong"
    assert d["data[NktDiachi]"] == "Số nhà 003, phố Yết Kiêu, Tổ 16"

    assert d["data[NddHoTen]"] == "LẠI NGỌC MINH"
    assert d["data[NddSoDinhdanh]"] == "012084000160"
    assert d["data[NddQuanheNkt]"] == "Cha"
    assert d["data[NddSodienthoai]"] == "0984456132"
    assert d["data[NddMaTinh]"] == "Lai Châu"
    assert d["data[NddMaXa]"] == "Tân Phong"

    assert d["data[khuyetTat5Obj][khuyetTatRadio]"] == "co"
    assert d["data[khuyetTat5Obj][khuyetTatRadio1]"] == "co"
    assert d["data[khuyetTat5Obj][khuyetTatRadio3]"] == "co"
    assert d["data[mucDoKhuyetTatObj][mucDoRadio4]"] == "CTG"
    assert d["data[mucDoKhuyetTatObj][mucDoRadio8]"] == "KTHD"
    assert d["data[mucDoKhuyetTatObj][mucDoRadio10]"] == "CTG"
    assert not res["errors"]


def test_khuyet_tat_compact_prompt_contract():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "ĐƠN ĐỀ NGHỊ XÁC ĐỊNH" in system_prompt
    assert "Không trả field UI" in system_prompt
    assert "Đơn đề nghị là nguồn chính" in system_prompt
    assert "KhuyetTat_DanhMuc" in system_prompt
    assert "MucDo_HoatDong" in system_prompt
    assert "kt5_1" in system_prompt
    assert "kt5_3" in system_prompt
    assert "vỡ dòng" in system_prompt
    assert "tách riêng" in system_prompt
    assert "THD" in system_prompt


def test_registry_uses_khuyet_tat_process_pipeline():
    proc = get_procedure("xac-dinh-muc-do-khuyet-tat")

    assert get_pipeline("xac-dinh-muc-do-khuyet-tat") is agent.run
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["label"] == "Xác định, xác định lại mức độ khuyết tật và cấp Giấy xác nhận khuyết tật"
    assert proc["detect"]["textIncludes"] == [proc["label"]]
    assert get_attach_pipeline("xac-dinh-muc-do-khuyet-tat") is not None
    assert proc["roles"] == []
    assert "Đơn đề nghị" in proc["uploadHint"]
