"""Compact agent hỗ trợ mai táng: CCCD facts -> Form.io requester/owner actions."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.ho_tro_mai_tang import process as agent
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi import process as huu_tri_agent
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.attach import plan as huu_tri_attach
from app.pipelines.ho_tro_mai_tang.process.prompt import EXTRA_RULES
from app.pipelines.ho_tro_mai_tang.process.schema import FIELDS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,QUFB"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "ocr_by_tiengnoi", False)
    monkeypatch.setattr(settings, "ocr_cache_enabled", False)


def _mock_services(out):
    respx.post(settings.ocr_raw_base_url.rstrip("/") + "/api/v1/ocr/raw").mock(
        return_value=httpx.Response(200, json={"fullText": "OCR TEXT"})
    )
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )


@respx.mock
async def test_ho_tro_mai_tang_one_cccd_ticks_owner_first(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            "ChuHoSo_HoTen": "TRẦN THÀNH CÔNG",
            "ChuHoSo_SoDinhDanh": "025203007360",
            "ChuHoSo_NgaySinh": "11/07/2003",
            "ChuHoSo_GioiTinh": "Nam",
            "ChuHoSo_NgayCap": "12/06/2021",
            "ChuHoSo_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "ChuHoSo_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh Phú Thọ",
                "xa": "Xã Hoàng Cương",
                "diaChi": "Khu 2",
            },
            "data[ownerFullname]": "UI_SAI",
        }
    })

    res = await agent.run(
        {"doc": [_file("cccd mat truoc.jpg"), _file("cccd mat sau.jpg")]},
        {"formContext": {"applicantFullname": "TRẦN THÀNH CÔNG",
                         "applicantIdentityNumber": "025203007360"}},
    )
    fields = res["fields"]
    d = {f["name"]: f["value"] for f in fields}

    assert fields[0] == {"name": "data[isOwnerDossierCheck]", "comp": "dom-checkbox", "value": True}
    assert d["data[fullname]"] == "TRẦN THÀNH CÔNG"
    assert d["data[identityNumber]"] == "025203007360"
    assert d["data[birthday]"] == "11/07/2003"
    assert d["data[gender]"] == "Nam"
    assert d["data[identityDate]"] == "12/06/2021"
    assert d["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["data[province]"] == "Phú Thọ"
    assert d["data[district]"] == "Hoàng Cương"
    assert d["data[address]"] == "Khu 2"
    assert d["data[ownerBirthday]"] == "11/07/2003"
    assert "data[ownerFullname]" not in d
    assert not res["errors"]


@respx.mock
async def test_ho_tro_mai_tang_two_cccd_fills_other_person_as_owner(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            "NguoiNop_HoTen": "TRẦN THÀNH CÔNG",
            "NguoiNop_SoDinhDanh": "025203007360",
            "NguoiNop_NgaySinh": "11/07/2003",
            "NguoiNop_GioiTinh": "Nam",
            "NguoiNop_NgayCap": "12/06/2021",
            "NguoiNop_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "NguoiNop_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh Phú Thọ",
                "xa": "Xã Hoàng Cương",
                "diaChi": "Khu 2",
            },
            "ChuHoSo_HoTen": "PHẠM NGỌC THỦY",
            "ChuHoSo_SoDinhDanh": "012193000851",
            "ChuHoSo_NgaySinh": "20/03/1993",
            "ChuHoSo_GioiTinh": "Nữ",
            "ChuHoSo_NgayCap": "06/02/2024",
            "ChuHoSo_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "ChuHoSo_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Quyết Tiến",
                "diaChi": "Tổ 3",
            },
        }
    })

    res = await agent.run(
        {"doc": [_file("cccd 1.jpg"), _file("cccd 2.jpg")]},
        {"formContext": {"applicantFullname": "TRẦN THÀNH CÔNG", "applicantIdentityNumber": "025203007360"}},
    )
    fields = res["fields"]
    d = {f["name"]: f["value"] for f in fields}

    assert fields[0] == {"name": "data[isOwnerDossierCheck]", "comp": "dom-checkbox", "value": False}
    assert d["data[fullname]"] == "TRẦN THÀNH CÔNG"
    assert d["data[identityNumber]"] == "025203007360"
    assert d["data[gender]"] == "Nam"
    assert d["data[identityDate]"] == "12/06/2021"
    assert d["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["data[province]"] == "Phú Thọ"
    assert d["data[district]"] == "Hoàng Cương"
    assert d["data[address]"] == "Khu 2"

    assert d["data[ownerFullname]"] == "PHẠM NGỌC THỦY"
    assert d["data[ownerIdentityNumber]"] == "012193000851"
    assert d["data[ownerBirthday]"] == "20/03/1993"
    assert d["data[ownerGender]"] == "Nữ"
    assert d["data[ownerIdentityDate]"] == "06/02/2024"
    assert d["data[ownerIdIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["data[ownerProvince]"] == "Lai Châu"
    assert d["data[ownerDistrict]"] == "Đoàn Kết"  # remap đơn vị hành chính Lai Châu hiện hành
    assert d["data[ownerAddress]"] == "Tổ 3"
    assert d["data[ownerNation]"] == "Việt Nam"
    assert not res["errors"]


@respx.mock
async def test_ho_tro_mai_tang_two_cccd_requires_form_context_match(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            "NguoiNop_HoTen": "TRẦN THÀNH CÔNG",
            "NguoiNop_SoDinhDanh": "025203007360",
            "ChuHoSo_HoTen": "PHẠM NGỌC THỦY",
            "ChuHoSo_SoDinhDanh": "012193000851",
        }
    })

    res = await agent.run(
        {"doc": [_file("cccd 1.jpg"), _file("cccd 2.jpg")]},
        {"formContext": {"applicantFullname": "Vũ Đình Thiết", "applicantIdentityNumber": "040203015844"}},
    )

    d = {field["name"]: field["value"] for field in res["fields"]}
    assert d["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in d
    assert d["data[ownerFullname]"] == "PHẠM NGỌC THỦY"
    assert "không điền phần người nộp" in res["errors"][0]


@respx.mock
async def test_ho_tro_mai_tang_tokhai_owner_from_form_no_cccd(monkeypatch):
    """CCCD người nộp + tờ khai (chủ hồ sơ khác, không có CCCD chủ hồ sơ):
    chủ hồ sơ lấy TỪ TỜ KHAI, không tích 'người nộp là chủ hồ sơ'."""
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            # CCCD người nộp (khớp UI)
            "NguoiNop_HoTen": "TRẦN THỊ THANH THẢO",
            "NguoiNop_SoDinhDanh": "036192014693",
            "NguoiNop_NgaySinh": "17/06/1992",
            "NguoiNop_GioiTinh": "Nữ",
            "NguoiNop_NgayCap": "17/06/2023",
            "NguoiNop_NoiCap": "Bộ Công an",
            "NguoiNop_NoiCuTru": {"tinh": "Ninh Bình", "xa": "Gia Thắng", "diaChi": "Xóm 2"},
            # Chủ hồ sơ từ tờ khai mục II.2 (không có CCCD)
            "ChuHoSo_HoTen": "Bùi Mạnh Cường",
            "ChuHoSo_NgaySinh": "20/08/1990",
            "ChuHoSo_SoDinhDanh": "001906118210",
            "ChuHoSo_NgayCap": "01/10/2025",
            "ChuHoSo_NoiCap": "Bộ Công an",
            "ChuHoSo_NoiCuTru": {"tinh": "Lai Châu", "xa": "Tân Phong", "diaChi": "Tổ 9"},
        }
    })

    res = await agent.run(
        {"doc": [_file("cccd.jpg"), _file("to khai.pdf", "application/pdf")]},
        {"formContext": {"applicantFullname": "TRẦN THỊ THANH THẢO",
                         "applicantIdentityNumber": "036192014693"}},
    )
    fields = res["fields"]
    d = {f["name"]: f["value"] for f in fields}

    assert fields[0] == {"name": "data[isOwnerDossierCheck]", "comp": "dom-checkbox", "value": False}
    # Người nộp (requester) từ CCCD của chính họ
    assert d["data[fullname]"] == "TRẦN THỊ THANH THẢO"
    assert d["data[identityNumber]"] == "036192014693"
    assert d["data[province]"] == "Ninh Bình"
    # Chủ hồ sơ (owner) từ tờ khai
    assert d["data[ownerFullname]"] == "Bùi Mạnh Cường"
    assert d["data[ownerIdentityNumber]"] == "001906118210"
    assert d["data[ownerBirthday]"] == "20/08/1990"
    assert d["data[ownerIdentityDate]"] == "01/10/2025"
    assert d["data[ownerIdIssuePlace]"] == "Bộ Công an"
    assert d["data[ownerProvince]"] == "Lai Châu"
    assert d["data[ownerDistrict]"] == "Tân Phong"
    assert d["data[ownerAddress]"] == "Tổ 9"
    assert "data[ownerGender]" not in d           # tờ khai không ghi giới tính → để trống
    assert not res["errors"]


@respx.mock
async def test_ho_tro_mai_tang_tokhai_owner_prefers_cccd_identity_tokhai_address(monkeypatch):
    """Có CCCD của chủ hồ sơ: định danh ưu tiên CCCD, địa chỉ ưu tiên tờ khai (2 cấp)."""
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            "NguoiNop_HoTen": "TRẦN THỊ THANH THẢO",
            "NguoiNop_SoDinhDanh": "036192014693",
            # CCCD của chính chủ hồ sơ (địa chỉ CCCD còn cấp cũ)
            "ChuHoSo_HoTen": "BÙI MẠNH CƯỜNG",
            "ChuHoSo_SoDinhDanh": "001906118210",
            "ChuHoSo_NgaySinh": "20/08/1990",
            "ChuHoSo_GioiTinh": "Nam",
            "ChuHoSo_NgayCap": "01/10/2025",
            "ChuHoSo_NoiCap": "Bộ Công an",
            # Tờ khai mục II.2: địa chỉ 2 cấp sáp nhập
            "ChuHoSo_NoiCuTru": {"tinh": "Lai Châu", "xa": "Tân Phong", "diaChi": "Tổ 9"},
        }
    })

    res = await agent.run(
        {"doc": [_file("cccd nop.jpg"), _file("cccd chu.jpg"), _file("to khai.pdf", "application/pdf")]},
        {"formContext": {"applicantFullname": "TRẦN THỊ THANH THẢO",
                         "applicantIdentityNumber": "036192014693"}},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    # Định danh ưu tiên CCCD chủ hồ sơ
    assert d["data[ownerGender]"] == "Nam"
    assert d["data[ownerIdentityNumber]"] == "001906118210"
    # Địa chỉ ưu tiên tờ khai (KHÔNG lấy Điện Biên trên CCCD)
    assert d["data[ownerProvince]"] == "Lai Châu"
    assert d["data[ownerDistrict]"] == "Tân Phong"
    assert d["data[ownerAddress]"] == "Tổ 9"
    assert not res["errors"]


@respx.mock
async def test_ho_tro_mai_tang_tokhai_owner_same_as_requester_ticks_check(monkeypatch):
    """Chủ hồ sơ (tờ khai II.2) trùng người nộp → tích 'người nộp là chủ hồ sơ', điền 1 mục."""
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            "ChuHoSo_HoTen": "TRẦN THỊ THANH THẢO",
            "ChuHoSo_SoDinhDanh": "036192014693",
            "ChuHoSo_NgaySinh": "17/06/1992",
            "ChuHoSo_NgayCap": "17/06/2023",
            "ChuHoSo_NoiCap": "Bộ Công an",
            "ChuHoSo_NoiCuTru": {"tinh": "Ninh Bình", "xa": "Gia Thắng", "diaChi": "Xóm 2"},
        }
    })

    res = await agent.run(
        {"doc": [_file("cccd.jpg"), _file("to khai.pdf", "application/pdf")]},
        {"formContext": {"applicantFullname": "TRẦN THỊ THANH THẢO",
                         "applicantIdentityNumber": "036192014693"}},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert res["fields"][0] == {"name": "data[isOwnerDossierCheck]", "comp": "dom-checkbox", "value": True}
    assert d["data[fullname]"] == "TRẦN THỊ THANH THẢO"
    assert d["data[ownerBirthday]"] == "17/06/1992"
    assert "data[ownerFullname]" not in d
    assert not res["errors"]


def test_ho_tro_mai_tang_prompt_keeps_output_compact():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "ChuHoSo_*" in system_prompt
    assert "NguoiNop_*" in system_prompt
    assert "Không tạo Person1_*" in system_prompt
    assert "TUYỆT ĐỐI KHÔNG lấy người chết" in system_prompt
    assert "vẫn phải trích ChuHoSo_*" in system_prompt
    assert "data[isOwnerDossierCheck]" in system_prompt
    assert "Không trả field UI như" in system_prompt


def test_registry_uses_ho_tro_mai_tang_process_pipeline():
    proc = get_procedure("ho-tro-mai-tang")

    assert get_pipeline("ho-tro-mai-tang") is agent.run
    assert proc["mode"] == "agent"
    assert proc["label"] == "Hỗ trợ chi phí mai táng cho đối tượng bảo trợ xã hội"
    assert proc["detect"]["textIncludes"] == [proc["label"]]
    assert proc["roles"] == []
    assert "người nộp và chủ hồ sơ khác nhau" in proc["uploadHint"]


def test_registry_uses_independent_pipeline_for_ho_tro_mai_tang_huu_tri_xa_hoi():
    proc = get_procedure("ho-tro-mai-tang-huu-tri-xa-hoi")

    assert get_pipeline("ho-tro-mai-tang-huu-tri-xa-hoi") is huu_tri_agent.run
    assert get_pipeline("ho-tro-mai-tang-huu-tri-xa-hoi") is not get_pipeline("ho-tro-mai-tang")
    assert get_attach_pipeline("ho-tro-mai-tang-huu-tri-xa-hoi") is huu_tri_attach
    assert get_attach_pipeline("ho-tro-mai-tang-huu-tri-xa-hoi") is not get_attach_pipeline("ho-tro-mai-tang")
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["label"] == "Hỗ trợ chi phí mai táng đối với đối tượng hưởng trợ cấp hưu trí xã hội"
    assert proc["detect"]["textIncludes"] == [proc["label"]]
    assert proc["roles"] == []
    assert proc["uploadHint"] == get_procedure("ho-tro-mai-tang")["uploadHint"]
