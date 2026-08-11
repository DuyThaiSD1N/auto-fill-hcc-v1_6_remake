"""Compact agent đăng ký khai tử: OCR text -> compact facts -> legacy UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines.khai_tu import process as agent
from app.pipelines.khai_tu.process.prompt import EXTRA_RULES
from app.pipelines.khai_tu.process import declaration, mapper, reason
from app.pipelines.khai_tu.process.runner import (
    _canonicalize_deceased_fields,
    _requester_hint,
)
from app.pipelines.khai_tu.process.schema import COMPACT_COMP_BY_NAME, FIELDS
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.procedures.registry import get_pipeline, get_procedure
from app.services import ocr


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


async def test_khai_tu_role_context_keeps_both_identity_cards(monkeypatch):
    ocr_docs = [
        {
            "name": "cccd_nguoi_yeu_cau.pdf",
            "provider": "test",
            "text": (
                "CĂN CƯỚC CÔNG DÂN\nHọ và tên: NGUYỄN VĂN MINH\n"
                "Số / No.: 012345678901\nNgày sinh: 10/02/1985"
            ),
        },
        {
            "name": "cccd_nguoi_mat.pdf",
            "provider": "test",
            "text": (
                "CĂN CƯỚC CÔNG DÂN\nHọ và tên: TRẦN THỊ HOA\n"
                "Số / No.: 012345678902\nNgày sinh: 15/06/1950"
            ),
        },
    ]

    async def fake_ocr_per_file(_files):
        return ocr_docs

    calls = []

    async def fake_chat(messages, **_kwargs):
        calls.append(messages)
        if "agent PHÂN VAI" in messages[0]["content"]:
            assert "Tài liệu có dấu hiệu CCCD/CMND: 1, 2." in messages[1]["content"]
            assert "Tài liệu chứa chính xác số định danh người yêu cầu: 1." in messages[1]["content"]
            return (
                "<nguoi_yeu_cau>\n"
                "Họ tên: NGUYỄN VĂN MINH\n"
                "Số CCCD/CMND: 012345678901\n"
                "Ngày sinh: 10/02/1985\n"
                "Ngày cấp giấy tờ: 02/07/2021\n"
                "Nơi cấp giấy tờ: Cục Cảnh sát quản lý hành chính về trật tự xã hội\n"
                "Nguồn: cccd_nguoi_yeu_cau.pdf\n"
                "Căn cứ phân vai: trùng requester_context\n"
                "</nguoi_yeu_cau>\n"
                "<nguoi_mat>\n"
                "Họ tên: TRẦN THỊ HOA\n"
                "Số CCCD/CMND: 012345678902\n"
                "Ngày sinh: 15/06/1950\n"
                "Ngày cấp giấy tờ: 06/02/2024\n"
                "Nơi cấp giấy tờ: Cục Cảnh sát quản lý hành chính về trật tự xã hội\n"
                "Nguồn: cccd_nguoi_mat.pdf\n"
                "Căn cứ phân vai: CCCD còn lại\n"
                "</nguoi_mat>\n"
                "<giay_to_khong_thuoc_hai_vai>\n"
                "Không có\n"
                "</giay_to_khong_thuoc_hai_vai>"
            )
        assert "<phan_vai_da_xac_dinh>" in messages[0]["content"]
        assert "012345678901" in messages[0]["content"]
        assert "012345678902" in messages[0]["content"]
        return json.dumps({
            "fields": {
                "Cccd_HoTen": "NGUYỄN VĂN MINH",
                "Cccd_SoDinhDanh": "012345678901",
                "NguoiMat_HoTen": "TRẦN THỊ HOA",
                "NguoiMat_SoDinhDanh": "012345678902",
                "NguoiMat_NgayCapGiayTo": "06/02/2024",
                "NguoiMat_NoiCapGiayTo": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            }
        }, ensure_ascii=False)

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr("app.services.llm.client.chat", fake_chat)
    monkeypatch.setattr("app.services.llm.client.chat_text", fake_chat)

    res = await agent.run(
        {"doc": [_file("cccd_nguoi_yeu_cau.pdf"), _file("cccd_nguoi_mat.pdf")]},
        {
            "formContext": {
                "applicantFullname": "NGUYỄN VĂN MINH",
                "applicantIdentityNumber": "012345678901",
            }
        },
    )
    values = {field["name"]: field["value"] for field in res["fields"]}

    assert len(calls) == 2
    assert values["SoDinhDanhC"] == "012345678901"
    assert values["SoDinhDanh"] == "012345678902"
    assert values["NgayCapDD"] == "06/02/2024"
    assert values["NoiCapDD"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert "012345678902" in res["reasoning_context"]
    assert "Ngày cấp giấy tờ: 06/02/2024" in res["reasoning_context"]
    assert "<giay_to_khong_thuoc_hai_vai>" in res["reasoning_context"]


async def test_khai_tu_rejects_unrelated_identity_card_after_role_analysis(
    monkeypatch,
):
    ocr_docs = [{
        "name": "khai_tu_nguoi_mat_lau_nam.pdf",
        "provider": "test",
        "text": (
            "Tiếp nhận yêu cầu đăng ký khai tử cho ông LÊ KHIỀN, "
            "sinh năm 1921, chết năm 1982.\n"
            "CĂN CƯỚC CÔNG DÂN\n"
            "Họ và tên: LÊ VĂN TRUNG\n"
            "Số / No.: 068063001858\n"
            "Ngày, tháng, năm: 27/12/2021"
        ),
    }]

    async def fake_ocr_per_file(_files):
        return ocr_docs

    calls = []

    async def fake_chat(messages, **_kwargs):
        calls.append(messages)
        if "agent PHÂN VAI" in messages[0]["content"]:
            return (
                "<nguoi_yeu_cau>\n"
                "Họ tên: VŨ ĐÌNH THIẾT\n"
                "Số CCCD/CMND: 040203015844\n"
                "Nguồn: requester_context\n"
                "</nguoi_yeu_cau>\n"
                "<nguoi_mat>\n"
                "Họ tên: LÊ KHIỀN\n"
                "Số CCCD/CMND: Không xác định\n"
                "Ngày sinh: 1921\n"
                "Nguồn: công văn đăng ký khai tử\n"
                "</nguoi_mat>\n"
                "<giay_to_khong_thuoc_hai_vai>\n"
                "- LÊ VĂN TRUNG — 068063001858 — không khớp hai vai\n"
                "</giay_to_khong_thuoc_hai_vai>"
            )
        assert "068063001858" in messages[0]["content"]
        assert "đều bị loại" in messages[0]["content"]
        return json.dumps({
            "fields": {
                "NguoiMat_HoTen": "LÊ KHIỀN",
                "NguoiMat_NgaySinh": "1921",
                "NguoiMat_NgayMat": "1982",
                # Mô phỏng đúng lỗi live: final agent vẫn cố gán thẻ người thứ ba.
                "Cccd_HoTen": "LÊ VĂN TRUNG",
                "Cccd_SoDinhDanh": "068063001858",
                "Cccd_NgayCap": "27/12/2021",
                "NguoiMat_SoDinhDanh": "068063001858",
                "NguoiMat_NgayCapGiayTo": "27/12/2021",
                "NguoiMat_NoiCapGiayTo": (
                    "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
                ),
            }
        }, ensure_ascii=False)

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr("app.services.llm.client.chat", fake_chat)
    monkeypatch.setattr("app.services.llm.client.chat_text", fake_chat)

    res = await agent.run(
        {"doc": [_file("khai_tu_nguoi_mat_lau_nam.pdf")]},
        {
            "formContext": {
                "applicantFullname": "VŨ ĐÌNH THIẾT",
                "applicantIdentityNumber": "040203015844",
            }
        },
    )
    values = {field["name"]: field["value"] for field in res["fields"]}

    assert len(calls) == 2
    assert values["HoTen"] == "LÊ KHIỀN"
    assert values["NgaySinh"] == "1921"
    assert values["NgayMat"] == "1982"
    assert "SoDinhDanh" not in values
    assert "SoGiayToDinhDanh" not in values
    assert "NgayCapDD" not in values
    assert "NoiCapDD" not in values
    assert "HoVaTenC" not in values
    assert "SoDinhDanhC" not in values
    assert "LÊ VĂN TRUNG" in res["reasoning_context"]


def test_khai_tu_role_context_rejects_wrong_requester_anchor():
    raw = (
        "<nguoi_yeu_cau>\n"
        "Họ tên: NGƯỜI KHÁC\nSố CCCD/CMND: 999999999999\n"
        "</nguoi_yeu_cau>\n"
        "<nguoi_mat>\nHọ tên: NGƯỜI MẤT\n</nguoi_mat>"
    )

    context = reason._render_context(
        raw,
        {
            "formContext": {
                "applicantFullname": "NGƯỜI YÊU CẦU",
                "applicantIdentityNumber": "012345678901",
            }
        },
    )

    assert context == ""


def test_khai_tu_role_prompt_prioritizes_exactly_two_identity_cards():
    prompt = reason._ROLE_PROMPT

    exact_two = prompt.index("CASE ĐÚNG 2 CCCD/CMND")
    unrelated = prompt.index("Chỉ khi không thuộc case đúng 2 thẻ")
    assert exact_two < unrelated
    assert "BẮT BUỘC gán thẻ khớp" in prompt
    assert "thẻ còn lại cho người chết" in prompt
    assert "Không cần thêm tờ khai/giấy báo tử" in prompt
    assert "CCCD/CMND chỉ được gán cho một vai khi" not in prompt


@respx.mock
async def test_khai_tu_compact_agent_derives_ui_fields(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")

    async def fake_ocr_per_file(files):
        results = []
        for f in files:
            if "giay bao tu" in (f.get("name") or "").lower():
                text = (
                    "BỆNH VIỆN ĐA KHOA TỈNH LAI CHÂU\n"
                    "Số: GBT.01929\n"
                    "GIẤY BÁO TỬ\n"
                    "Lai Châu, ngày 05 tháng 02 năm 2026"
                )
            else:
                text = "CĂN CƯỚC CÔNG DÂN"
            results.append({"name": f.get("name"), "text": text, "provider": "test"})
        return results

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
            "NguoiMat_HoTen": "ĐÈO THẾ SỐP",
            "NguoiMat_NgaySinh": "10/04/1940",
            "NguoiMat_GioiTinh": "Nam",
            "NguoiMat_DanToc": "Thái",
            "NguoiMat_SoDinhDanh": "012040000001",
            "NguoiMat_NoiCuTruCuoiCung": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "diaChi": "Bản Nậm Hàng",
            },
            "NguoiMat_NgayMat": "4/2/2026",
            "NguoiMat_GioMat": "6 giờ 38 phút",
            "NguoiMat_NguyenNhanMat": "Suy hô hấp",
            "NguoiMat_NoiChet": {
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
            "ToKhai_LoaiDangKy": "Đăng ký quá hạn",
            "NguoiMat_HoTen": "LIỀU THỊ BỘ",
            "NguoiMat_NgaySinh": "15/03/1985",
            "NguoiMat_GioiTinh": "Nữ",
            "NguoiMat_DanToc": "Mông",
            "NguoiMat_QuocTich": "Việt Nam",
            "NguoiMat_SoDinhDanh": "012131081609",
            "NguoiMat_NgayCapGiayTo": "23/09/2022",
            "NguoiMat_NoiCapGiayTo": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "NguoiMat_NoiCuTruCuoiCung": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "diaChi": "Tổ dân phố Cư Nhà La",
            },
            "NguoiMat_NgayMat": "12/06/2026",
            "NguoiMat_NguyenNhanMat": "Bệnh già",
            "NguoiMat_NoiChet": {
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
    assert d["loaiDangKy"] == "4"
    assert d["HoTen"] == "LIỀU THỊ BỘ"
    assert d["NgaySinh"] == "15/03/1985"
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
        {"name": "NguoiMat_HoTen", "value": "NGUYỄN THỊ ĐIỂM"},
        {"name": "CopyRequest_Quantity", "value": "03 bản"},
    ]
    d = {f["name"]: f["value"] for f in mapper.enrich(fields)}

    assert d["CapBanSao"] == "Có"
    assert d["SoLuong"] == "3"


def test_khai_tu_mapper_does_not_default_copy_request_when_source_is_blank():
    from app.pipelines.khai_tu.process import mapper

    fields = [{"name": "NguoiMat_HoTen", "value": "NGƯỜI MẤT"}]
    d = {f["name"]: f["value"] for f in mapper.enrich(fields)}

    assert "CapBanSao" not in d
    assert "SoLuong" not in d


def test_khai_tu_mapper_maps_registration_type_and_defaults_when_missing():
    from app.pipelines.khai_tu.process import mapper

    cases = (
        ("Đăng ký đúng hạn", "1"),
        ("Đăng ký quá hạn", "4"),
        ("Đăng ký khai tử cho người chết đã lâu", "5"),
    )
    for source, expected in cases:
        fields = [{"name": "ToKhai_LoaiDangKy", "value": source}]
        mapped = {field["name"]: field for field in mapper.enrich(fields)}
        assert mapped["loaiDangKy"]["value"] == expected
        assert "default" not in mapped["loaiDangKy"]

    mapped = {field["name"]: field for field in mapper.enrich([])}
    assert mapped["loaiDangKy"]["value"] == "1"
    assert mapped["loaiDangKy"]["default"] is True


def test_khai_tu_mapper_preserves_deceased_ethnicity_and_selected_residence_source():
    from app.pipelines.khai_tu.process import mapper

    fields = [
        {"name": "NguoiMat_HoTen", "value": "LÒ VĂN MINH"},
        {"name": "NguoiMat_DanToc", "value": "Thái"},
        {
            "name": "NguoiMat_NoiCuTruCuoiCung",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Điện Biên",
                "xa": "Thanh Nưa",
                "diaChi": "Số 12, bản Nà Púng",
            },
        },
    ]
    d = {f["name"]: f["value"] for f in mapper.enrich(fields)}

    assert d["nktDanToc"] == "Thái"
    assert d["nktNoiCuTru_TrongNuoc"] == {
        "quocGia": "Việt Nam",
        "tinh": "Điện Biên",
        "xa": "Thanh Nưa",
        "diaChi": "Số 12, bản Nà Púng",
    }
    assert "CapBanSao" not in d


def test_khai_tu_mapper_preserves_provincial_police_issuer_for_cmnd():
    from app.pipelines.khai_tu.process import mapper

    fields = [
        {"name": "NguoiMat_HoTen", "value": "NGƯỜI MẤT"},
        {"name": "NguoiMat_SoDinhDanh", "value": "123456789"},
        {"name": "NguoiMat_NgayCapGiayTo", "value": "04/03/2016"},
        {"name": "NguoiMat_NoiCapGiayTo", "value": "Công an tỉnh Cao Bằng"},
    ]
    d = {f["name"]: f["value"] for f in mapper.enrich(fields)}

    assert d["LoaiGiayToDinhDanh"] == "Chứng minh nhân dân"
    assert d["NoiCapDD"] == "Công an tỉnh Cao Bằng"


def test_khai_tu_mapper_does_not_use_death_notice_issuer_as_death_place():
    from app.pipelines.khai_tu.process import mapper

    fields = [
        {"name": "NguoiMat_HoTen", "value": "NGƯỜI MẤT"},
        {"name": "Gbt_CoQuanCap", "value": "UBND xã MINH TÂN"},
    ]
    d = {f["name"]: f["value"] for f in mapper.enrich(fields)}

    assert d["gbtCoQuanCap"] == "UBND xã MINH TÂN"
    assert d["nktNoiChet"] == "1"
    assert d["nktNoiChet_TrongNuoc"] == {"quocGia": "Việt Nam"}


def test_khai_tu_compact_prompt_instructs_source_split():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "<task_contract>" in system_prompt
    assert "<execution_order>" in system_prompt
    assert "<document_inventory>" in system_prompt
    assert "<role_routing>" in system_prompt
    assert "<source_authority>" in system_prompt
    assert "<verification_loop>" in system_prompt
    assert "Cccd_* chỉ lấy giấy tờ người yêu cầu" in system_prompt
    assert "đúng 2 CCCD và đúng 1 thẻ" in system_prompt
    assert "thẻ còn lại là người chết" in system_prompt
    assert "Giữ nguyên cụm họ tên, số giấy tờ" in system_prompt
    assert "mục \"Nơi cư trú cuối cùng\" trong paper_declaration" in system_prompt
    assert "\"Nơi thường trú/Place of residence\" trên deceased_identity, chỉ là fallback" in system_prompt
    assert "Không thay nguồn ưu tiên chỉ vì nguồn thấp hơn trình bày rõ" in system_prompt
    assert "CCCD/Căn cước thông thường KHÔNG in dân tộc" in system_prompt
    assert "không làm mất dân tộc đọc rõ từ nguồn ưu tiên" in system_prompt
    assert "CMND ghi \"Công an tỉnh/thành phố ...\" → giữ nguyên" in system_prompt
    assert 'chỉ còn "QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"' in system_prompt
    assert '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"' in system_prompt
    assert "Không lấy chữ ký cuối trang" in system_prompt
    assert "Không diễn giải ô trống thành \"Không\"" in system_prompt
    assert "bỏ cả CopyRequest_WantsCopy và CopyRequest_Quantity" in system_prompt
    assert "Cơ quan/cơ sở cấp giấy báo tử KHÔNG mặc nhiên là nơi chết" in system_prompt
    assert "Ưu tiên địa giới 2 cấp là bước CHUẨN HÓA SAU KHI CHỌN NGUỒN" in system_prompt
    assert "Tờ khai có \"Dân tộc: <giá trị>\"" in system_prompt
    assert "output không có hai CopyRequest_*" in system_prompt
    assert "<source_priority_example>" in system_prompt
    assert "Chọn paper_declaration" in system_prompt
    assert '"tinh":"Minh Sơn","xa":"Bình An"' in system_prompt
    assert "<historical_death_correspondence_case>" in system_prompt
    assert '"đăng ký khai tử ... cho ông/bà <HỌ TÊN>"' in system_prompt
    assert "CCCD không liên quan" in system_prompt
    assert "Nơi an táng/mộ phần không mặc nhiên là nơi chết" in system_prompt
    assert "KHÔNG phải Gbt_So/Gbt_NgayCap/Gbt_CoQuanCap" in system_prompt
    assert 'Không xếp "TRÍCH LỤC KHAI TỬ" vào nhóm này' in system_prompt
    assert "TLKT hoặc TLKT-BS TUYỆT ĐỐI KHÔNG được dùng" in system_prompt
    assert "không xuất vào bất kỳ Gbt_* nào" in system_prompt
    assert "không dùng địa chỉ người yêu cầu, vợ/chồng hoặc chủ hộ khác" in system_prompt
    assert "Không suy giới tính chỉ từ cách xưng hô" in system_prompt


def test_khai_tu_schema_prioritizes_declaration_for_deceased_residence():
    descriptions = {field["name"]: field["desc"] for field in FIELDS}
    residence = descriptions["NguoiMat_NoiCuTruCuoiCung"]
    ethnicity = descriptions["NguoiMat_DanToc"]
    death_place = descriptions["NguoiMat_NoiChet"]

    assert residence.index('mục "Nơi cư trú cuối cùng"') < residence.index("CCCD/CMND người chết")
    assert "Tờ khai đăng ký khai tử" in ethnicity
    assert "Giấy báo tử/giấy chứng tử" in ethnicity
    assert "Không dùng cơ quan cấp giấy báo tử làm nơi chết" in death_place


def test_khai_tu_schema_accepts_historical_death_correspondence():
    descriptions = {field["name"]: field["desc"] for field in FIELDS}

    assert '"đăng ký khai tử ... cho ông/bà <họ tên>"' in descriptions["NguoiMat_HoTen"]
    assert "sinh năm yyyy" in descriptions["NguoiMat_NgaySinh"]
    assert '"chết năm yyyy"' in descriptions["NguoiMat_NgayMat"]
    assert 'không suy từ "ông/bà"' in descriptions["NguoiMat_GioiTinh"]


def test_khai_tu_schema_extracts_registration_type_only_when_declared():
    descriptions = {field["name"]: field["desc"] for field in FIELDS}
    desc = descriptions["ToKhai_LoaiDangKy"]

    assert '"Loại đăng ký"' in desc
    assert '"Đăng ký đúng hạn"' in desc
    assert '"Đăng ký quá hạn"' in desc
    assert '"Đăng ký khai tử cho người chết đã lâu"' in desc
    assert "Nếu tài liệu không ghi thì bỏ field" in desc


def test_khai_tu_schema_keeps_requester_identity_out_of_deceased_fields():
    descriptions = {field["name"]: field["desc"] for field in FIELDS}

    for name in (
        "NguoiMat_SoDinhDanh",
        "NguoiMat_NgayCapGiayTo",
        "NguoiMat_NoiCapGiayTo",
    ):
        assert "người yêu cầu" in descriptions[name]

    assert "BẮT BUỘC" in descriptions["NguoiMat_NgayCapGiayTo"]
    assert "BẮT BUỘC" in descriptions["NguoiMat_NoiCapGiayTo"]
    residence = descriptions["NguoiMat_NoiCuTruCuoiCung"]
    assert "xác nhận trực tiếp thuộc người chết" in residence
    assert "Không dùng địa chỉ người yêu cầu, vợ/chồng hoặc chủ hộ khác" in residence


def test_khai_tu_requester_hint_routes_second_cccd_to_deceased():
    hint = _requester_hint({
        "formContext": {
            "applicantFullname": "NGƯỜI YÊU CẦU",
            "applicantIdentityNumber": "012345678901",
        }
    })

    assert 'họ tên="NGƯỜI YÊU CẦU"' in hint
    assert 'số định danh="012345678901"' in hint
    assert "chỉ là mỏ neo phân vai" in hint
    assert "đúng 2 CCCD" not in hint
    assert "NguoiMat_NoiCuTruCuoiCung" not in hint

    combined_rules = hint + EXTRA_RULES
    assert combined_rules.index("<requester_context>") < combined_rules.index("<role_routing>")
    source_block = combined_rules.index("\n<source_authority>\n")
    assert combined_rules.index("<role_routing>") < source_block
    assert source_block < combined_rules.index("<source_priority_example>")


def test_khai_tu_canonicalizes_legacy_deceased_names_before_validation():
    raw = {
        "Gbt_HoTenNguoiMat": "NGƯỜI MẤT TÊN CŨ",
        "NguoiMat_HoTen": "NGƯỜI MẤT TÊN MỚI",
        "Gbt_NgayMat": "01/02/2026",
        "Gbt_So": "17",
        "Gbt_CoQuanCap": "UBND xã Bình An",
        "Gbt_NgayCap": "02/02/2026",
    }

    canonical = _canonicalize_deceased_fields(raw, [])

    assert canonical["NguoiMat_HoTen"] == "NGƯỜI MẤT TÊN MỚI"
    assert canonical["NguoiMat_NgayMat"] == "01/02/2026"
    assert canonical["Gbt_So"] == "17"
    assert canonical["Gbt_CoQuanCap"] == "UBND xã Bình An"
    assert canonical["Gbt_NgayCap"] == "02/02/2026"
    assert "Gbt_HoTenNguoiMat" not in canonical
    assert "Gbt_NgayMat" not in canonical


def test_khai_tu_drops_death_extract_metadata_when_declaration_reference_is_blank():
    raw = {
        "NguoiMat_HoTen": "NGUYỄN VĂN LƯƠM",
        "Gbt_So": "208",
        "Gbt_CoQuanCap": "UBND phường Xuân Hương - Đà Lạt",
        "Gbt_NgayCap": "25/07/2026",
        "CopyRequest_Quantity": 10,
    }
    documents = [{
        "name": "ho-so-khai-tu.pdf",
        "text": (
            "───── Trang 1/2 ─────\n"
            "TỜ KHAI ĐĂNG KÝ KHAI TỬ\n"
            "Số Giấy báo tử/Giấy tờ thay thế Giấy báo tử: (4)\n"
            "Tôi cam đoan những nội dung khai trên đây là đúng sự thật.\n"
            "Số lượng: 10 bản\n"
            "───── Trang 2/2 ─────\n"
            "UBND PHƯỜNG XUÂN HƯƠNG - ĐÀ LẠT\n"
            "Số: 208/TLKT-BS\n"
            "TRÍCH LỤC KHAI TỬ (BẢN SAO)\n"
            "Xuân Hương, ngày 25 tháng 7 năm 2026\n"
        ),
    }]

    canonical = _canonicalize_deceased_fields(raw, documents)

    assert canonical["NguoiMat_HoTen"] == "NGUYỄN VĂN LƯƠM"
    assert canonical["CopyRequest_Quantity"] == 10
    assert not ({"Gbt_So", "Gbt_CoQuanCap", "Gbt_NgayCap"} & canonical.keys())


def test_khai_tu_keeps_death_notice_reference_from_paper_declaration():
    raw = {
        "Gbt_So": "17/UBND-GBT",
        "Gbt_CoQuanCap": "UBND phường Bình An",
        "Gbt_NgayCap": "26/07/2026",
    }
    documents = [{
        "name": "to-khai.pdf",
        "text": (
            "TỜ KHAI ĐĂNG KÝ KHAI TỬ\n"
            "Số Giấy báo tử/Giấy tờ thay thế Giấy báo tử: (4) 17/UBND-GBT "
            "do U.BND phường Bình An cấp ngày 26 tháng 07 năm 2026\n"
            "Tôi cam đoan những nội dung khai trên đây là đúng sự thật."
        ),
    }]

    canonical = _canonicalize_deceased_fields(raw, documents)

    assert canonical["Gbt_So"] == "17/UBND-GBT"
    assert canonical["Gbt_CoQuanCap"] == "UBND phường Bình An"
    assert canonical["Gbt_NgayCap"] == "26/07/2026"


def test_khai_tu_only_keeps_metadata_supported_by_actual_death_notice():
    correct = {
        "Gbt_So": "41002",
        "Gbt_CoQuanCap": "Bệnh viện Đa khoa Bình Minh",
        "Gbt_NgayCap": "26/07/2026",
    }
    wrong_extract = {
        "Gbt_So": "208",
        "Gbt_CoQuanCap": "UBND phường Xuân Hương",
        "Gbt_NgayCap": "25/07/2026",
    }
    documents = [{
        "name": "giay-bao-tu-va-trich-luc.pdf",
        "text": (
            "───── Trang 1/2 ─────\n"
            "BỆNH VIỆN ĐA KHOA BÌNH MINH\n"
            "Số: 41002-GBT\n"
            "GIẤY BÁO TỬ\n"
            "Bình Minh, ngày 26 tháng 7 năm 2026\n"
            "───── Trang 2/2 ─────\n"
            "UBND PHƯỜNG XUÂN HƯƠNG\n"
            "Số: 208/TLKT-BS\n"
            "TRÍCH LỤC KHAI TỬ\n"
            "Xuân Hương, ngày 25 tháng 7 năm 2026\n"
        ),
    }]

    assert _canonicalize_deceased_fields(correct, documents) == correct
    assert _canonicalize_deceased_fields(wrong_extract, documents) == {}


def test_khai_tu_schema_uses_new_deceased_prefix_and_keeps_death_notice_names():
    names = {field["name"] for field in FIELDS}

    assert {
        "NguoiMat_HoTen",
        "NguoiMat_SoDinhDanh",
        "NguoiMat_NoiCuTruCuoiCung",
        "NguoiMat_NgayMat",
        "NguoiMat_NoiChet",
    } <= names
    assert {"Gbt_So", "Gbt_CoQuanCap", "Gbt_NgayCap"} <= names
    assert not any(
        name.startswith("Gbt_")
        and name not in {"Gbt_So", "Gbt_CoQuanCap", "Gbt_NgayCap"}
        for name in names
    )

    descriptions = {field["name"]: field["desc"] for field in FIELDS}
    assert "TLKT/TLKT-BS tuyệt đối không phải Gbt_So" in descriptions["Gbt_So"]
    assert "Không lấy cơ quan ban hành/ký Trích lục khai tử" in descriptions["Gbt_CoQuanCap"]
    assert "Không lấy ngày lập/cấp/đăng ký của Trích lục khai tử" in descriptions["Gbt_NgayCap"]


_TO_KHAI_OCR = (
    "TỜ KHAI ĐĂNG KÝ KHAI TỬ\n"
    "Kính gửi: (1) UBND XÃ ĐƠN DƯƠNG\n"
    "Họ, chữ đệm, tên người yêu cầu: TRẦN THỊ B "
    "Ngày, tháng, năm sinh: 20/05/1994 "
    "Nơi cư trú: (2) Thôn Số 3 - xã Đơn Dương - Lâm Đồng "
    "Giấy tờ tùy thân: (3) CCCD số 999111222333 "
    "Nơi cấp: Cục trưởng cục cảnh sát QLHC về trật tự xã hội cấp ngày 10/10/2022 "
    "Quan hệ với người đã chết: Em ruột\n"
    "Đề nghị cơ quan đăng ký khai tử cho người có tên dưới đây: "
    "Họ, chữ đệm, tên: NGUYỄN VĂN A "
    "Ngày, tháng, năm sinh: 15/03/1985 "
    "Giới tính: (2) Nam Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam "
    "Nơi cư trú cuối cùng: (2) Số 3 - xã Đơn Dương - Lâm Đồng "
    "Giấy tờ tùy thân: (3) CCCD số 999444555666 "
    "Nơi cấp: Cục trưởng cục cảnh sát QLHC về trật tự xã hội cấp ngày 5/5/2021 "
    "Đã chết vào lúc: 10 giờ 30 phút, ngày 18 tháng 7 năm 2026 "
    "Nơi chết: Thôn Số 3 - xã Đơn Dương - Lâm Đồng "
    "Nguyên nhân chết: Bệnh lý "
    "Số Giấy báo tử/Giấy tờ thay thế Giấy báo tử: (4)\n"
    "Tôi cam đoan những nội dung khai trên đây là đúng sự thật.\n"
)


def test_khai_tu_declaration_reads_deceased_block_deterministically():
    """Mục II của tờ khai đọc được bằng Python, không phụ thuộc agent nhớ đủ field."""
    values = declaration.deceased_fields(_TO_KHAI_OCR)

    assert values["NguoiMat_HoTen"] == "NGUYỄN VĂN A"
    assert values["NguoiMat_NgaySinh"] == "15/03/1985"
    assert values["NguoiMat_GioiTinh"] == "Nam"
    assert values["NguoiMat_DanToc"] == "Kinh"
    assert values["NguoiMat_QuocTich"] == "Việt Nam"
    assert values["NguoiMat_SoDinhDanh"] == "999444555666"
    assert values["NguoiMat_NgayCapGiayTo"] == "05/05/2021"
    assert values["NguoiMat_NoiCapGiayTo"] == (
        "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    )
    assert values["NguoiMat_NgayMat"] == "18/07/2026"
    assert values["NguoiMat_GioMat"] == "10:30"
    assert values["NguoiMat_NguyenNhanMat"] == "Bệnh lý"
    assert values["NguoiMat_NoiCuTruCuoiCung"]["xa"] == "Đơn Dương"
    assert values["NguoiMat_NoiChet"]["xa"] == "Đơn Dương"
    # Không được kéo dữ kiện người yêu cầu (mục I) xuống khối người mất.
    assert "TRẦN THỊ B" not in json.dumps(values, ensure_ascii=False)


def test_khai_tu_fill_missing_backfills_deceased_block_when_agent_skips_it():
    fields = [
        {"name": "NguoiMat_HoTen", "comp": "x-input", "value": "NGUYỄN VĂN A"},
    ]

    filled = declaration.fill_missing(fields, _TO_KHAI_OCR, COMPACT_COMP_BY_NAME)
    values = {field["name"]: field["value"] for field in filled}
    ui = {
        field["name"]: field["value"]
        for field in mapper.enrich(filled, {}, reasoning_context="x")
    }

    assert values["NguoiMat_NgayMat"] == "18/07/2026"
    assert ui["NgayMat"] == "18/07/2026"
    assert ui["GioMat"] == "10"
    assert ui["PhutMat"] == "30"
    assert ui["NguyenNhanMat"] == "Bệnh lý"
    assert ui["nktDanToc"] == "Kinh"
    assert ui["QuanHe"] == "Em ruột"


def test_khai_tu_fill_missing_never_overwrites_agent_values():
    fields = [
        {"name": "NguoiMat_HoTen", "comp": "x-input", "value": "TÊN TỪ GIẤY BÁO TỬ"},
        {"name": "NguoiMat_NgayMat", "comp": "x-date", "value": "19/07/2026"},
    ]

    values = {
        field["name"]: field["value"]
        for field in declaration.fill_missing(fields, _TO_KHAI_OCR, COMPACT_COMP_BY_NAME)
    }

    assert values["NguoiMat_HoTen"] == "TÊN TỪ GIẤY BÁO TỬ"
    assert values["NguoiMat_NgayMat"] == "19/07/2026"


def test_khai_tu_sanitize_corrects_deceased_id_instead_of_dropping_document_block():
    """OCR tờ khai thừa chữ số không được làm mất số định danh/ngày cấp/nơi cấp người mất."""
    context = (
        "<nguoi_yeu_cau>\nHọ tên: TRẦN THỊ B\n"
        "Số CCCD/CMND: 999111222333\n</nguoi_yeu_cau>\n"
        "<nguoi_mat>\nHọ tên: NGUYỄN VĂN A\n"
        "Số CCCD/CMND: 999444555666\n</nguoi_mat>\n"
        "<giay_to_khong_thuoc_hai_vai>\nKhông có\n</giay_to_khong_thuoc_hai_vai>"
    )
    fields = [
        {"name": "Cccd_SoDinhDanh", "value": "999111222333"},
        {"name": "NguoiMat_SoDinhDanh", "value": "0680911000907"},
        {"name": "NguoiMat_NgayCapGiayTo", "value": "05/05/2021"},
        {"name": "NguoiMat_NoiCapGiayTo", "value": "Cục Cảnh sát QLHC về TTXH"},
    ]

    values = {
        field["name"]: field["value"]
        for field in reason.sanitize_identity_fields(fields, context)
    }

    assert values["NguoiMat_SoDinhDanh"] == "999444555666"
    assert values["NguoiMat_NgayCapGiayTo"] == "05/05/2021"
    assert values["NguoiMat_NoiCapGiayTo"] == "Cục Cảnh sát QLHC về TTXH"
    assert values["Cccd_SoDinhDanh"] == "999111222333"


def test_khai_tu_sanitize_keeps_deceased_document_when_role_agent_has_no_card():
    """Tờ khai không kèm ảnh thẻ người mất -> mỏ neo trống, nhưng số trên tờ khai vẫn đúng."""
    context = (
        "<nguoi_yeu_cau>\nHọ tên: TRẦN THỊ B\n"
        "Số CCCD/CMND: 999111222333\n</nguoi_yeu_cau>\n"
        "<nguoi_mat>\nHọ tên: NGUYỄN VĂN A\n"
        "Số CCCD/CMND: Không xác định\n</nguoi_mat>\n"
        "<giay_to_khong_thuoc_hai_vai>\nKhông có\n</giay_to_khong_thuoc_hai_vai>"
    )
    fields = [
        {"name": "NguoiMat_SoDinhDanh", "value": "999444555666"},
        {"name": "NguoiMat_NgayCapGiayTo", "value": "05/05/2021"},
    ]

    values = {
        field["name"]: field["value"]
        for field in reason.sanitize_identity_fields(fields, context)
    }

    assert values["NguoiMat_SoDinhDanh"] == "999444555666"
    assert values["NguoiMat_NgayCapGiayTo"] == "05/05/2021"


def test_khai_tu_sanitize_still_drops_third_party_card_from_deceased():
    context = (
        "<nguoi_yeu_cau>\nHọ tên: VŨ ĐÌNH THIẾT\n"
        "Số CCCD/CMND: 040203015844\n</nguoi_yeu_cau>\n"
        "<nguoi_mat>\nHọ tên: LÊ KHIỀN\n"
        "Số CCCD/CMND: Không xác định\n</nguoi_mat>\n"
        "<giay_to_khong_thuoc_hai_vai>\n"
        "- LÊ VĂN TRUNG — 068063001858 — không khớp hai vai\n"
        "</giay_to_khong_thuoc_hai_vai>"
    )
    fields = [
        {"name": "NguoiMat_SoDinhDanh", "value": "068063001858"},
        {"name": "NguoiMat_NgayCapGiayTo", "value": "27/12/2021"},
        {"name": "NguoiMat_NoiCapGiayTo", "value": "Cục Cảnh sát QLHC về TTXH"},
        {"name": "Cccd_SoDinhDanh", "value": "068063001858"},
    ]

    names = {
        field["name"] for field in reason.sanitize_identity_fields(fields, context)
    }

    assert names == set()


def _card(name, number, birth):
    return {
        "name": f"cccd_{number}.pdf",
        "provider": "test",
        "text": (
            "CĂN CƯỚC CÔNG DÂN / Citizen Identity Card\n"
            f"Số / No.: {number}\n"
            f"Họ và tên / Full name: {name}\n"
            f"Ngày sinh / Date of birth: {birth}\n"
            "Quốc tịch / Nationality: Việt Nam"
        ),
    }


def _role_block(tag, name, number, birth):
    return (
        f"<{tag}>\nHọ tên: {name}\nSố CCCD/CMND: {number}\n"
        f"Ngày sinh: {birth}\n</{tag}>"
    )


def test_khai_tu_two_cards_only_uses_age_rule_for_role_hint():
    """Chỉ 2 thẻ CCCD, tài khoản cổng không khớp thẻ nào -> người già hơn là người mất."""
    documents = [
        _card("TRẦN THỊ B", "999111222333", "20/05/1994"),
        _card("NGUYỄN VĂN A", "999444555666", "15/03/1985"),
    ]
    options = {
        "formContext": {
            "applicantFullname": "LÊ VĂN C",
            "applicantIdentityNumber": "999777888999",
        }
    }

    assert reason._age_rule_applies(documents, options) is True
    # THỨC sinh 1991, sinh trước DUNG (1994) -> THỨC là người mất.
    assert reason._older_card_number(documents) == "999444555666"

    hint = reason._document_hints(documents, options)
    assert "<quy_tac_tuoi_hai_the>" in hint
    assert "Thẻ số 999444555666 là người SINH TRƯỚC (già hơn) → NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI TỬ." in hint
    assert "Thẻ số 999111222333 là người SINH SAU (trẻ hơn) → NGƯỜI YÊU CẦU." in hint


def test_khai_tu_age_rule_survives_front_and_back_sides_as_separate_files():
    """Mặt trước/mặt sau tải lên thành file riêng vẫn phải gom về đúng 2 người."""
    back_side = {
        "name": "mat_sau.jpg",
        "provider": "test",
        "text": (
            "Đặc điểm nhận dạng / Personal identification: sẹo chấm ngay sơn căn\n"
            "Ngày, tháng, năm / Date, month, year: 10/10/2022\n"
            "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI\n"
            "IDVNM1940051653999111222333<<9\n9404092F3404090VNM<<<<<<<<<<<<2"
        ),
    }
    documents = [
        _card("TRẦN THỊ B", "999111222333", "20/05/1994"),
        back_side,
        _card("NGUYỄN VĂN A", "999444555666", "15/03/1985"),
    ]

    # Dãy MRZ không được đếm thành người thứ ba.
    assert set(reason._card_people(documents)) == {"999111222333", "999444555666"}
    assert reason._age_rule_applies(documents, {}) is True
    assert reason._older_card_number(documents) == "999444555666"


def test_khai_tu_age_rule_swaps_role_blocks_when_agent_inverts_them():
    raw = (
        _role_block("nguoi_yeu_cau", "NGUYỄN VĂN A", "999444555666", "15/03/1985")
        + "\n"
        + _role_block("nguoi_mat", "TRẦN THỊ B", "999111222333", "20/05/1994")
    )

    context = reason._render_context(
        raw,
        {
            "formContext": {
                "applicantFullname": "LÊ VĂN C",
                "applicantIdentityNumber": "999777888999",
            }
        },
        has_declaration=False,
        age_rule=True,
    )

    assert context, "quy tắc tuổi phải giữ lại context dù tài khoản cổng lệch cả hai thẻ"
    assert reason._role_identity_number(context, "nguoi_mat") == "999444555666"
    assert reason._role_identity_number(context, "nguoi_yeu_cau") == "999111222333"
    assert "QUY TẮC TUỔI" in context


def test_khai_tu_age_rule_leaves_correct_role_blocks_untouched():
    raw = (
        _role_block("nguoi_yeu_cau", "TRẦN THỊ B", "999111222333", "20/05/1994")
        + "\n"
        + _role_block("nguoi_mat", "NGUYỄN VĂN A", "999444555666", "15/03/1985")
    )

    context = reason._render_context(raw, {}, has_declaration=False, age_rule=True)

    assert reason._role_identity_number(context, "nguoi_mat") == "999444555666"
    assert reason._role_identity_number(context, "nguoi_yeu_cau") == "999111222333"


def test_khai_tu_age_rule_skipped_when_portal_account_matches_a_card():
    """Cha mẹ già đứng đơn khai tử cho con: tài khoản cổng khớp thẻ thì tuổi không quyết định."""
    documents = [
        _card("NGUYỄN VĂN CHA", "999000111222", "10/03/1955"),
        _card("NGUYỄN VĂN CON", "999333444555", "20/08/1990"),
    ]
    options = {
        "formContext": {
            "applicantFullname": "NGUYỄN VĂN CHA",
            "applicantIdentityNumber": "999000111222",
        }
    }

    assert reason._age_rule_applies(documents, options) is False
    assert "<quy_tac_tuoi_hai_the>" not in reason._document_hints(documents, options)


def test_khai_tu_age_rule_skipped_when_declaration_present():
    documents = [
        _card("TRẦN THỊ B", "999111222333", "20/05/1994"),
        _card("NGUYỄN VĂN A", "999444555666", "15/03/1985"),
        {"name": "to_khai.pdf", "provider": "test", "text": _TO_KHAI_OCR},
    ]

    assert reason._age_rule_applies(documents, {}) is False


def test_khai_tu_enforce_role_assignment_swaps_inverted_card_clusters():
    context = (
        "<nguoi_yeu_cau>\nHọ tên: TRẦN THỊ B\n"
        "Số CCCD/CMND: 999111222333\n</nguoi_yeu_cau>\n"
        "<nguoi_mat>\nHọ tên: NGUYỄN VĂN A\n"
        "Số CCCD/CMND: 999444555666\n</nguoi_mat>"
    )
    fields = [
        {"name": "Cccd_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "Cccd_SoDinhDanh", "value": "999444555666"},
        {"name": "Cccd_NgaySinh", "value": "15/03/1985"},
        {"name": "NguoiMat_HoTen", "value": "TRẦN THỊ B"},
        {"name": "NguoiMat_SoDinhDanh", "value": "999111222333"},
        {"name": "NguoiMat_NgaySinh", "value": "20/05/1994"},
        {"name": "NguoiMat_NgayMat", "value": "18/07/2026"},
    ]

    values = {
        field["name"]: field["value"]
        for field in reason.enforce_role_assignment(fields, context)
    }

    assert values["Cccd_HoTen"] == "TRẦN THỊ B"
    assert values["Cccd_SoDinhDanh"] == "999111222333"
    assert values["NguoiMat_HoTen"] == "NGUYỄN VĂN A"
    assert values["NguoiMat_SoDinhDanh"] == "999444555666"
    assert values["NguoiMat_NgaySinh"] == "15/03/1985"
    # Sự kiện chết không thuộc cặp song ánh nên phải giữ nguyên.
    assert values["NguoiMat_NgayMat"] == "18/07/2026"


def test_khai_tu_enforce_role_assignment_is_noop_when_roles_already_correct():
    context = (
        "<nguoi_yeu_cau>\nSố CCCD/CMND: 999111222333\n</nguoi_yeu_cau>\n"
        "<nguoi_mat>\nSố CCCD/CMND: 999444555666\n</nguoi_mat>"
    )
    fields = [
        {"name": "Cccd_SoDinhDanh", "value": "999111222333"},
        {"name": "NguoiMat_SoDinhDanh", "value": "999444555666"},
    ]

    assert reason.enforce_role_assignment(fields, context) == fields


async def test_khai_tu_two_cards_only_maps_older_person_as_deceased(monkeypatch):
    """End-to-end: 2 CCCD, tài khoản cổng là người thứ ba -> người già hơn vào mục II."""
    ocr_docs = [
        _card("TRẦN THỊ B", "999111222333", "20/05/1994"),
        _card("NGUYỄN VĂN A", "999444555666", "15/03/1985"),
    ]

    async def fake_ocr_per_file(_files):
        return ocr_docs

    async def fake_chat(messages, **_kwargs):
        if "agent PHÂN VAI" in messages[0]["content"]:
            assert "<quy_tac_tuoi_hai_the>" in messages[1]["content"]
            # Mô phỏng agent phân vai gán NGƯỢC để kiểm tra lớp chốt tất định.
            return (
                _role_block("nguoi_yeu_cau", "NGUYỄN VĂN A", "999444555666", "15/03/1985")
                + "\n"
                + _role_block("nguoi_mat", "TRẦN THỊ B", "999111222333", "20/05/1994")
                + "\n<giay_to_khong_thuoc_hai_vai>\nKhông có\n</giay_to_khong_thuoc_hai_vai>"
            )
        return json.dumps({
            "fields": {
                "Cccd_HoTen": "TRẦN THỊ B",
                "Cccd_SoDinhDanh": "999111222333",
                "Cccd_NgaySinh": "20/05/1994",
                "NguoiMat_HoTen": "NGUYỄN VĂN A",
                "NguoiMat_SoDinhDanh": "999444555666",
                "NguoiMat_NgaySinh": "15/03/1985",
            }
        }, ensure_ascii=False)

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr("app.services.llm.client.chat", fake_chat)
    monkeypatch.setattr("app.services.llm.client.chat_text", fake_chat)

    res = await agent.run(
        {"doc": [_file("cccd_dung.pdf"), _file("cccd_thuc.pdf")]},
        {
            "formContext": {
                "applicantFullname": "LÊ VĂN C",
                "applicantIdentityNumber": "999777888999",
            }
        },
    )
    values = {field["name"]: field["value"] for field in res["fields"]}

    assert values["HoTen"] == "NGUYỄN VĂN A"
    assert values["SoDinhDanh"] == "999444555666"
    assert values["NgaySinh"] == "15/03/1985"
    assert values["HoVaTenC"] == "TRẦN THỊ B"
    assert values["SoDinhDanhC"] == "999111222333"


def test_registry_uses_khai_tu_compact_agent_mode():
    proc = get_procedure("khai-tu")

    assert get_pipeline("khai-tu") is agent.run
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["roles"] == []
    assert "tự phân biệt theo nội dung OCR" in proc["uploadHint"]
