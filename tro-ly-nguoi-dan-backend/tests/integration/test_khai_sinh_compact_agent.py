"""Compact agent đăng ký khai sinh: short LLM output -> Angular UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.khai_sinh_lien_thong import process as agent
from app.pipelines.khai_sinh_lien_thong.process.prompt import EXTRA_RULES
from app.pipelines.khai_sinh_lien_thong.process.schema import FIELDS
from app.procedures.registry import get_pipeline


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")


@respx.mock
async def test_khai_sinh_compact_agent_derives_angular_fields(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
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
    by_name = {f["name"]: f for f in res["fields"]}

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
    assert d["LoaiXacNhanVNeID"] == "2"
    assert d["DkttIsTtBo"] is True
    assert d["DkttIsTtMe"] is False
    assert d["LoaiThanNhanXacNhan"] == "1"
    assert d["LoaiChuSoHuuChoO"] == "1"
    for name in (
        "LoaiXacNhanVNeID",
        "DkttIsTtBo",
        "DkttIsTtMe",
        "LoaiThanNhanXacNhan",
        "LoaiChuSoHuuChoO",
    ):
        assert by_name[name]["default"] is True
    assert not res["errors"]


def test_khai_sinh_compact_prompt_forbids_ui_fields():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Gcs_* lấy từ GIẤY CHỨNG SINH" in system_prompt  # wording lõi mới 2026-08
    assert "CccdNam_* ưu tiên lấy từ giấy tờ CĂN CƯỚC/CMND có giới tính \"Nam\"" in system_prompt
    assert "Không trả field mặc định hoặc field UI" in system_prompt
    assert "Ho, ChaHo, MeHo" in system_prompt


@respx.mock
async def test_khai_sinh_compact_agent_rejects_direct_ui_keys(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
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
