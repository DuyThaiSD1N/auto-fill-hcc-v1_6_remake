"""Compact agent đăng ký khai tử: OCR text -> Cccd/Gbt facts -> legacy UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines.khai_tu import process as agent
from app.pipelines.khai_tu.process.prompt import EXTRA_RULES
from app.pipelines.khai_tu.process.schema import FIELDS
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.procedures.registry import get_pipeline, get_procedure
from app.services import ocr


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


@respx.mock
async def test_khai_tu_compact_agent_derives_ui_fields(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")

    async def fake_ocr_per_file(files):
        return [{"name": f.get("name"), "text": "...", "provider": "test"} for f in files]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Cccd_HoTen": "VŨ ĐÌNH THIẾT",
            "Cccd_SoDinhDanh": "040203015844",
            "Cccd_NgayCap": "02/07/2021",
            "Cccd_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Nghệ An",
                "diaChi": "Xóm Long Thành",
            },
            "Gbt_HoTenNguoiMat": "ĐÈO THẾ SỐP",
            "Gbt_NgaySinhNguoiMat": "10/04/1940",
            "Gbt_GioiTinhNguoiMat": "Nam",
            "Gbt_DanTocNguoiMat": "Thái",
            "Gbt_SoDinhDanhNguoiMat": "012040000001",
            "Gbt_NoiCuTruNguoiMat": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "diaChi": "Bản Nậm Hàng",
            },
            "Gbt_NgayMat": "4/2/2026",
            "Gbt_GioMat": "6 giờ 38 phút",
            "Gbt_NguyenNhanMat": "Suy hô hấp",
            "Gbt_NoiChet": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "diaChi": "Bệnh viện Đa khoa tỉnh",
            },
            "Gbt_So": "GBT.01929",
            "Gbt_CoQuanCap": "BỆNH VIỆN ĐA KHOA TỈNH LAI CHÂU",
            "Gbt_NgayCap": "05/02/2026",
            "HoTen": "UI_SAI",
            "gbtLoai": "UI_SAI",
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
        {"doc": [_file("cccd nguoi yeu cau.jpg"), _file("giay bao tu.pdf", "application/pdf")]},
        {},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["loaiDangKy"] == "1"
    assert d["HoVaTenC"] == "VŨ ĐÌNH THIẾT"
    assert d["SoDinhDanhC"] == "040203015844"
    assert d["SoGiayToDinhDanhC"] == "040203015844"
    assert d["LoaiGiayToDinhDanhC"] == "Thẻ căn cước công dân"
    assert d["NgayCapDDC"] == "02/07/2021"
    assert d["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["nycLoaiCuTru"] == "Thường trú"
    assert d["nycNoiCuTru"] == "1"
    assert d["nycNoiCuTru_TrongNuoc"]["tinh"] == "Nghệ An"

    assert d["HoTen"] == "ĐÈO THẾ SỐP"
    assert d["NgaySinh"] == "10/04/1940"
    assert d["GioiTinh"] == "Nam"
    assert d["nktDanToc"] == "Thái"
    assert d["nktQuocTich"] == "Việt Nam"
    assert d["SoDinhDanh"] == "012040000001"
    assert d["SoGiayToDinhDanh"] == "012040000001"
    assert d["LoaiGiayToDinhDanh"] == "Thẻ căn cước công dân"
    assert d["nktLoaiCuTru"] == "Thường trú"
    assert d["nktNoiCuTru"] == "1"
    assert d["nktNoiCuTru_TrongNuoc"]["diaChi"] == "Bản Nậm Hàng"

    assert d["NgayMat"] == "04/02/2026"
    assert d["GioMat"] == "06"
    assert d["PhutMat"] == "38"
    assert d["NguyenNhanMat"] == "Suy hô hấp"
    assert d["nktNoiChet"] == "1"
    assert d["nktNoiChet_TrongNuoc"]["tinh"] == "Lai Châu"
    assert d["gbtLoai"] == "Giấy báo tử"
    assert d["gbtSo"] == "GBT.01929"
    assert d["gbtCoQuanCap"] == "BỆNH VIỆN ĐA KHOA TỈNH LAI CHÂU"
    assert d["gbtNgay"] == "05/02/2026"
    assert not res["errors"]


@respx.mock
async def test_khai_tu_compact_agent_accepts_paper_declaration(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")

    async def fake_ocr_per_file(files):
        return [{"name": f.get("name"), "text": "...", "provider": "test"} for f in files]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Cccd_HoTen": "VÀNG A PHỦ",
            "Cccd_SoDinhDanh": "012098002766",
            "Cccd_NgayCap": "17/01/2022",
            "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Cccd_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "diaChi": "Bản Lùng Thàng",
            },
            "ToKhai_QuanHeNguoiYeuCau": "Con",
            "Gbt_HoTenNguoiMat": "LIỀU THỊ BỘ",
            "Gbt_NgaySinhNguoiMat": "01/01/1991",
            "Gbt_GioiTinhNguoiMat": "Nữ",
            "Gbt_DanTocNguoiMat": "Mông",
            "Gbt_QuocTichNguoiMat": "Việt Nam",
            "Gbt_SoDinhDanhNguoiMat": "012131081609",
            "Gbt_NgayCapDDNguoiMat": "23/09/2022",
            "Gbt_NoiCapDDNguoiMat": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Gbt_NoiCuTruNguoiMat": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "diaChi": "Tổ dân phố Cư Nhà La",
            },
            "Gbt_NgayMat": "12/06/2026",
            "Gbt_NguyenNhanMat": "Bệnh già",
            "Gbt_NoiChet": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "diaChi": "Nhà riêng",
            },
            "CopyRequest_WantsCopy": "Có",
            "CopyRequest_Quantity": "03 bản",
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
        {"doc": [_file("VANG_A_PHU_CCCD.pdf", "application/pdf"), _file("VANG_A_PHU_TOKHAI.pdf", "application/pdf")]},
        {},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["HoVaTenC"] == "VÀNG A PHỦ"
    assert d["SoDinhDanhC"] == "012098002766"
    assert d["QuanHe"] == "Con"
    assert d["HoTen"] == "LIỀU THỊ BỘ"
    assert d["NgaySinh"] == "01/01/1991"
    assert d["GioiTinh"] == "Nữ"
    assert d["nktDanToc"] == "Mông"
    assert d["SoDinhDanh"] == "012131081609"
    assert d["NgayMat"] == "12/06/2026"
    assert d["NguyenNhanMat"] == "Bệnh già"
    assert d["nktNoiChet"] == "1"
    assert d["nktNoiChet_TrongNuoc"]["diaChi"] == "Nhà riêng"
    assert d["CapBanSao"] == "Có"
    assert d["SoLuong"] == "3"
    assert "gbtLoai" not in d
    assert "gbtSo" not in d
    assert "gbtCoQuanCap" not in d


def test_khai_tu_mapper_uses_positive_copy_quantity_as_wants_copy():
    from app.pipelines.khai_tu.process import mapper

    fields = [
        {"name": "Gbt_HoTenNguoiMat", "value": "NGUYỄN THỊ ĐIỂM"},
        {"name": "CopyRequest_Quantity", "value": "03 bản"},
    ]
    d = {f["name"]: f["value"] for f in mapper.enrich(fields)}

    assert d["CapBanSao"] == "Có"
    assert d["SoLuong"] == "3"


def test_khai_tu_compact_prompt_instructs_source_split():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Cccd_* CHỈ lấy từ CCCD/CMND của NGƯỜI YÊU CẦU" in system_prompt
    assert "tờ khai đăng ký khai tử bản giấy" in system_prompt
    assert "Gbt_* là nhóm thông tin NGƯỜI ĐƯỢC KHAI TỬ" in system_prompt
    assert "Gbt_NgayMat/Gbt_GioMat: lấy từ cụm \"Đã chết vào lúc\"" in system_prompt
    assert "dòng \"Vào cơ sở KCB lúc\"" in system_prompt
    assert "Cccd_NgayCap/Cccd_NoiCap từ mặt sau CCCD" in system_prompt
    assert "Không lấy chữ ký cuối trang" in system_prompt
    assert "CopyRequest_Quantity = số lượng bản sao dương" in system_prompt
    assert "Không trả field UI/default" in system_prompt


def test_registry_uses_khai_tu_compact_agent_mode():
    proc = get_procedure("khai-tu")

    assert get_pipeline("khai-tu") is agent.run
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["roles"] == []
    assert "tự phân biệt theo nội dung OCR" in proc["uploadHint"]
