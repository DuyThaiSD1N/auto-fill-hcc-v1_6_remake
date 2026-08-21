"""Compact agent đăng ký đất đai lần đầu: OCR text -> CCCD/GCN facts -> DOM UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines.dang_ky_dat_dai import process as agent
from app.pipelines.dang_ky_dat_dai.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_dat_dai.process.schema import FIELDS
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.procedures.registry import get_pipeline, get_procedure


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


@respx.mock
async def test_dang_ky_dat_dai_compact_agent_derives_ui_fields(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 20})
    )
    out = {
        "fields": {
            "Cccd_HoTen": "TRẦN THÀNH CÔNG",
            "Cccd_SoDinhDanh": "025203007360",
            "Cccd_NgaySinh": "11/07/2003",
            "Cccd_GioiTinh": "Nam",
            "Cccd_DanToc": "Kinh",
            "Cccd_NgayCap": "12/06/2021",
            "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Gcn_SoPhatHanh": "AB 123456 (số vào sổ: CH 00120)",
            "Gcn_SoVaoSo": "CH 00120",
            "Gcn_NgayCap": "21/12/2010",
            "Gcn_CoQuanCap": "TM. ỦY BAN NHÂN DÂN Thị xã Lai Châu, tỉnh Lai Châu - CHỦ TỊCH",
            "CongDan_soGCNGP": "UI_SAI",
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
        {"doc": [_file("cccd.jpg"), _file("giay chung nhan qsd dat.pdf", "application/pdf")]},
        {},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["CongDan_tenCongDan"] == "TRẦN THÀNH CÔNG"
    assert d["CongDan_tenCoQuanToChuc"] == "TRẦN THÀNH CÔNG"
    assert d["CongDan_maSoThueNguoiNop"] == "025203007360"
    assert d["CongDan_soCmnd"] == "025203007360"
    assert d["CongDan_soCCCD"] == "025203007360"
    assert d["CongDan_ngayCapCmnd"] == "12/06/2021"
    assert d["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["CongDan_maDMQuocGia"] == "Việt Nam"
    assert d["CongDan_diaChiNuocNgoai"] == "Việt Nam"
    assert d["CongDan_soGCNGP"] == "AB 123456"
    assert "CH 00120" not in d["CongDan_soGCNGP"]
    assert d["CongDan_ngayCapGCNGP"] == "21/12/2010"
    assert d["CongDan_noiCapGCNGP"] == "UBND Thị xã Lai Châu, tỉnh Lai Châu"
    assert next(f for f in res["fields"] if f["name"] == "CongDan_soGCNGP")["aliases"] == ["soGCNGP"]
    assert not res["errors"]


@respx.mock
async def test_dang_ky_dat_dai_falls_back_to_ocr_gcn_serial(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    ocr_text = "\n".join([
        "GIẤY CHỨNG NHẬN",
        "QUYỀN SỬ DỤNG ĐẤT",
        "SOAN 276270",
        "---",
        "Ngày 24 tháng 7 năm 2009",
        "Số vào sổ cấp giấy chứng nhận quyền sử dụng đất:",
        "H 0.0.2.0.6..",
    ])
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": ocr_text}] * 20})
    )
    out = {
        "fields": {
            "Gcn_NgayCap": "24/07/2009",
            "Gcn_CoQuanCap": "UBND Thị xã Lai Châu, tỉnh Lai Châu",
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

    res = await agent.run({"doc": [_file("giay chung nhan qsd dat.pdf", "application/pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["CongDan_soGCNGP"] == "AN 276270"
    assert d["CongDan_ngayCapGCNGP"] == "24/07/2009"
    assert d["CongDan_noiCapGCNGP"] == "UBND Thị xã Lai Châu, tỉnh Lai Châu"
    assert not res["errors"]


def test_dang_ky_dat_dai_prompt_locks_gcn_serial():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Gcn_SoPhatHanh là SỐ PHÁT HÀNH GCN" in system_prompt
    assert "KHÔNG ghép \"số vào sổ\"" in system_prompt
    assert "Gcn_SoVaoSo" in system_prompt
    assert "Không trả field UI/default" in system_prompt


def test_registry_uses_dang_ky_dat_dai_compact_agent_mode():
    proc = get_procedure("dang-ky-dat-dai-lan-dau")

    assert get_pipeline("dang-ky-dat-dai-lan-dau") is agent.run
    assert proc["label"] == "Đăng ký đất đai lần đầu"
    assert proc["mode"] == "agent"
    assert proc["roles"] == []
    assert "Giấy chứng nhận quyền sử dụng đất" in proc["uploadHint"]
