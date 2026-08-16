"""Compact agent đăng ký kết hôn: OCR text -> CccdNam/CccdNu -> legacy UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.ket_hon import process as agent
from app.pipelines.ket_hon.process import mapper, runner as ket_hon_runner
from app.pipelines.ket_hon.process.prompt import EXTRA_RULES
from app.pipelines.ket_hon.process.schema import FIELDS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")


@respx.mock
async def test_ket_hon_compact_agent_derives_ui_fields(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_raw_base_url.rstrip("/") + "/api/v1/ocr/raw").mock(
        return_value=httpx.Response(200, json={"fullText": "..."})
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
                "xa": "Xã cũ bên nam",
                "diaChi": "Xóm Long Thành",
            },
            "ToKhaiNam_NoiCuTru_TrongNuoc": {
                "quocGia": "Việt Nam",
                "tinh": "Lâm Đồng",
                "xa": "Phường Xuân Hương",
                "diaChi": "8D Đoàn Thị Điểm",
            },
            "CccdNu_HoTen": "PHẠM NGỌC THỦY",
            "CccdNu_SoDinhDanh": "012193000851",
            "CccdNu_NgaySinh": "20/03/1993",
            "CccdNu_NgayCap": "06/02/2024",
            "CccdNu_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "CccdNu_NoiCuTru_TrongNuoc": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Xã cũ bên nữ",
                "diaChi": "Tổ 3",
            },
            "ToKhaiNu_NoiCuTru_TrongNuoc": {
                "quocGia": "Việt Nam",
                "tinh": "Lâm Đồng",
                "xa": "Xã Đạ Huoai",
                "diaChi": "94 Lê Hồng Phong, Thôn 4",
            },
            # Dấu tick có thể mất trong OCR; số lượng dương vẫn phải suy ra đề nghị cấp bản sao.
            "CopyRequest_Quantity": "02 bản",
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
    assert d["LoaiGiayToDinhDanh_BenNam"] == "Thẻ căn cước công dân"
    assert d["NgaySinhBenNam"] == "26/04/2003"
    assert d["NgayCapDD_BenNam"] == "02/07/2021"
    assert d["NoiCapDD_BenNam"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["QuocTichBenNam"] == "Việt Nam"
    assert d["LoaiCuTru_BenNam"] == "Thường trú"
    assert d["NoiCuTru_BenNam"] == "1"
    assert d["NoiCuTru_BenNam_TrongNuoc"] == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Xuân Hương",
        "diaChi": "8D Đoàn Thị Điểm",
    }

    assert d["HoTenBenNu"] == "PHẠM NGỌC THỦY"
    assert d["SoDinhDanh_BenNu"] == "012193000851"
    assert d["SoGiayToDinhDanh_BenNu"] == "012193000851"
    assert d["NgayCapDD_BenNu"] == "06/02/2024"
    assert d["NoiCapDD_BenNu"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["QuocTichBenNu"] == "Việt Nam"
    assert d["NoiCuTru_BenNu"] == "1"
    assert d["NoiCuTru_BenNu_TrongNuoc"] == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Đạ Huoai",
        "diaChi": "94 Lê Hồng Phong, Thôn 4",
    }
    assert d["CapBanSao"] == "Có"
    assert d["SoLuong"] == "2"

    assert "LoaiTinhTrangHonNhan_BenNam" not in d
    assert not res["errors"]


def test_ket_hon_compact_prompt_instructs_gender_split():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    field_desc = {field["name"]: field["desc"] for field in FIELDS}

    assert "Nam -> nhóm CccdNam_*" in system_prompt
    assert "Nữ -> nhóm CccdNu_*" in system_prompt
    assert "Không phân biệt nam/nữ theo tên file" in system_prompt
    assert "BẮT BUỘC cố đọc CccdNam_NoiCap/CccdNu_NoiCap" in system_prompt
    assert "Bộ Công an" in system_prompt
    assert "HoTenBenNam" in system_prompt
    assert "Không trả field UI/default" in system_prompt
    assert '"TỜ KHAI ĐĂNG KÝ KẾT HÔN"' in system_prompt
    assert "Nếu có số lượng dương thì BẮT BUỘC trả CopyRequest_WantsCopy" in system_prompt
    assert "TUYỆT ĐỐI không mặc định" in system_prompt
    assert "CHỈ lấy từ CCCD/CMND của bên nam" in field_desc["CccdNam_NoiCuTru_TrongNuoc"]
    assert "CHỈ lấy từ CCCD/CMND của bên nữ" in field_desc["CccdNu_NoiCuTru_TrongNuoc"]
    assert "CHỈ lấy từ tờ khai" in field_desc["ToKhaiNam_NoiCuTru_TrongNuoc"]
    assert "CHỈ lấy từ tờ khai" in field_desc["ToKhaiNu_NoiCuTru_TrongNuoc"]
    assert "mapper sẽ tự ưu tiên tờ khai" in system_prompt
    assert "giấy xác nhận tình trạng hôn nhân" in system_prompt
    assert 'nhãn rõ "Xã ..." hoặc "Phường ..."' in system_prompt
    assert "TUYỆT ĐỐI không fuzzy/sửa họ tên để tạo khớp" in system_prompt
    assert 'Cấp tỉnh Hồ Chí Minh luôn trả đúng "Thành phố Hồ Chí Minh"' in system_prompt
    assert 'P9/P.9/P 9 → "Phường 9"' in system_prompt


def test_ket_hon_ethnicity_requires_explicit_labeled_source():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    field_desc = {field["name"]: field["desc"] for field in FIELDS}

    assert 'không xuất hiện nhãn "Dân tộc" → BỎ CẢ HAI field dân tộc' in system_prompt
    assert "không suy đoán dân tộc" in system_prompt
    assert "Dân tộc phổ biến" not in system_prompt
    assert "thiếu nhãn thì bỏ field" in field_desc["CccdNam_DanToc"]
    assert "thiếu nhãn thì bỏ field" in field_desc["CccdNu_DanToc"]

    # Hai CCCD không cung cấp dân tộc: compact output không có field dân tộc thì mapper
    # cũng tuyệt đối không tự tạo giá trị cho form.
    mapped = {
        field["name"]: field["value"]
        for field in mapper.enrich([
            {"name": "CccdNam_HoTen", "value": "NGƯỜI NAM"},
            {"name": "CccdNam_SoDinhDanh", "value": "001001001001"},
            {"name": "CccdNu_HoTen", "value": "NGƯỜI NỮ"},
            {"name": "CccdNu_SoDinhDanh", "value": "002002002002"},
        ])
    }
    assert "DanTocBenNam" not in mapped
    assert "DanTocBenNu" not in mapped


def test_ket_hon_drops_inferred_ethnicity_when_two_cccd_have_no_ethnicity_label():
    hallucinated = {
        "CccdNam_HoTen": "NGƯỜI NAM",
        "CccdNam_DanToc": "DÂN TỘC SUY ĐOÁN",
        "CccdNu_HoTen": "NGƯỜI NỮ",
        "CccdNu_DanToc": "DÂN TỘC SUY ĐOÁN",
    }
    two_identity_cards = [
        {"text": "CĂN CƯỚC - Họ và tên: NGƯỜI NAM - Giới tính: Nam - Nơi cư trú: Bản A"},
        {"text": "CĂN CƯỚC - Họ và tên: NGƯỜI NỮ - Giới tính: Nữ - Nơi cư trú: Bản B"},
    ]

    filtered = ket_hon_runner._compact_field_fallback(hallucinated, two_identity_cards)

    assert filtered["CccdNam_HoTen"] == "NGƯỜI NAM"
    assert filtered["CccdNu_HoTen"] == "NGƯỜI NỮ"
    assert "CccdNam_DanToc" not in filtered
    assert "CccdNu_DanToc" not in filtered


def test_ket_hon_keeps_ethnicity_when_document_has_explicit_label():
    extracted = {"CccdNam_DanToc": "Kinh", "CccdNu_DanToc": "Mông"}
    declaration = [{"text": "TỜ KHAI ĐĂNG KÝ KẾT HÔN\nDân tộc | Kinh | Mông"}]

    assert ket_hon_runner._compact_field_fallback(extracted, declaration) == extracted


def test_ket_hon_does_not_recheck_divorce_status_after_llm():
    extracted = {
        "CccdNu_HoTen": "NGƯỜI NỮ",
        "CccdNu_TinhTrangHonNhan": "3",
        "CccdNam_HoTen": "NGƯỜI NAM",
        "CccdNam_TinhTrangHonNhan": "3",
    }
    documents = [{"text": "QUYẾT ĐỊNH LY HÔN"}]

    assert ket_hon_runner._compact_field_fallback(extracted, documents) == extracted


def test_ket_hon_mapper_normalizes_ho_chi_minh_province_aliases():
    aliases = (
        "TP.Hồ Chí Minh",
        "TP Hồ Chí Minh",
        "TP.HCM",
        "TPHCM",
        "HCM",
        "Hồ Chí Minh",
        "Thành phố Hồ Chí Minh",
    )
    for province in aliases:
        mapped = {field["name"]: field["value"] for field in mapper.enrich([
            {"name": "CccdNam_HoTen", "value": "NGƯỜI NAM"},
            {"name": "CccdNam_SoDinhDanh", "value": "079000000001"},
            {"name": "CccdNam_NoiCuTru_TrongNuoc", "value": {
                "quocGia": "Việt Nam",
                "tinh": province,
                "xa": "P15",
                "diaChi": "92B đường A",
            }},
        ])}
        assert mapped["NoiCuTru_BenNam_TrongNuoc"]["tinh"] == "Thành phố Hồ Chí Minh"
        assert mapped["NoiCuTru_BenNam_TrongNuoc"]["xa"] == "Phường 15"


def test_ket_hon_copy_request_has_no_default_and_quantity_is_positive_signal():
    def mapped(compact_fields):
        return {field["name"]: field["value"] for field in mapper.enrich(compact_fields)}

    assert "CapBanSao" not in mapped([])
    assert mapped([{"name": "CopyRequest_WantsCopy", "value": "Không"}])["CapBanSao"] == "Không"
    with_quantity = mapped([
        {"name": "CopyRequest_WantsCopy", "value": "Không"},
        {"name": "CopyRequest_Quantity", "value": "02 bản"},
    ])
    assert with_quantity["CapBanSao"] == "Có"
    assert with_quantity["SoLuong"] == "2"


def test_registry_uses_ket_hon_compact_agent_mode():
    proc = get_procedure("ket-hon")

    assert get_pipeline("ket-hon") is agent.run
    assert get_attach_pipeline("ket-hon") is not None
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["roles"] == []
    assert "tự phân biệt theo giới tính" in proc["uploadHint"]
