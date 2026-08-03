"""Contract OCR -> compact LLM -> mapper cho cấp GCN ATTP nông, lâm, thủy sản."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines.cap_gcn_attp_nong_lam_thuy_san import process as agent


def _file(name: str) -> dict:
    return {"name": name, "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AAA"}


@respx.mock
async def test_compact_agent_maps_sample_application_and_two_cccd_roles(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")

    async def fake_ocr_per_file(files):
        return [{"name": file["name"], "type": file["type"], "text": "OCR sample", "provider": "raw"} for file in files]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    compact = {
        "fields": {
            "Person1_HoTen": "VŨ ĐÌNH THIẾT",
            "Person1_SoDinhDanh": "040203015844",
            "Person1_NgaySinh": "26/04/2003",
            "Person1_GioiTinh": "Nam",
            "Person1_NgayCap": "02/07/2021",
            "Person1_NoiCuTru": {
                "quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Xã Tam Hợp", "diaChi": "Xóm Long Thành",
            },
            "Person2_HoTen": "ĐẶNG MINH HOÀNG",
            "Person2_SoDinhDanh": "048075012345",
            "Person2_NoiCuTru": {
                "quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Phường An Hải", "diaChi": "Tổ 12",
            },
            "Don_DiaDanh": "Đà Nẵng",
            "Don_NgayDon": "16/04/2026",
            "Don_KinhGui": "Chi cục Biển đảo và Thủy sản thành phố Đà Nẵng",
            "Don_TenCoSo": "Đặng Minh Hoàng – Tàu cá ĐNA 90679",
            "Don_DiaChiCoSo": {
                "quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Phường An Hải", "diaChi": "",
            },
            "Don_DienThoai": "0973329308",
            "Don_MaSoDKKD": "32C8019879",
            "Don_SoDangKy": "Đăng ký lần đầu",
            "Don_NgayCapDKKD": "14/04/2025",
            "Don_MatHang": "Hải sản",
            "Don_LyDoCap": "Cấp mới",
            "Don_DaiDienCoSo": "ĐẶNG MINH HOÀNG",
        }
    }
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(compact, ensure_ascii=False)}}]},
        )
    )

    result = await agent.run(
        {"doc": [_file("cccd-nguoi-nop.pdf"), _file("cccd-chu-co-so.pdf"), _file("don-phu-luc-i.pdf")]},
        {"formContext": {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        }},
    )

    assert result["errors"] == []
    assert next(field for field in result["fields"] if field["name"] == "data[isOwnerDossierCheck]")["value"] is False
    assert next(field for field in result["fields"] if field["name"] == "data[fullname]")["value"] == "Vũ Đình Thiết"
    assert next(field for field in result["fields"] if field["name"] == "data[ownerFullname]")["value"] == "ĐẶNG MINH HOÀNG"
    application_address = next(
        field for field in result["fields"]
        if field["name"] == "data[address]" and field.get("occurrence") == 1
    )
    assert application_address["value"] == "Phường An Hải, Thành phố Đà Nẵng"
