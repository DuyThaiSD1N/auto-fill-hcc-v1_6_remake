"""Compact agent trích lục khai sinh: short LLM output -> legacy x-* UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.trich_luc import process as agent
from app.pipelines.trich_luc.process import mapper
from app.pipelines.trich_luc.process.prompt import EXTRA_RULES
from app.pipelines.trich_luc.process.schema import FIELDS
from app.procedures.registry import get_pipeline


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def test_trich_luc_maps_explicit_copy_quantity_and_does_not_default_three():
    source_fields = [
        {"name": "CopyRequest_Quantity", "value": "10 bản"},
    ]

    result = {field["name"]: field for field in mapper.enrich(source_fields)}

    assert result["SoLuong"]["value"] == "10"
    assert result["SoLuong"].get("default") is not True
    assert "CapBanSao" not in result


def test_trich_luc_ignores_copy_choice_without_quantity():
    yes = {
        field["name"]: field
        for field in mapper.enrich([{"name": "CopyRequest_WantsCopy", "value": "Có"}])
    }
    no = {
        field["name"]: field
        for field in mapper.enrich([{"name": "CopyRequest_WantsCopy", "value": "Không"}])
    }

    assert "CapBanSao" not in yes
    assert "SoLuong" not in yes
    assert "CapBanSao" not in no
    assert "SoLuong" not in no


def test_trich_luc_does_not_fill_copy_fields_without_declaration():
    result = {
        field["name"]: field
        for field in mapper.enrich([{"name": "HoTich_LoaiSuKien", "value": "birth"}])
    }

    assert "CapBanSao" not in result
    assert "SoLuong" not in result


def test_trich_luc_replaces_declaration_title_with_civil_status_document_name():
    source_fields = [
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_TenGiayTo", "value": "Tờ khai đăng ký lại khai sinh"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN VĂN A"},
    ]

    result = {field["name"]: field for field in mapper.enrich(source_fields)}

    assert result["HoSo_TenGiayTo"]["value"] == "Giấy khai sinh"


def test_trich_luc_preserves_xuan_huong_ward_prefix_for_form_option():
    source_fields = [
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN VĂN A"},
        {
            "name": "HoTich_NoiCuTru",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Lâm Đồng",
                "xa": "Phường Xuân Hương",
                "diaChi": "10/4 Đường A",
            },
        },
    ]

    result = {field["name"]: field for field in mapper.enrich(source_fields)}

    assert result["NDK_NoiCuTru_TrongNuoc"]["value"]["xa"] == "Phường Xuân Hương"


@respx.mock
async def test_trich_luc_compact_agent_derives_ui_fields(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    respx.post(settings.ocr_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "..."}}]})
    )
    out = {
        "fields": {
            "Cccd_HoTen": "TRẦN THÀNH CÔNG",
            "Cccd_SoDinhDanh": "025203007360",
            "Cccd_NgayCap": "12/6/2021",
            "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Cccd_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Phú Thọ",
                "diaChi": "Khu 2",
            },
            "HoTich_LoaiSuKien": "birth",
            "HoTich_TenGiayTo": "Giấy khai sinh",
            "HoTich_HoTenNguoiDuocDangKy": "VÀNG A PHỈNH",
            "HoTich_NgaySinh": "6/5/2025",
            "HoTich_GioiTinh": "Nam",
            "HoTich_DanToc": "Mông",
            "HoTich_SoDinhDanh": "012225001150",
            "HoTich_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "diaChi": "Tổ 3",
            },
            "HoTich_CoQuanDangKy": "UBND xã Lản Nhì Thàng",
            "HoTich_So": "47",
            "HoTich_QuyenSo": "01/2025",
            "HoTich_NgayDangKy": "7/5/2025",
            "HoVaTenC": "SAI_FIELD_UI",
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
        {"doc": [_file("cccd truoc.jpg"), _file("cccd sau.jpg"), _file("gks.pdf", "application/pdf")]},
        {},
    )
    by_name = {f["name"]: f for f in res["fields"]}
    d = {name: f["value"] for name, f in by_name.items()}

    assert d["HoVaTenC"] == "TRẦN THÀNH CÔNG"
    assert by_name["HoVaTenC"]["aliases"] == ["NYC_HoVaTen"]
    assert d["SoDinhDanhC"] == "025203007360"
    assert by_name["SoDinhDanhC"]["aliases"] == ["NYC_SoDinhDanh"]
    assert d["LoaiGiayToDinhDanhC"] == "Căn cước công dân"
    assert by_name["LoaiGiayToDinhDanhC"]["aliases"] == ["NYC_LoaiGiayToTuyThan"]
    assert d["NYC_SoGiayToTuyThan"] == "025203007360"
    assert d["NgayCapDDC"] == "12/06/2021"
    assert by_name["NgayCapDDC"]["aliases"] == ["NYC_NgayCap"]
    assert d["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by_name["NoiCapDDC"]["aliases"] == ["NYC_NoiCap"]
    assert d["NYC_LoaiCuTru"] == "Thường trú"
    assert d["NYC_NoiCuTru"] == "1"
    assert d["NYC_NoiCuTru_TrongNuoc"]["tinh"] == "Phú Thọ"

    assert d["NDK_HoVaTen"] == "VÀNG A PHỈNH"
    assert d["NDK_NgaySinh"] == "06/05/2025"
    assert d["NDK_GioiTinh"] == "Nam"
    assert d["NDK_DanToc"] == "Mông"
    assert d["NDK_QuocTich"] == "Việt Nam"
    assert d["NDK_SoDinhDanh"] == "012225001150"
    assert d["NDK_LoaiCuTru"] == "Thường trú"
    assert d["NDK_NoiCuTru"] == "1"
    assert d["NDK_NoiCuTru_TrongNuoc"]["diaChi"] == "Tổ 3"

    assert d["HoSo_LoaiYeuCau"].startswith("Giấy khai sinh bản sao")
    assert d["HoSo_CoQuanDangKy"] == "UBND xã Lản Nhì Thàng"
    assert d["HoSo_TenGiayTo"] == "Giấy khai sinh"
    assert d["HoSo_So"] == "47"
    assert d["HoSo_QuyenSo"] == "01/2025"
    assert d["HoSo_NgayCapSo"] == "07/05/2025"
    assert d["PhuongThucNhanKQ"] == "2"

    assert "NYC_HoVaTen" not in d
    assert "NYC_QuanHe" not in d
    assert not res["errors"]


def test_trich_luc_compact_prompt_rejects_ui_fields():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Cccd_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND" in system_prompt
    assert "Cccd_NgayCap/Cccd_NoiCap từ mặt sau CCCD" in system_prompt
    assert "Cccd_NoiCap = \"Cục Cảnh sát quản lý hành chính về trật tự xã hội\"" in system_prompt
    assert 'HoTich_LoaiSuKien = "marriage"' in system_prompt
    assert "HoTich_* CHỈ lấy từ tài liệu hộ tịch chính" in system_prompt
    assert "Không trả field quan hệ NYC_QuanHe" in system_prompt
    assert "HoSo_LoaiYeuCau" in system_prompt
    assert "PhuongThucNhanKQ" in system_prompt
    assert "CopyRequest_Quantity=10" in system_prompt
    assert "không trả CapBanSao" in system_prompt
    assert "CopyRequest_WantsCopy" not in {field["name"] for field in FIELDS}
    assert '"Số bộ 123"' in system_prompt
    assert 'BẮT BUỘC đổi Phường 3 thuộc Đà Lạt thành "Phường Xuân Hương"' in system_prompt


@respx.mock
async def test_trich_luc_compact_agent_ignores_direct_ui_values(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    respx.post(settings.ocr_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "..."}}]})
    )
    out = {
        "fields": {
            "NYC_HoVaTen": "UI_SAI",
            "HoSo_LoaiYeuCau": "SAI_DEFAULT",
            "NYC_QuanHe": "Bố Đẻ",
            "Cccd_HoTen": "NGUYỄN VĂN A",
            "Cccd_SoDinhDanh": "012345678901",
            "HoTich_LoaiSuKien": "birth",
            "HoTich_HoTenNguoiDuocDangKy": "TRẦN BÉ",
            "HoTich_NgaySinh": "10/04/2022",
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

    res = await agent.run({"doc": [_file("cccd.jpg"), _file("gks.pdf", "application/pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["HoVaTenC"] == "NGUYỄN VĂN A"
    assert d["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["NDK_HoVaTen"] == "TRẦN BÉ"
    assert d["HoSo_LoaiYeuCau"].startswith("Giấy khai sinh bản sao")
    assert "NYC_QuanHe" not in d
    assert not res["errors"]


@respx.mock
async def test_trich_luc_compact_agent_maps_marriage_extract(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    respx.post(settings.ocr_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "GIẤY CHỨNG NHẬN KẾT HÔN"}}]})
    )
    out = {
        "fields": {
            "Cccd_HoTen": "TRẦN THÀNH CÔNG",
            "Cccd_SoDinhDanh": "025203007360",
            "HoTich_LoaiSuKien": "marriage",
            "HoTich_TenGiayTo": "Giấy chứng nhận kết hôn",
            "HoTich_HoTenNguoiDuocDangKy": "MÃ THỊ SỐ; SUNG A CO",
            "HoTich_NgaySinh": "01/01/1986",
            "HoTich_DanToc": "H'Mông",
            "HoTich_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Đoàn Kết",
                "diaChi": "Tổ dân phố Cư Nhà La",
            },
            "HoTich_LoaiGiayToTuyThan": "Thẻ căn cước công dân",
            "HoTich_SoGiayToTuyThan": "012086005221",
            "HoTich_NgayCapGiayToTuyThan": "06/01/2026",
            "HoTich_NoiCapGiayToTuyThan": "Bộ Công an",
            "HoTich_CoQuanDangKy": "Ủy ban nhân dân phường Đoàn Kết, tỉnh Lai Châu",
            "HoTich_So": "40/2026",
            "HoTich_NgayDangKy": "01/04/2026",
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

    res = await agent.run({"doc": [_file("cccd.pdf", "application/pdf"), _file("ket-hon.jpg")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["HoSo_LoaiYeuCau"] == "Trích lục kết hôn (bản sao)/ Trích lục ghi chú kết hôn (bản sao)"
    assert d["HoSo_TenGiayTo"] == "Giấy chứng nhận kết hôn"
    assert d["HoSo_CoQuanDangKy"] == "Ủy ban nhân dân phường Đoàn Kết, tỉnh Lai Châu"
    assert d["HoSo_So"] == "40/2026"
    assert d["HoSo_NgayCapSo"] == "01/04/2026"
    assert d["PhuongThucNhanKQ"] == "2"
    assert d["NDK_HoVaTen"] == "SUNG A CO"
    assert d["NDK_NgaySinh"] == "01/01/1986"
    assert d["NDK_GioiTinh"] == "Nam"
    assert d["NDK_DanToc"] == "Mông (Hmông)"
    assert d["NDK_SoDinhDanh"] == "012086005221"
    assert d["NDK_LoaiGiayToTuyThan"] == "Căn cước công dân"
    assert d["NDK_SoGiayToTuyThan"] == "012086005221"
    assert d["NDK_NgayCap"] == "06/01/2026"
    assert d["NDK_NoiCap"] == "Bộ Công an"
    assert d["NDK_NoiCuTru"] == "1"
    assert d["NDK_NoiCuTru_TrongNuoc"]["tinh"] == "Lai Châu"
    assert d["NDK_NoiCuTru_TrongNuoc"]["xa"] == "Đoàn Kết"
    assert d["NDK_NoiCuTru_TrongNuoc"]["diaChi"] == "Tổ dân phố Cư Nhà La"
    assert "HoSo_QuyenSo" not in d
    assert not res["errors"]


def test_registry_uses_trich_luc_compact_pipeline():
    assert get_pipeline("trich-luc-ks") is agent.run
