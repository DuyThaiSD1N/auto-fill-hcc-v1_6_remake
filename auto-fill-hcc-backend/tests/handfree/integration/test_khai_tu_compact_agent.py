"""Compact agent đăng ký khai tử: phân vai người yêu cầu/người mất → field UI eForm cổng mới.

Runner khai_tu gọi LLM 2 LƯỢT (reason phân vai → trích xuất) trên cùng endpoint —
mock respx theo side_effect đúng thứ tự.
"""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.khai_tu import process as agent
from app.pipelines.khai_tu_dvcqg import process as khai_tu_dvcqg_agent
from app.pipelines.khai_tu.process.prompt import EXTRA_RULES
from app.pipelines.khai_tu.process.schema import FIELDS
from app.channels.handfree.procedure_registry import get_pipeline, get_procedure


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,QUFB"}


def _llm_response(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def _fields_response(fields: dict) -> httpx.Response:
    return _llm_response("```json\n" + json.dumps({"fields": fields}, ensure_ascii=False) + "\n```")


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")


@respx.mock
async def test_khai_tu_phan_vai_loai_cccd_lech_whitelist(monkeypatch):
    """Agent phân vai chốt số CCCD hai vai; agent trích xuất trả Cccd_* LỆCH whitelist
    → sanitize bỏ cụm danh tính người yêu cầu, mapper rơi về mặc định viền vàng."""
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(
            200, json={"results": [{"text": "CĂN CƯỚC CÔNG DÂN 040203015844"}] * 10}
        )
    )
    role_text = (
        "<nguoi_yeu_cau>\nHọ tên: TRẦN VĂN A\nSố CCCD/CMND: 040203015844\n</nguoi_yeu_cau>\n"
        "<nguoi_mat>\nHọ tên: NGUYỄN THỊ B\nSố CCCD/CMND: 038054000123\n</nguoi_mat>\n"
        "<giay_to_khong_thuoc_hai_vai>\nKhông có\n</giay_to_khong_thuoc_hai_vai>"
    )
    fields = {
        "Cccd_HoTen": "AI ĐÓ KHÁC",
        "Cccd_SoDinhDanh": "111111111111",   # lệch whitelist người yêu cầu → phải bị loại
        "NguoiMat_HoTen": "NGUYỄN THỊ B",
        "NguoiMat_SoDinhDanh": "038054000123",  # khớp whitelist người mất → giữ
        "NguoiMat_NgayMat": "05/06/2026",
    }
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        side_effect=[_llm_response(role_text), _fields_response(fields)]
    )

    options = {"formContext": {"applicantFullname": "TRẦN VĂN A",
                               "applicantIdentityNumber": "040203015844"}}
    res = await agent.run({"doc": [_file("ho so.jpg")]}, options)
    d = {f["name"]: f for f in res["fields"]}
    v = {name: f["value"] for name, f in d.items()}

    # Danh tính LỆCH whitelist bị loại (không điền "AI ĐÓ KHÁC"); lõi mới rơi về MỎ NEO
    # VNeID (formContext) với viền VÀNG thay vì bỏ trống — cán bộ/người dân tự rà.
    assert v["HoVaTenC"] == "TRẦN VĂN A" and d["HoVaTenC"].get("default") is True
    assert v["SoDinhDanhC"] == "040203015844"
    assert d["nycNoiCuTru"].get("default") is True  # cư trú người yêu cầu vẫn mặc định viền vàng
    assert v["HoTen"] == "NGUYỄN THỊ B"
    assert v["SoDinhDanh"] == "038054000123"        # giấy tờ người mất khớp whitelist → giữ


def test_khai_tu_compact_prompt_chua_quy_tac_phan_vai():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Đăng ký khai tử" in system_prompt
    assert "phan_vai_da_xac_dinh" in system_prompt
    # Wording lõi mới (đồng bộ auto-fill 2026-08): Cccd_* = dữ kiện in trên ẢNH THẺ.
    assert "Cccd_* = dữ kiện IN TRÊN ẢNH THẺ CCCD/CMND của chính người yêu cầu" in system_prompt
    assert "Quan hệ với người đã chết" in system_prompt
    assert "GIẤY BÁO TỬ" in system_prompt


def test_registry_khai_tu_entry():
    proc = get_procedure("khai-tu")

    # Key "khai-tu" chạy package SurveyJS của Cổng DVC quốc gia (eForm cũ đã thay).
    assert get_pipeline("khai-tu") is khai_tu_dvcqg_agent.run
    assert proc["mode"] == "agent" and proc["hasAttachmentStep"] is True
    assert not proc.get("hiddenFromList")           # đã đẩy lên card chọn thủ tục (2026-08-13)
    assert proc["needsAgencySelect"] is True
    assert proc["keKhaiUrl"].endswith("019d2bfd-3fac-7489-b53b-9c6c958f2da4")
    docs = {r["key"]: r for r in proc["requiredDocs"]}
    assert set(docs) == {"cccd", "bao_tu", "to_khai", "khac"}
    assert proc["hideRepeatableHint"] is True
    assert docs["cccd"]["name"] == "Căn cước công dân"
    assert docs["bao_tu"]["name"] == "Giấy báo tử hoặc giấy tờ thay giấy báo tử"
    assert docs["khac"]["name"] == "Giấy tờ liên quan khác"
    assert all(item["sides"] == 1 and item.get("repeatable") for item in docs.values())
    assert not docs["cccd"].get("optional")
    assert not docs["bao_tu"].get("optional")       # giấy báo tử BẮT BUỘC
    assert docs["to_khai"].get("optional") is True
    assert docs["khac"].get("optional") is True
