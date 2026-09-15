"""Compact agent đổi tên nước sạch: OCR text -> CCCD/đơn/GCN facts -> DOM UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.doi_ten_nuoc_sach import process as agent
from app.pipelines.doi_ten_nuoc_sach.process.prompt import EXTRA_RULES
from app.pipelines.doi_ten_nuoc_sach.process.schema import FIELDS
from app.procedures.registry import get_pipeline, get_procedure


def _file(name, typ="application/pdf"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


@respx.mock
async def test_doi_ten_nuoc_sach_compact_agent_derives_dom_fields(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")

    async def fake_ocr_per_file(files):
        text = "\n".join([
            "GIẤY CHỨNG NHẬN",
            "SOAA 00200361",
            "Số vào sổ cấp Giấy chứng nhận: VP.140",
        ])
        return [{"name": f["name"], "type": f["type"], "text": text, "provider": "tiengnoi"} for f in files]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Cccd_HoTen": "TRẦN THANH BÌNH",
            "Cccd_SoDinhDanh": "025085013037",
            "Cccd_NgaySinh": "16/11/1985",
            "Cccd_GioiTinh": "Nam",
            "Cccd_NgayCap": "30/09/2025",
            "Cccd_NoiCap": "BỘ CÔNG AN/MINISTRY OF PUBLIC SECURITY",
            "Cccd_NoiCuTru": {
                "tinh": "Lai Châu",
                "xa": "Sì Lở Lầu",
                "diaChi": "Bản Sì Choang",
                "fullText": "Bản Sì Choang, Sì Lở Lầu, Lai Châu",
            },
            "DonDoiTen_SoDienThoai": "0988.618.366",
            "DonDoiTen_DiaChiThuongTru": "Bản Sì Choang, Sì Lở Lầu, Lai Châu",
            "DonDoiTen_DiaChiHopDong": "SN 363 Trần Hưng Đạo - phường Đoàn Kết - Lai Châu",
            "DonDoiTen_MaKhachHang": "TP03405",
            "DonDoiTen_NguoiDungTenCu": "Nguyễn Chí Công",
            "DonDoiTen_LyDo": "Mua lại nhà",
            "Gcn_SoPhatHanh": "AA 00200361",
            "Gcn_SoVaoSo": "VP.140",
            "Gcn_NgayCap": "25/03/2025",
            "Gcn_CoQuanCap": "VĂN PHÒNG ĐĂNG KÝ ĐẤT ĐAI TỈNH LAI CHÂU - GIÁM ĐỐC",
            "CongDan_soCmnd": "027085013037",
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
        {"doc": [_file("cccd Bình.pdf"), _file("Đơn đổi tên_0001.pdf"), _file("sđ Bình.pdf")]},
        {},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["CongDan_tenCongDan"] == "TRẦN THANH BÌNH"
    assert d["CongDan_ngaySinhCongDan"] == "16/11/1985"
    assert d["CongDan_gioiTinhCongDan"] == "Nam"
    assert d["CongDan_danTocCongDan"] == "Kinh"
    assert d["CongDan_soCmnd"] == "025085013037"
    assert d["CongDan_soCCCD"] == "025085013037"
    assert d["CongDan_ngayCapCmnd"] == "30/09/2025"
    assert d["CongDan_noiCapCmnd"] == "Bộ Công an"
    assert d["CongDan_maTinhThanh"] == "Lai Châu"
    assert d["CongDan_maPhuongXa"] == "Sì Lở Lầu"
    assert d["CongDan_diaChi"] == "Bản Sì Choang"
    assert d["CongDan_diDong"] == "0988618366"
    assert d["CongDan_maDMQuocGia"] == "Việt Nam"
    assert d["CongDan_diaChiNuocNgoai"] == "Việt Nam"
    assert d["CongDan_soGCNGP"] == "AA 00200361"
    assert "VP.140" not in d["CongDan_soGCNGP"]
    assert d["CongDan_ngayCapGCNGP"] == "25/03/2025"
    assert d["CongDan_noiCapGCNGP"] == "VĂN PHÒNG ĐĂNG KÝ ĐẤT ĐAI TỈNH LAI CHÂU"
    assert d["CongDan_noiOHienTai"] == "SN 363 Trần Hưng Đạo - phường Đoàn Kết - Lai Châu"
    assert d["CongDan_diaChiThuongTru"] == "Bản Sì Choang, Sì Lở Lầu, Lai Châu"
    assert next(f for f in res["fields"] if f["name"] == "CongDan_soGCNGP")["aliases"] == ["soGCNGP"]
    assert not res["errors"]


@respx.mock
async def test_doi_ten_nuoc_sach_falls_back_to_ocr_gcn_serial(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    ocr_text = "\n".join([
        "GIẤY CHỨNG NHẬN",
        "QUYỀN SỬ DỤNG ĐẤT",
        "SOAA 00200361",
        "Số vào sổ cấp Giấy chứng nhận: VP.140",
    ])

    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "type": f["type"], "text": ocr_text, "provider": "tiengnoi"} for f in files]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Gcn_SoVaoSo": "VP.140",
            "Gcn_NgayCap": "25/03/2025",
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

    res = await agent.run({"doc": [_file("sđ Bình.pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["CongDan_soGCNGP"] == "AA 00200361"
    assert d["CongDan_ngayCapGCNGP"] == "25/03/2025"
    assert d["CongDan_noiCapGCNGP"] == "Văn phòng đăng ký đất đai tỉnh Lai Châu"
    assert not res["errors"]


@respx.mock
async def test_doi_ten_nuoc_sach_maps_enterprise_fields_without_asset_gcn(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")

    async def fake_ocr_per_file(files):
        text = "\n".join([
            "GIẤY CHỨNG NHẬN",
            "SOAA 00200361",
            "Số vào sổ cấp Giấy chứng nhận: VP.140",
        ])
        return [{"name": f["name"], "type": f["type"], "text": text, "provider": "tiengnoi"} for f in files]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Cccd_HoTen": "NGUYỄN THỊ QUỲNH",
            "Cccd_SoDinhDanh": "011083001513",
            "Cccd_NgaySinh": "07/10/1984",
            "Cccd_GioiTinh": "Nữ",
            "Cccd_NgayCap": "04/05/2024",
            "Cccd_NoiCap": "Cục Cảnh sát QLHC về TTXH",
            "Cccd_QueQuan": {
                "tinh": "Ninh Bình",
                "xa": "Hải Hậu",
                "diaChi": "Hải Anh",
            },
            "Cccd_NoiCuTru": {
                "tinh": "Lai Châu",
                "xa": "Quyết Thắng",
                "diaChi": "Tổ 9",
                "fullText": "Tổ 9, Quyết Thắng, Thành phố Lai Châu, Lai Châu",
            },
            "DonDoiTen_SoDienThoai": "0982213206",
            "DonDoiTen_TenCoQuanToChuc": "CÔNG TY TNHH MTV SX & TM PỜ MA LUNG LAI CHÂU",
            "DonDoiTen_MaSoThue": "6200123497",
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

    res = await agent.run({"doc": [_file("cccd giám đốc.pdf"), _file("giấy đkkd.pdf"), _file("đơn đổi tên.pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["CongDan_tenCongDan"] == "NGUYỄN THỊ QUỲNH"
    assert d["CongDan_tenCoQuanToChuc"] == "CÔNG TY TNHH MTV SX & TM PỜ MA LUNG LAI CHÂU"
    assert d["CongDan_maSoThueNguoiNop"] == "6200123497"
    assert d["CongDan_soCmnd"] == "011083001513"
    assert d["CongDan_maTinhThanh"] == "Ninh Bình"
    assert d["CongDan_maPhuongXa"] == "Hải Hậu"
    assert d["CongDan_diaChi"] == "Hải Anh"
    assert d["CongDan_diDong"] == "0982213206"
    assert d["CongDan_noiOHienTai"] == "Tổ 9, Quyết Thắng, Thành phố Lai Châu, Lai Châu"
    assert "CongDan_soGCNGP" not in d
    assert "CongDan_ngayCapGCNGP" not in d
    assert "CongDan_noiCapGCNGP" not in d
    assert next(f for f in res["fields"] if f["name"] == "CongDan_tenCoQuanToChuc")["aliases"] == ["tenCoQuanToChuc"]
    assert next(f for f in res["fields"] if f["name"] == "CongDan_maSoThueNguoiNop")["aliases"] == ["maSoThueNguoiNop"]
    assert not res["errors"]


@respx.mock
async def test_doi_ten_nuoc_sach_maps_agency_fields_without_gcn(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")

    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "type": f["type"], "text": "...", "provider": "tiengnoi"} for f in files]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Cccd_HoTen": "NGUYỄN TRÍ HÒA",
            "Cccd_SoDinhDanh": "011083001513",
            "Cccd_NgaySinh": "18/09/1983",
            "Cccd_GioiTinh": "Nam",
            "Cccd_NgayCap": "04/05/2024",
            "Cccd_NoiCap": "Cục Cảnh sát QLHC về TTXH",
            "Cccd_QueQuan": {
                "tinh": "Phú Thọ",
                "xa": "Hạ Hòa",
                "diaChi": "Minh Côi",
            },
            "Cccd_NoiCuTru": {
                "fullText": "Tổ 2, Quyết Tiến, TP. Lai Châu, Lai Châu",
            },
            "DonDoiTen_SoDienThoai": "0982213206",
            "DonDoiTen_TenCoQuanToChuc": "Văn Phòng Đảng ủy phường Tân Phong",
            "DonDoiTen_MaSoThue": "6200127685",
            "DonDoiTen_DiaChiHopDong": "Tổ 2, Quyết Tiến, TP. Lai Châu, Lai Châu",
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

    res = await agent.run({"doc": [_file("cccd chánh vp.pdf"), _file("đơn đổi tên cơ quan.pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["CongDan_tenCongDan"] == "NGUYỄN TRÍ HÒA"
    assert d["CongDan_tenCoQuanToChuc"] == "Văn Phòng Đảng ủy phường Tân Phong"
    assert d["CongDan_maSoThueNguoiNop"] == "6200127685"
    assert d["CongDan_maTinhThanh"] == "Phú Thọ"
    assert d["CongDan_maPhuongXa"] == "Hạ Hòa"
    assert d["CongDan_diaChi"] == "Minh Côi"
    assert d["CongDan_noiOHienTai"] == "Tổ 2, Quyết Tiến, TP. Lai Châu, Lai Châu"
    assert d["CongDan_diaChiThuongTru"] == "Tổ 2, Quyết Tiến, TP. Lai Châu, Lai Châu"
    assert "CongDan_soGCNGP" not in d
    assert "CongDan_ngayCapGCNGP" not in d
    assert "CongDan_noiCapGCNGP" not in d
    assert not res["errors"]


def test_doi_ten_nuoc_sach_prompt_locks_sources():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Đơn đổi tên/Giấy ĐKKD chỉ dùng để lấy DonDoiTen_*" in system_prompt
    assert "DonDoiTen_TenCoQuanToChuc" in system_prompt
    assert "DonDoiTen_MaSoThue" in system_prompt
    assert "CCCD thật \"025085013037\" nhưng đơn ghi \"027085013037\"" in system_prompt
    assert "Gcn_SoPhatHanh là SỐ PHÁT HÀNH GCN" in system_prompt
    assert "KHÔNG ghép \"số vào sổ\"" in system_prompt
    assert "Với doanh nghiệp/cơ quan/tổ chức, KHÔNG dùng sổ đỏ/tài sản để điền Gcn_*" in system_prompt


def test_registry_uses_doi_ten_nuoc_sach_compact_agent_mode():
    proc = get_procedure("chuyen-doi-ten-hop-dong-nuoc-sach")

    assert get_pipeline("chuyen-doi-ten-hop-dong-nuoc-sach") is agent.run
    assert proc["label"] == "Thủ tục chuyển đổi tên trong Hợp đồng dịch vụ sử dụng nước sạch"
    assert proc["mode"] == "agent"
    assert proc["roles"] == []
    assert "Đơn xin đổi tên trong hợp đồng dịch vụ cấp nước" in proc["uploadHint"]
