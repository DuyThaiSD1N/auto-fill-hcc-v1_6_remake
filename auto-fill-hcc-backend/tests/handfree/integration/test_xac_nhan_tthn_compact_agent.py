"""Compact agent xác nhận tình trạng hôn nhân: 1 CCCD -> self fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines.xac_nhan_tthn.process import base_prompt as compact_prompt
from app.pipelines.xac_nhan_tthn import process as agent
from app.pipelines.xac_nhan_tthn.process.prompt import EXTRA_RULES
from app.pipelines.xac_nhan_tthn.process.schema import FIELDS
from app.channels.handfree.procedure_registry import get_owner_info_pipeline, get_pipeline, get_procedure
from app.pipelines.xac_nhan_tthn_dvc_moi import process as dvc_moi_agent


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,QUFB"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")


@respx.mock
async def test_xac_nhan_tthn_compact_agent_maps_divorce_decision(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 10})
    )
    out = {
        "fields": {
            "NguoiDuocCap_HoTen": "PHẠM MINH TUÂN",
            "NguoiDuocCap_SoDinhDanh": "012071000001",
            "NguoiDuocCap_NgaySinh": "01/01/1971",
            "NguoiDuocCap_GioiTinh": "Nam",
            "NguoiDuocCap_NgayCap": "02/02/2021",
            "NguoiDuocCap_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
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
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 10})
    )
    out = {"fields": {"NguoiDuocCap_HoTen": "NGUYỄN VĂN A", "NguoiDuocCap_SoDinhDanh": "012345678901"}}
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

    # Wording lõi mới 2026-08 (đồng bộ auto-fill): phân vai BẢN THÂN/ỦY QUYỀN thay câu
    # "mặc định là bản thân"; TinhTrangHonNhanC1 là MÃ chữ đọc theo nội dung dòng tình trạng hôn nhân.
    assert "A. BẢN THÂN: người yêu cầu chính là người cần giấy XNTTHN" in system_prompt
    assert "NguoiDuocCap_* = thông tin IN trên giấy tờ của NGƯỜI ĐƯỢC CẤP" in system_prompt
    assert "Không trả field UI/default" in system_prompt
    assert "quanhevoinguoiduocxacminh" in system_prompt
    assert "BanAn_Number/Date/Agency: CHỈ đọc từ VĂN BẢN quyết định/bản án ly hôn" in system_prompt
    assert "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN CŨ" in system_prompt  # nguồn giấy XNTTHN cũ
    assert "TinhTrangHonNhanC1 = MỘT mã chữ dưới đây" in system_prompt
    assert "Không suy luận tình trạng hôn nhân từ CCCD" in system_prompt


def test_registry_uses_xac_nhan_tthn_compact_agent_mode():
    proc = get_procedure("xac-nhan-tinh-trang-hon-nhan")

    # Trang nộp một trang của Cổng DVC quốc gia mới: không bước chủ hồ sơ.
    assert get_pipeline("xac-nhan-tinh-trang-hon-nhan") is dvc_moi_agent.run
    assert get_owner_info_pipeline("xac-nhan-tinh-trang-hon-nhan") is None
    assert proc["flowProfile"] == "tu-phap-moi"
    assert "ownerInfo" not in proc
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["roles"] == []
    assert "useRequestMode" not in proc
