"""Compact agent nước sạch: OCR text -> CCCD/đơn/GCN facts -> DOM UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.cap_nuoc_sach import process as agent
from app.pipelines.cap_nuoc_sach.process.prompt import EXTRA_RULES
from app.pipelines.cap_nuoc_sach.process.schema import FIELDS
from app.procedures.registry import get_pipeline, get_procedure


def _file(name, typ="application/pdf"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


@respx.mock
async def test_cap_nuoc_sach_compact_agent_derives_dom_fields(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")

    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "type": f["type"], "text": "...", "provider": "raw"} for f in files]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Cccd_HoTen": "LÊ THỊ DUNG",
            "Cccd_SoDinhDanh": "010184000972",
            "Cccd_NgaySinh": "03/07/1984",
            "Cccd_GioiTinh": "Nữ",
            "Cccd_DanToc": "Kinh",
            "Cccd_NgayCap": "16/04/2021",
            "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Cccd_QueQuan": {
                "tinh": "Hải Phòng",
                "xa": "Vĩnh Bảo",
                "diaChi": "Trung Lập",
            },
            "Cccd_ThuongTru": {
                "tinh": "Lai Châu",
                "xa": "Đông Phong",
                "diaChi": "Tổ 26",
                "fullText": "Tổ 26, Đông Phong, Thành phố Lai Châu, Lai Châu",
            },
            "Don_SoDienThoai": "0975754384",
            "Don_DiaChiDeNghiCapNuoc": "Đường Lý Tự Trọng, Tổ 26, P. Tân Phong, T. Lai Châu",
            "Gcn_SoPhatHanh": "AA 05565655",
            "Gcn_SoVaoSo": "V.P. 2144",
            "Gcn_NgayCap": "28/04/2026",
            "Gcn_CoQuanCap": "VĂN PHÒNG ĐĂNG KÝ ĐẤT ĐAI TỈNH LAI CHÂU - GIÁM ĐỐC",
            "CongDan_tenCongDan": "Lò Thị Duy",
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
        {"doc": [_file("CCCD LÊ THỊ DUNG.pdf"), _file("Đơn đăng ký_0001.pdf"), _file("sđ Dung_0001.pdf")]},
        {},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["CongDan_tenCongDan"] == "LÊ THỊ DUNG"
    assert d["CongDan_ngaySinhCongDan"] == "03/07/1984"
    assert d["CongDan_gioiTinhCongDan"] == "Nữ"
    assert d["CongDan_danTocCongDan"] == "Kinh"
    assert d["CongDan_soCmnd"] == "010184000972"
    assert d["CongDan_soCCCD"] == "010184000972"
    assert d["CongDan_ngayCapCmnd"] == "16/04/2021"
    assert d["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["CongDan_maTinhThanh"] == "Hải Phòng"
    assert d["CongDan_maPhuongXa"] == "Vĩnh Bảo"
    assert d["CongDan_diaChi"] == "Trung Lập"
    assert d["CongDan_diDong"] == "0975754384"
    assert d["CongDan_maDMQuocGia"] == "Việt Nam"
    assert d["CongDan_diaChiNuocNgoai"] == "Việt Nam"
    assert d["CongDan_soGCNGP"] == "AA 05565655"
    assert "V.P. 2144" not in d["CongDan_soGCNGP"]
    assert d["CongDan_ngayCapGCNGP"] == "28/04/2026"
    assert d["CongDan_noiCapGCNGP"] == "VĂN PHÒNG ĐĂNG KÝ ĐẤT ĐAI TỈNH LAI CHÂU"
    assert d["CongDan_noiOHienTai"] == "Đường Lý Tự Trọng, Tổ 26, P. Tân Phong, T. Lai Châu"
    assert d["CongDan_diaChiThuongTru"] == "Tổ 26, Đông Phong, Thành phố Lai Châu, Lai Châu"
    assert next(f for f in res["fields"] if f["name"] == "CongDan_soGCNGP")["aliases"] == ["soGCNGP"]
    assert not res["errors"]


@respx.mock
async def test_cap_nuoc_sach_falls_back_to_ocr_gcn_serial(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    ocr_text = "\n".join([
        "GIẤY CHỨNG NHẬN",
        "QUYỀN SỬ DỤNG ĐẤT",
        "SOAA 05565655",
        "Số vào sổ cấp Giấy chứng nhận: V.P. 2144",
    ])

    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "type": f["type"], "text": ocr_text, "provider": "raw"} for f in files]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Gcn_SoVaoSo": "V.P. 2144",
            "Gcn_NgayCap": "28/04/2026",
            "Gcn_CoQuanCap": "Văn phòng đăng ký đất đai tỉnh Lai Châu",
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

    res = await agent.run({"doc": [_file("sđ Dung_0001.pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["CongDan_soGCNGP"] == "AA 05565655"
    assert d["CongDan_ngayCapGCNGP"] == "28/04/2026"
    assert d["CongDan_noiCapGCNGP"] == "Văn phòng đăng ký đất đai tỉnh Lai Châu"
    assert not res["errors"]


@respx.mock
async def test_cap_nuoc_sach_maps_enterprise_fields_without_asset_gcn(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    ocr_text = "\n".join([
        "GIẤY CHỨNG NHẬN",
        "QUYỀN SỬ DỤNG ĐẤT",
        "SOAA 05565655",
        "Số vào sổ cấp Giấy chứng nhận: V.P. 2144",
    ])

    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "type": f["type"], "text": ocr_text, "provider": "raw"} for f in files]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Cccd_HoTen": "NGUYỄN THỊ BÍCH PHƯƠNG",
            "Cccd_SoDinhDanh": "012301005867",
            "Cccd_NgaySinh": "03/07/1984",
            "Cccd_GioiTinh": "Nữ",
            "Cccd_DanToc": "Kinh",
            "Cccd_NgayCap": "21/01/2026",
            "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Cccd_QueQuan": {
                "tinh": "Hưng Yên",
                "xa": "Đông Hưng",
                "diaChi": "Minh Tân",
            },
            "Cccd_ThuongTru": {
                "tinh": "Lai Châu",
                "xa": "Thèn Sin",
                "diaChi": "Bản Đông Phong",
                "fullText": "Bản Đông Phong, Thèn Sin, Tam Đường, Lai Châu",
            },
            "Don_SoDienThoai": "0393273913",
            "Don_DiaChiDeNghiCapNuoc": "Bản Đông Phong, Thèn Sin, Tam Đường, Lai Châu",
            "Don_TenCoQuanToChuc": "Công ty CP chè Lai Châu",
            "Don_MaSoThue": "6200120834",
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
        {"doc": [_file("CCCD giám đốc.pdf"), _file("Giấy ĐKKD.pdf"), _file("Đơn đăng ký cấp nước.pdf")]},
        {},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["CongDan_tenCongDan"] == "NGUYỄN THỊ BÍCH PHƯƠNG"
    assert d["CongDan_tenCoQuanToChuc"] == "Công ty CP chè Lai Châu"
    assert d["CongDan_maSoThueNguoiNop"] == "6200120834"
    assert d["CongDan_ngaySinhCongDan"] == "03/07/1984"
    assert d["CongDan_gioiTinhCongDan"] == "Nữ"
    assert d["CongDan_soCmnd"] == "012301005867"
    assert d["CongDan_soCCCD"] == "012301005867"
    assert d["CongDan_ngayCapCmnd"] == "21/01/2026"
    assert d["CongDan_maTinhThanh"] == "Hưng Yên"
    assert d["CongDan_maPhuongXa"] == "Đông Hưng"
    assert d["CongDan_diaChi"] == "Minh Tân"
    assert d["CongDan_diDong"] == "0393273913"
    assert d["CongDan_noiOHienTai"] == "Bản Đông Phong, Thèn Sin, Tam Đường, Lai Châu"
    assert d["CongDan_diaChiThuongTru"] == "Bản Đông Phong, Thèn Sin, Tam Đường, Lai Châu"
    assert "CongDan_soGCNGP" not in d
    assert "CongDan_ngayCapGCNGP" not in d
    assert "CongDan_noiCapGCNGP" not in d
    assert next(f for f in res["fields"] if f["name"] == "CongDan_tenCoQuanToChuc")["aliases"] == ["tenCoQuanToChuc"]
    assert next(f for f in res["fields"] if f["name"] == "CongDan_maSoThueNguoiNop")["aliases"] == ["maSoThueNguoiNop"]
    assert not res["errors"]


def test_cap_nuoc_sach_prompt_locks_sources():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Đơn đăng ký/Giấy ĐKKD chỉ dùng để lấy Don_*" in system_prompt
    assert "Don_TenCoQuanToChuc" in system_prompt
    assert "Don_MaSoThue" in system_prompt
    assert "KHÔNG dùng tên đó để thay Cccd_HoTen" in system_prompt
    assert "Gcn_SoPhatHanh là SỐ PHÁT HÀNH GCN" in system_prompt
    assert "KHÔNG ghép \"số vào sổ\"" in system_prompt
    assert "KHÔNG dùng sổ đỏ/tài sản để điền Gcn_*" in system_prompt


def test_registry_uses_cap_nuoc_sach_compact_agent_mode():
    proc = get_procedure("dang-ky-lap-dat-su-dung-nuoc-sach")

    assert get_pipeline("dang-ky-lap-dat-su-dung-nuoc-sach") is agent.run
    assert proc["label"] == "Thủ tục đăng ký lắp đặt sử dụng nước sạch"
    assert proc["mode"] == "agent"
    assert proc["roles"] == []
    assert "Đơn đăng ký/đơn đề nghị cấp nước sạch" in proc["uploadHint"]
