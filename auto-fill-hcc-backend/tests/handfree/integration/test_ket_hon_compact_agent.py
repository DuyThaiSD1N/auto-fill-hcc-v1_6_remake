"""Compact agent đăng ký kết hôn: OCR text -> CccdNam/CccdNu -> legacy UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.ket_hon import process as agent
from app.pipelines.ket_hon.process.prompt import EXTRA_RULES
from app.pipelines.ket_hon.process.schema import FIELDS
from app.channels.handfree.procedure_registry import get_attach_pipeline, get_pipeline, get_procedure
from app.upload_session.classify import classify_text, route_to_slot
from app.upload_session.store import progress


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,QUFB"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")


@respx.mock
async def test_ket_hon_compact_agent_derives_ui_fields(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 10})
    )
    out = {
        "fields": {
            "CccdNam_HoTen": "VŨ ĐÌNH THIẾT",
            "CccdNam_SoDinhDanh": "040203015844",
            "CccdNam_NgaySinh": "26/4/2003",
            "CccdNam_NgayCap": "2/7/2021",
            "CccdNam_NoiCuTru_TrongNuoc": {
                "quocGia": "Việt Nam",
                "tinh": "Nghệ An",
                "diaChi": "Xóm Long Thành",
            },
            "CccdNu_HoTen": "PHẠM NGỌC THỦY",
            "CccdNu_SoDinhDanh": "012193000851",
            "CccdNu_NgaySinh": "20/03/1993",
            "CccdNu_NgayCap": "06/02/2024",
            "CccdNu_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "CccdNu_NoiCuTru_TrongNuoc": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "diaChi": "Tổ 3",
            },
            "HoTenBenNam": "UI_SAI",
            "LoaiTinhTrangHonNhan_BenNam": "Độc thân",
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

    res = await agent.run({"doc": [_file("cccd nam.jpg"), _file("cccd nu.jpg")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["HoTenBenNam"] == "VŨ ĐÌNH THIẾT"
    assert d["SoDinhDanh_BenNam"] == "040203015844"
    assert d["SoGiayToDinhDanh_BenNam"] == "040203015844"
    # Option trên eForm cổng mới: "Thẻ căn cước công dân" (đã fill thật OK trên form kết hôn).
    assert d["LoaiGiayToDinhDanh_BenNam"] == "Thẻ căn cước công dân"
    assert d["NgaySinhBenNam"] == "26/04/2003"
    assert d["NgayCapDD_BenNam"] == "02/07/2021"
    assert d["NoiCapDD_BenNam"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["QuocTichBenNam"] == "Việt Nam"
    assert d["LoaiCuTru_BenNam"] == "Thường trú"
    assert d["NoiCuTru_BenNam"] == "1"
    assert d["NoiCuTru_BenNam_TrongNuoc"]["tinh"] == "Nghệ An"

    assert d["HoTenBenNu"] == "PHẠM NGỌC THỦY"
    assert d["SoDinhDanh_BenNu"] == "012193000851"
    assert d["SoGiayToDinhDanh_BenNu"] == "012193000851"
    assert d["NgayCapDD_BenNu"] == "06/02/2024"
    assert d["NoiCapDD_BenNu"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["QuocTichBenNu"] == "Việt Nam"
    assert d["NoiCuTru_BenNu"] == "1"
    assert d["NoiCuTru_BenNu_TrongNuoc"]["diaChi"] == "Tổ 3"

    # "Độc thân" LLM điền thẳng bị LỌC (không phải field compact hợp lệ); giá trị hiện diện
    # là SUY LUẬN mặc định của mapper (chỉ có CCCD → kết hôn lần đầu), tô vàng.
    assert d["LoaiTinhTrangHonNhan_BenNam"] == "Hiện tại chưa đăng ký kết hôn với ai"
    assert not res["errors"]


def test_ket_hon_compact_prompt_instructs_gender_split():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Nam -> nhóm CccdNam_*" in system_prompt
    assert "Nữ -> nhóm CccdNu_*" in system_prompt
    assert "Không phân biệt nam/nữ theo tên file" in system_prompt
    assert "BẮT BUỘC cố đọc CccdNam_NoiCap/CccdNu_NoiCap" in system_prompt
    assert "Bộ Công an" in system_prompt
    assert "HoTenBenNam" in system_prompt
    assert "Không trả field UI/default" in system_prompt


def test_registry_uses_ket_hon_compact_agent_mode():
    proc = get_procedure("ket-hon")
    docs = {item["key"]: item for item in proc["requiredDocs"]}

    assert get_pipeline("ket-hon") is agent.run
    assert get_attach_pipeline("ket-hon") is not None
    assert proc["flowProfile"] == "tu-phap"
    assert proc["ownerInfo"]["enabled"] is True
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["roles"] == []
    assert "tự phân biệt theo giới tính" in proc["uploadHint"]
    assert proc["hideRepeatableHint"] is True
    assert docs["cccd_nam"]["name"] == "Căn cước công dân bên nam"
    assert docs["cccd_nu"]["name"] == "Căn cước công dân bên nữ"
    assert docs["khac"]["name"] == "Giấy tờ chứng minh tình trạng hôn nhân hoặc giấy tờ khác"
    assert all(item["sides"] == 1 and item.get("repeatable") for item in docs.values())
    assert not docs["cccd_nam"].get("optional") and not docs["cccd_nu"].get("optional")
    assert docs["to_khai"]["optional"] and docs["khac"]["optional"]


def test_ket_hon_repeatable_docs_accept_many_files_without_face_limit():
    docs = get_procedure("ket-hon")["requiredDocs"]
    existing = [
        *({"doc_key": "cccd_nam"} for _ in range(3)),
        *({"doc_key": "cccd_nu"} for _ in range(4)),
        *({"doc_key": "to_khai"} for _ in range(5)),
        *({"doc_key": "khac"} for _ in range(6)),
    ]
    result = progress({
        "procedure_key": "ket-hon",
        "required_docs": docs,
        "files": existing,
        "complete": False,
    })
    counts = {item["key"]: item["receivedCount"] for item in result["docs"]}

    assert result["received"] == result["total"] == 2
    assert counts == {"cccd_nam": 3, "cccd_nu": 4, "to_khai": 5, "khac": 6}
    assert route_to_slot(
        classify_text("CĂN CƯỚC CÔNG DÂN Giới tính: Nam"), docs, existing, None
    )[0] == "cccd_nam"
    assert route_to_slot(
        classify_text("CĂN CƯỚC CÔNG DÂN Giới tính: Nữ"), docs, existing, None
    )[0] == "cccd_nu"
    assert route_to_slot(
        classify_text("TỜ KHAI ĐĂNG KÝ KẾT HÔN"), docs, existing, None
    )[0] == "to_khai"
    assert route_to_slot(
        classify_text("GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN"), docs, existing, None
    )[0] == "khac"
