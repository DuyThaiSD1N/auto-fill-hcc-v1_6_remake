"""Compact agent xác nhận tình trạng hôn nhân: 1 CCCD -> self fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.xac_nhan_tthn import process as agent
from app.pipelines.xac_nhan_tthn.process.prompt import EXTRA_RULES
from app.pipelines.xac_nhan_tthn.process.schema import FIELDS
from app.procedures.registry import get_pipeline, get_procedure


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")


@respx.mock
async def test_xac_nhan_tthn_compact_agent_derives_self_ui_fields(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_raw_base_url.rstrip("/") + "/api/v1/ocr/raw").mock(
        return_value=httpx.Response(200, json={"fullText": "..."})
    )
    out = {
        "fields": {
            "Cccd_HoTen": "VŨ ĐÌNH THIẾT",
            "Cccd_SoDinhDanh": "040203015844",
            "Cccd_NgaySinh": "26/4/2003",
            "Cccd_GioiTinh": "Nam",
            "Cccd_DanToc": "Kinh",
            "Cccd_NgayCap": "2/7/2021",
            "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Cccd_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Nghệ An",
                "diaChi": "Xóm Long Thành",
            },
            "HoVaTenC1": "UI_SAI",
            "TinhTrangHonNhanC1": "Độc thân",
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

    res = await agent.run({"doc": [_file("cccd truoc.jpg"), _file("cccd sau.jpg")]}, {})
    by_name = {f["name"]: f for f in res["fields"]}
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["loaiDangKy"] == "1"
    assert by_name["loaiDangKy"]["aliases"] == ["LoaiDangKy"]
    assert d["HoVaTenC"] == "VŨ ĐÌNH THIẾT"
    assert d["SoDinhDanhC"] == "040203015844"
    assert d["LoaiGiayToDinhDanhC"] == "Căn cước công dân"
    assert d["NgayCapDDC"] == "02/07/2021"
    assert d["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["nycLoaiCuTru"] == "Thường trú"
    assert d["nycNoiCuTru"] == "1"
    assert d["nycNoiCuTru_TrongNuoc"]["tinh"] == "Nghệ An"

    assert d["quanhevoinguoiduocxacminh"] == "1"
    assert d["HoVaTenC1"] == "VŨ ĐÌNH THIẾT"
    assert d["NgaySinhC1"] == "26/04/2003"
    assert d["GioiTinhC1"] == "Nam"
    assert d["DanTocC1"] == "Kinh"
    assert d["QuocTichC1"] == "Việt Nam"
    assert d["SoDinhDanhC1"] == "040203015844"
    assert d["SoGiayToTuyThanC1"] == "040203015844"
    assert by_name["SoGiayToTuyThanC1"]["aliases"] == ["SoGiayToDinhDanhC1"]
    assert d["LoaiGiayToDinhDanhC1"] == "Căn cước công dân"
    assert d["NgayCapDDC1"] == "02/07/2021"
    assert d["NoiCapDDC1"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["nxnLoaiCuTru"] == "Thường trú"
    assert d["nxnNoiCuTru"] == "1"
    assert d["nxnNoiCuTru_TrongNuoc"]["diaChi"] == "Xóm Long Thành"
    assert d["mucdich"] == "Sử dụng vào mục đích khác"
    assert d["TraKQ"] == "1"

    assert "TinhTrangHonNhanC1" not in d
    assert not res["errors"]


@respx.mock
async def test_xac_nhan_tthn_compact_agent_maps_divorce_decision(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_raw_base_url.rstrip("/") + "/api/v1/ocr/raw").mock(
        return_value=httpx.Response(200, json={"fullText": "..."})
    )
    out = {
        "fields": {
            "Cccd_HoTen": "PHẠM MINH TUÂN",
            "Cccd_SoDinhDanh": "012071000001",
            "Cccd_NgaySinh": "01/01/1971",
            "Cccd_GioiTinh": "Nam",
            "Cccd_NgayCap": "02/02/2021",
            "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "DivorceDecision_Number": "16/2012/QĐST-HNGĐ",
            "DivorceDecision_Date": "03/05/2012",
            "DivorceDecision_Agency": "Tòa án nhân dân thị xã Lai Châu, tỉnh Lai Châu",
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

    res = await agent.run({"doc": [_file("cccd.pdf", "application/pdf"), _file("qd-ly-hon.pdf", "application/pdf")]}, {})
    by_name = {f["name"]: f for f in res["fields"]}
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["TinhTrangHonNhanC1"] == (
        "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; "
        "hiện tại chưa đăng ký kết hôn với ai"
    )
    assert by_name["nxnLoaiTinhTrangHonNhan=3"]["aliases"] == ["nxnLoaiTinhTrangHonNhan=2"]
    divorce_detail = d["nxnLoaiTinhTrangHonNhan=3"]
    assert divorce_detail["soBanAnQuyetDinhLyHon"] == "16/2012/QĐST-HNGĐ"
    assert divorce_detail["ngayCapBanAnQuyetDinhLyHon"] == "03/05/2012"
    assert divorce_detail["coQuanCapBanAnQuyetDinhLyHon"] == "Tòa án nhân dân thị xã Lai Châu, tỉnh Lai Châu"


@respx.mock
async def test_xac_nhan_tthn_compact_agent_defaults_issuer(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_raw_base_url.rstrip("/") + "/api/v1/ocr/raw").mock(
        return_value=httpx.Response(200, json={"fullText": "..."})
    )
    out = {"fields": {"Cccd_HoTen": "NGUYỄN VĂN A", "Cccd_SoDinhDanh": "012345678901"}}
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )

    res = await agent.run({"doc": [_file("cccd.jpg")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["HoVaTenC"] == "NGUYỄN VĂN A"
    assert d["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["NoiCapDDC1"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_xac_nhan_tthn_compact_prompt_rejects_ui_fields():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "mặc định NGƯỜI YÊU CẦU là BẢN THÂN" in system_prompt
    assert "Cccd_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND" in system_prompt
    assert "Không trả field UI/default" in system_prompt
    assert "quanhevoinguoiduocxacminh" in system_prompt
    assert "DivorceDecision_* lấy từ OCR" in system_prompt
    assert "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN CŨ" in system_prompt  # nguồn giấy XNTTHN cũ
    assert "Không trả TinhTrangHonNhanC1" in system_prompt
    assert "Không suy luận tình trạng hôn nhân từ CCCD" in system_prompt


def test_registry_uses_xac_nhan_tthn_compact_agent_mode():
    proc = get_procedure("xac-nhan-tinh-trang-hon-nhan")

    assert get_pipeline("xac-nhan-tinh-trang-hon-nhan") is agent.run
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["roles"] == []
    assert "useRequestMode" not in proc
    assert "Mặc định người yêu cầu là bản thân" in proc["uploadHint"]
