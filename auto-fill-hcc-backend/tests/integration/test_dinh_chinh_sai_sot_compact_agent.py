"""Compact agent đính chính sai sót: OCR text -> người nộp/GCN facts -> DOM UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines.dinh_chinh_sai_sot import process as agent
from app.pipelines.dinh_chinh_sai_sot.process.prompt import EXTRA_RULES
from app.pipelines.dinh_chinh_sai_sot.process.schema import FIELDS
from app.pipelines.dinh_chinh_sai_sot.process import mapper
from app.pipelines.dinh_chinh_sai_sot.process.fallback import apply_ocr_fallback
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.procedures.registry import get_pipeline, get_procedure
from app.services import ocr


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


@respx.mock
async def test_dinh_chinh_sai_sot_compact_agent_derives_ui_fields(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")

    async def fake_ocr(files):
        return [
            {"name": file["name"], "type": file["type"], "text": "...", "provider": "test"}
            for file in files
        ]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    out = {
        "fields": {
            "NguoiNop_HoTen": "VŨ ĐÌNH THIẾT",
            "NguoiNop_SoDinhDanh": "040203015844",
            "NguoiNop_NgaySinh": "26/04/2003",
            "NguoiNop_GioiTinh": "Nam",
            "NguoiNop_DanToc": "Kinh",
            "NguoiNop_NgayCapGiayTo": "02/07/2021",
            "NguoiNop_NoiCapGiayTo": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
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

    assert d["CongDan_tenCongDan"] == "VŨ ĐÌNH THIẾT"
    assert "CongDan_tenCoQuanToChuc" not in d
    assert "CongDan_maSoThueNguoiNop" not in d
    assert d["CongDan_soCmnd"] == "040203015844"
    assert d["CongDan_soCCCD"] == "040203015844"
    assert d["CongDan_ngayCapCmnd"] == "02/07/2021"
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
async def test_dinh_chinh_sai_sot_falls_back_to_ocr_gcn_serial(monkeypatch):
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

    async def fake_ocr(files):
        return [
            {"name": file["name"], "type": file["type"], "text": ocr_text, "provider": "test"}
            for file in files
        ]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
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


def test_dinh_chinh_sai_sot_prompt_locks_gcn_serial():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Gcn_SoPhatHanh là SỐ PHÁT HÀNH GCN" in system_prompt
    assert "KHÔNG ghép \"số vào sổ\"" in system_prompt
    assert "Gcn_SoVaoSo" in system_prompt
    assert "Không trả field UI/default" in system_prompt


def test_dinh_chinh_sai_sot_falls_back_to_identity_issue_date_on_application():
    fields = {
        "NguoiNop_HoTen": "GIÀNG A TỦA",
        "NguoiNop_SoDinhDanh": "012080000778",
    }
    documents = [{
        "text": (
            "Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất:\n"
            "Tên: GIÀNG A TỦA Sinh ngày: 22/02/1980\n"
            "Giấy tờ nhân thân/pháp nhân(3): Căn cước công dân số 012080000778, "
            "ngày cấp: 28/04/2021, nơi cấp: Cục cảnh sát QLHC về TTXH\n"
            "Địa chỉ: Bản Tả Cu Tỷ, xã Tả Lèng, tỉnh Lai Châu\n"
            "Tả Lèng, ngày 27 tháng 7 năm 2026"
        )
    }]

    result = apply_ocr_fallback(fields, documents)

    assert result["NguoiNop_NgayCapGiayTo"] == "28/04/2021"


def test_dinh_chinh_sai_sot_migrates_legacy_applicant_field_names():
    result = apply_ocr_fallback({
        "Cccd_HoTen": "GIÀNG A TỦA",
        "Cccd_NgayCap": "28/04/2021",
        "Don_DienThoaiLienHe": "0349129815",
    }, [])

    assert result["NguoiNop_HoTen"] == "GIÀNG A TỦA"
    assert result["NguoiNop_NgayCapGiayTo"] == "28/04/2021"
    assert result["NguoiNop_DienThoai"] == "0349129815"
    assert "Cccd_HoTen" not in result
    assert "Cccd_NgayCap" not in result
    assert "Don_DienThoaiLienHe" not in result


def test_dinh_chinh_sai_sot_does_not_fill_organization_or_tax_fields():
    fields = [
        {"name": "NguoiNop_HoTen", "comp": "x-input", "value": "GIÀNG A TỦA"},
        {"name": "NguoiNop_SoDinhDanh", "comp": "x-input", "value": "012080000778"},
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(fields)}

    assert result["CongDan_tenCongDan"] == "GIÀNG A TỦA"
    assert result["CongDan_soCmnd"] == "012080000778"
    assert "CongDan_tenCoQuanToChuc" not in result
    assert "CongDan_maSoThueNguoiNop" not in result


def test_dinh_chinh_sai_sot_maps_application_contact_phone():
    fields = [
        {"name": "NguoiNop_DienThoai", "comp": "x-input", "value": "0349 / 129 815"},
    ]

    result = {field["name"]: field["value"] for field in mapper.enrich(fields)}

    assert result["CongDan_diDong"] == "0349129815"


def test_dinh_chinh_sai_sot_schema_requests_application_contact_phone():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "NguoiNop_DienThoai" in system_prompt
    assert 'nhãn "Điện thoại liên hệ (nếu có)"' in system_prompt
    assert "không lấy số CCCD, số GCN" in system_prompt
    assert 'đúng cụm "Giấy tờ nhân thân/pháp nhân"' in system_prompt
    assert "BẮT BUỘC trả đủ NguoiNop_SoDinhDanh" in system_prompt
    assert "NguoiNop_NgayCapGiayTo và NguoiNop_NoiCapGiayTo" in system_prompt
    assert "Cccd_HoTen" not in system_prompt
    assert "Cccd_NgayCap" not in system_prompt
    assert "Don_DienThoaiLienHe" not in system_prompt


def test_registry_uses_dinh_chinh_sai_sot_compact_agent_mode():
    proc = get_procedure("dinh-chinh-sai-sot")

    assert get_pipeline("dinh-chinh-sai-sot") is agent.run
    assert proc["mode"] == "agent"
    assert proc["roles"] == []
    assert "Giấy chứng nhận quyền sử dụng đất" in proc["uploadHint"]
