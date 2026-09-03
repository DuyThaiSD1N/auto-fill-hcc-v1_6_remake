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
async def test_khai_tu_compact_agent_derives_ui_fields(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    # Runner mới lọc Gbt_* chống bịa: số/ngày/cơ quan phải CÓ BẰNG CHỨNG trên trang
    # tiêu đề "GIẤY BÁO TỬ" (hoặc đúng mục trên tờ khai) mới được giữ lại.
    gbt_page = (
        "GIẤY BÁO TỬ\n"
        "Số: 12/GBT\n"
        "Cơ quan cấp: Trạm y tế xã Hợp Thành\n"
        "Ngày cấp: 05/06/2026\n"
    )
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": gbt_page}] * 10})
    )
    fields = {
        "Cccd_HoTen": "TRẦN VĂN A",
        "Cccd_SoDinhDanh": "040203015844",
        "Cccd_NgayCap": "2/7/2021",
        "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "Cccd_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Nghệ An",
                          "xa": "Xã Hợp Thành", "diaChi": "Xóm 1"},
        "ToKhai_QuanHeNguoiYeuCau": "Con",
        "NguoiMat_HoTen": "NGUYỄN THỊ B",
        "NguoiMat_NgaySinh": "1950",
        "NguoiMat_GioiTinh": "Nữ",
        "NguoiMat_NoiCuTruCuoiCung": {"quocGia": "Việt Nam", "tinh": "Nghệ An",
                                      "xa": "Phường Vinh", "diaChi": "Số 5"},
        "NguoiMat_NgayMat": "05/06/2026",
        "NguoiMat_GioMat": "06 giờ 38 phút",
        "NguoiMat_NguyenNhanMat": "Tuổi cao sức yếu",
        "Gbt_So": "12/GBT",
        "Gbt_CoQuanCap": "Trạm y tế xã Hợp Thành",
        "Gbt_NgayCap": "05/06/2026",
    }
    # Lượt 1: agent phân vai trả text KHÔNG có tag → context rỗng (fallback luồng cũ);
    # lượt 2: agent trích xuất trả JSON fields.
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        side_effect=[_llm_response("Không xác định được vai."), _fields_response(fields)]
    )

    res = await agent.run({"doc": [_file("cccd truoc.jpg"), _file("cccd sau.jpg"),
                                   _file("giay bao tu.jpg")]}, {})
    d = {f["name"]: f for f in res["fields"]}
    v = {name: f["value"] for name, f in d.items()}

    # Người yêu cầu (không có mỏ neo formContext → tin Cccd_* như cũ).
    assert v["HoVaTenC"] == "TRẦN VĂN A"
    assert v["SoDinhDanhC"] == "040203015844" and v["SoGiayToDinhDanhC"] == "040203015844"
    # Option eForm cổng mới (đối chiếu thongtin/khai tử): "Thẻ căn cước công dân".
    assert v["LoaiGiayToDinhDanhC"] == "Thẻ căn cước công dân"
    assert v["NgayCapDDC"] == "02/07/2021"
    assert v["nycNoiCuTru"] == "1" and v["nycNoiCuTru_TrongNuoc"]["xa"] == "Hợp Thành"
    assert v["QuanHe"] == "Con"

    # Người mất + sự kiện chết.
    assert v["HoTen"] == "NGUYỄN THỊ B"
    assert v["NgaySinh"] == "1950"          # chỉ có năm → điền năm (input trần)
    assert v["GioiTinh"] == "Nữ"
    assert v["nktQuocTich"] == "Việt Nam"
    assert v["nktNoiCuTru"] == "1" and v["nktNoiCuTru_TrongNuoc"]["xa"] == "Vinh"
    assert v["NgayMat"] == "05/06/2026"
    assert v["GioMat"] == "06" and v["PhutMat"] == "38"
    assert v["NguyenNhanMat"] == "Tuổi cao sức yếu"
    # Không có nơi chết trong nguồn → mặc định trong nước, viền vàng.
    assert v["nktNoiChet"] == "1" and d["nktNoiChet"].get("default") is True

    # Giấy báo tử.
    assert v["gbtLoai"] == "Giấy báo tử"
    assert v["gbtSo"] == "12/GBT" and v["gbtNgay"] == "05/06/2026"

    # Loại đăng ký không có trên tờ khai → mặc định "Đăng ký đúng hạn" (viền vàng).
    assert v["loaiDangKy"] == "1" and d["loaiDangKy"].get("default") is True
    assert not res["errors"]


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

    assert get_pipeline("khai-tu") is agent.run
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
