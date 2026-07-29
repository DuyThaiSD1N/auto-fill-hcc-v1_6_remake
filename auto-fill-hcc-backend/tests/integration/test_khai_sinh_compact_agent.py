"""Compact agent đăng ký khai sinh: short LLM output -> Angular UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.khai_sinh_lien_thong import process as agent
from app.pipelines.khai_sinh_lien_thong.process import mapper
from app.pipelines.khai_sinh_lien_thong.process.prompt import EXTRA_RULES
from app.pipelines.khai_sinh_lien_thong.process.schema import FIELDS
from app.pipelines.khai_sinh_dang_ky_lai import process as dang_ky_lai_process
from app.procedures.registry import get_pipeline
from app.services import ocr


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def _fields(values: dict) -> list[dict]:
    return [{"name": name, "value": value} for name, value in values.items()]


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")


async def _fake_ocr_per_file(files):
    return [{"name": f.get("name"), "text": "...", "provider": "test"} for f in files]


@respx.mock
async def test_khai_sinh_compact_agent_derives_angular_fields(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    monkeypatch.setattr(ocr, "ocr_per_file", _fake_ocr_per_file)
    respx.post(settings.ocr_raw_base_url.rstrip("/") + "/api/v1/ocr/raw").mock(
        return_value=httpx.Response(200, json={"fullText": "..."})
    )
    out = {
        "fields": {
            "Gcs_HoTenCon": "VÀNG A PHỈNH",
            "Gcs_NgaySinhCon": "6/5/2025",
            "Gcs_GioiTinhCon": "Nam",
            "Gcs_DanTocCon": "Mông",
            "Gcs_NoiSinh": {
                "tinh": "Lai Châu",
                "diaChi": "Trung tâm y tế huyện Phong Thổ",
            },
            "CccdNam_HoTen": "TRẦN THÀNH CÔNG",
            "CccdNam_SoDinhDanh": "025203007360",
            "CccdNam_NgaySinh": "11/7/2003",
            "CccdNam_QueQuan": {
                "tinh": "Nghệ An",
                "diaChi": "Xóm Long Thành",
            },
            "CccdNam_NoiCuTru": {
                "tinh": "Phú Thọ",
                "diaChi": "Khu 2",
            },
            "CccdNu_HoTen": "PHẠM NGỌC THỦY",
            "CccdNu_SoDinhDanh": "012193000851",
            "CccdNu_NgaySinh": "20/03/1993",
            "CccdNu_NoiCuTru": {
                "tinh": "Lai Châu",
                "diaChi": "Tổ 3",
            },
            "CopyRequest_Quantity": "...3......bản",
            "ChaHo": "SAI_FIELD_UI",
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
        {"doc": [_file("cha.jpg"), _file("me.jpg"), _file("gcs.pdf", "application/pdf")]}, {}
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["Ho"] == "VÀNG"
    assert d["ChuDem"] == "A"
    assert d["Ten"] == "PHỈNH"
    assert d["NgaySinh"] == "06/05/2025"
    assert d["GioiTinh"] == "Nam"
    assert d["MaDanToc"] == "Mông"
    assert d["MaQuocTich"] == "Việt Nam"
    assert d["NsMaQuocGia"] == "Việt Nam"
    assert d["NsDiaChi"]["diaChi"] == "Trung tâm y tế huyện Phong Thổ"

    assert d["ChaHo"] == "TRẦN"
    assert d["ChaChuDem"] == "THÀNH"
    assert d["ChaTen"] == "CÔNG"
    assert d["ChaNgaySinh"] == "11/07/2003"
    assert d["ChaSoGiayTo"] == "025203007360"
    assert d["ChaMaQuocTich"] == "Việt Nam"
    assert d["ChaLoaiCuTru"] == "Thường trú"
    assert d["ChaDiaChi"]["diaChi"] == "Khu 2"
    assert d["QqDiaChi"]["tinh"] == "Nghệ An"
    assert "ChaMaDanToc" not in d

    assert d["MeHo"] == "PHẠM"
    assert d["MeChuDem"] == "NGỌC"
    assert d["MeTen"] == "THỦY"
    assert d["MeSoGiayTo"] == "012193000851"
    assert d["MeMaQuocTich"] == "Việt Nam"
    assert d["MeLoaiCuTru"] == "Thường trú"
    assert d["MeDiaChi"]["diaChi"] == "Tổ 3"
    assert "MeMaDanToc" not in d

    assert d["NycQuanHe"] == {
        "chaCccd": "025203007360",
        "chaTen": "TRẦN THÀNH CÔNG",
        "meCccd": "012193000851",
        "meTen": "PHẠM NGỌC THỦY",
    }
    assert d["CapBanSao"] == "1"
    assert d["BanSaoSoLuong"] == "3"
    assert d["LoaiXacNhanVNeID"] == "2"
    assert d["DkttIsTtBo"] is True
    assert d["DkttMaQuanHe"] == "Con đẻ"
    assert not res["errors"]


def test_khai_sinh_compact_prompt_forbids_ui_fields():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Gcs_* lấy từ GIẤY CHỨNG SINH" in system_prompt
    assert "trẻ CHƯA CÓ TÊN: BỎ HẲN Gcs_HoTenCon" in system_prompt
    assert "Nếu ứng viên trùng tên mẹ thì BỎ Gcs_HoTenCon" in system_prompt
    assert "Tân Phong" not in system_prompt
    assert "CccdNam_* ưu tiên lấy từ giấy tờ CĂN CƯỚC/CMND có giới tính \"Nam\"" in system_prompt
    assert "CopyRequest_Quantity CHỈ lấy từ mục \"Đề nghị cấp bản sao\"" in system_prompt
    assert "TUYỆT ĐỐI không tự mặc định 1" in system_prompt
    assert "Không trả field mặc định hoặc field UI" in system_prompt
    assert "Ho, ChaHo, MeHo" in system_prompt
    assert "BanSaoSoLuong" in system_prompt


def test_mapper_only_emits_copy_quantity_when_present():
    base = {
        "Gcs_HoTenCon": "ĐÀO NGỌC TUỆ KHÍ",
        "Gcs_NgaySinhCon": "17/07/2026",
    }

    without_copy = {field["name"]: field["value"] for field in mapper.enrich(_fields(base))}
    assert "CapBanSao" not in without_copy
    assert "BanSaoSoLuong" not in without_copy

    with_copy = {
        field["name"]: field["value"]
        for field in mapper.enrich(_fields({**base, "CopyRequest_Quantity": "...3......bản"}))
    }
    assert with_copy["CapBanSao"] == "1"
    assert with_copy["BanSaoSoLuong"] == "3"


def test_mapper_rejects_mother_name_as_child_but_keeps_birth_facts():
    out = mapper.enrich(_fields({
        "Gcs_HoTenCon": "PHAN THỊ BÌNH",
        "Gcs_NgaySinhCon": "13/06/2026",
        "Gcs_GioiTinhCon": "Nữ",
        "Gcs_NoiSinh": {
            "tinh": "Lâm Đồng",
            "diaChi": "Bệnh viện Đa khoa tỉnh Lâm Đồng",
        },
        "CccdNu_HoTen": "PHAN THỊ BÌNH",
        "CccdNu_SoDinhDanh": "040194019162",
    }))
    values = {field["name"]: field["value"] for field in out}

    assert "Ho" not in values
    assert "ChuDem" not in values
    assert "Ten" not in values
    assert values["NgaySinh"] == "13/06/2026"
    assert values["GioiTinh"] == "Nữ"
    assert values["NsDiaChi"] == {
        "tinh": "Lâm Đồng",
        "diaChi": "Bệnh viện Đa khoa tỉnh Lâm Đồng",
    }
    assert values["MeHo"] == "PHAN"
    assert values["MeChuDem"] == "THỊ"
    assert values["MeTen"] == "BÌNH"


def test_mapper_rejects_blank_child_name_markers():
    for marker in ("/", "\\", "-", "_", "...", "Chưa đặt tên"):
        values = {
            field["name"]: field["value"]
            for field in mapper.enrich(_fields({
                "Gcs_HoTenCon": marker,
                "Gcs_NgaySinhCon": "13/06/2026",
            }))
        }
        assert "Ho" not in values
        assert "ChuDem" not in values
        assert "Ten" not in values
        assert values["NgaySinh"] == "13/06/2026"


def test_birth_place_known_mapping_stays_deterministic_in_mapper():
    lai_chau = mapper._norm_birth_place({
        "tinh": "Lai Châu",
        "diaChi": "Bệnh viện đa khoa tỉnh",
    })
    lam_dong = mapper._norm_birth_place({
        "tinh": "Lâm Đồng",
        "diaChi": "Bệnh viện Đa khoa tỉnh Lâm Đồng",
    })

    assert lai_chau["xa"] == "Tân Phong"
    assert lam_dong.get("xa") is None


@respx.mock
async def test_khai_sinh_compact_agent_rejects_direct_ui_keys(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    monkeypatch.setattr(ocr, "ocr_per_file", _fake_ocr_per_file)
    respx.post(settings.ocr_raw_base_url.rstrip("/") + "/api/v1/ocr/raw").mock(
        return_value=httpx.Response(200, json={"fullText": "..."})
    )
    out = {
        "fields": {
            "Ho": "TÊN_UI_SAI",
            "ChaHo": "CHA_UI_SAI",
            "MeHo": "MẸ_UI_SAI",
            "Gcs_HoTenCon": "TRẦN ANH QUÂN",
            "Gcs_NgaySinhCon": "10/04/2025",
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

    res = await agent.run({"doc": [_file("gcs.pdf", "application/pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["Ho"] == "TRẦN"
    assert d["ChuDem"] == "ANH"
    assert d["Ten"] == "QUÂN"
    assert d["NgaySinh"] == "10/04/2025"
    assert "ChaHo" not in d
    assert "MeHo" not in d
    assert not res["errors"]


def test_registry_uses_compact_birth_pipelines():
    assert get_pipeline("khai-sinh-dang-ky") is agent.run
    assert get_pipeline("khai-sinh-dang-ky-lai") is dang_ky_lai_process.run
