"""Compact agent hỗ trợ mai táng: người chết -> khối chủ hồ sơ, người đứng ra mai táng -> người nộp."""

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
    monkeypatch.setattr(settings, "ocr_cache_enabled", False)


def _mock_services(out):
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "OCR TEXT"}] * 20})
    )
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )


_NGUOI_MAT = {
    "NguoiMat_HoTen": "NGUYỄN VĂN AN",
    "NguoiMat_SoDinhDanh": "012040000111",
    "NguoiMat_NgaySinh": "05/05/1940",
    "NguoiMat_GioiTinh": "Nam",
    "NguoiMat_NgayCap": "01/09/2021",
    "NguoiMat_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "NguoiMat_NoiCuTru": {
        "quocGia": "Việt Nam",
        "tinh": "Lai Châu",
        "xa": "Quyết Tiến",
        "diaChi": "Tổ 3",
    },
}


@respx.mock
async def test_ho_tro_mai_tang_nguoi_chet_la_chu_ho_so_nguoi_mai_tang_la_nguoi_nop(monkeypatch):
    """Người đứng ra mai táng khớp UI → người nộp; khối chủ hồ sơ = người chết, KHÔNG tick tự nộp."""
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            **_NGUOI_MAT,
            "ChuHoSo_HoTen": "TRẦN THỊ BÌNH",
            "ChuHoSo_SoDinhDanh": "025203000222",
            "ChuHoSo_NgaySinh": "11/07/1960",
            "ChuHoSo_GioiTinh": "Nữ",
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
        {"doc": [_file("to khai.pdf", "application/pdf")]},
        {"formContext": {"applicantFullname": "TRẦN THỊ BÌNH",
                         "applicantIdentityNumber": "025203000222"}},
    )
    fields = res["fields"]
    d = {f["name"]: f["value"] for f in fields}

    assert fields[0] == {"name": "data[isOwnerDossierCheck]", "comp": "dom-checkbox", "value": False}
    assert d["data[fullname]"] == "TRẦN THỊ BÌNH"
    assert d["data[identityNumber]"] == "025203000222"
    assert d["data[birthday]"] == "11/07/1960"
    assert d["data[gender]"] == "Nữ"
    assert d["data[province]"] == "Phú Thọ"
    assert d["data[district]"] == "Hoàng Cương"
    assert d["data[address]"] == "Khu 2"

    assert d["data[ownerFullname]"] == "NGUYỄN VĂN AN"
    assert d["data[ownerIdentityNumber]"] == "012040000111"
    assert d["data[ownerBirthday]"] == "05/05/1940"
    assert d["data[ownerGender]"] == "Nam"
    assert d["data[ownerIdentityDate]"] == "01/09/2021"
    assert d["data[ownerIdIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["data[ownerProvince]"] == "Lai Châu"
    assert d["data[ownerDistrict]"] == "Đoàn Kết"  # remap đơn vị hành chính Lai Châu hiện hành
    assert d["data[ownerAddress]"] == "Tổ 3"
    assert d["data[ownerNation]"] == "Việt Nam"
    assert not res["errors"]


@respx.mock
async def test_ho_tro_mai_tang_nguoi_nop_khac_nguoi_mai_tang(monkeypatch):
    """NguoiNop khớp UI (CCCD riêng) thì vào khối người nộp; người đứng ra mai táng không được điền."""
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            **_NGUOI_MAT,
            "NguoiNop_HoTen": "LÊ VĂN CƯỜNG",
            "NguoiNop_SoDinhDanh": "036192000333",
            "NguoiNop_NgaySinh": "17/06/1992",
            "NguoiNop_NoiCuTru": {"tinh": "Ninh Bình", "xa": "Gia Thắng", "diaChi": "Xóm 2"},
            "ChuHoSo_HoTen": "TRẦN THỊ BÌNH",
            "ChuHoSo_SoDinhDanh": "025203000222",
        }
    })

    res = await agent.run(
        {"doc": [_file("cccd.jpg"), _file("to khai.pdf", "application/pdf")]},
        {"formContext": {"applicantFullname": "LÊ VĂN CƯỜNG", "applicantIdentityNumber": "036192000333"}},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[fullname]"] == "LÊ VĂN CƯỜNG"
    assert d["data[identityNumber]"] == "036192000333"
    assert d["data[province]"] == "Ninh Bình"
    assert d["data[ownerFullname]"] == "NGUYỄN VĂN AN"
    assert "TRẦN THỊ BÌNH" not in str(list(d.values()))
    assert not res["errors"]


@respx.mock
async def test_ho_tro_mai_tang_khong_khop_ui_van_dien_nguoi_chet(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            **_NGUOI_MAT,
            "NguoiNop_HoTen": "LÊ VĂN CƯỜNG",
            "NguoiNop_SoDinhDanh": "036192000333",
            "ChuHoSo_HoTen": "TRẦN THỊ BÌNH",
            "ChuHoSo_SoDinhDanh": "025203000222",
        }
    })

    res = await agent.run(
        {"doc": [_file("to khai.pdf", "application/pdf")]},
        {"formContext": {"applicantFullname": "Người Khác", "applicantIdentityNumber": "040203000444"}},
    )

    d = {field["name"]: field["value"] for field in res["fields"]}
    assert d["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in d
    assert d["data[ownerFullname]"] == "NGUYỄN VĂN AN"
    assert "không điền phần người nộp" in res["errors"][0]


@respx.mock
async def test_ho_tro_mai_tang_owner_mode_nguoi_nop_la_nguoi_mai_tang(monkeypatch):
    """Toggle owner_as_submitter: bỏ mỏ neo UI, người nộp = người đứng ra mai táng; người chết vẫn là chủ hồ sơ."""
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            **_NGUOI_MAT,
            "ChuHoSo_HoTen": "TRẦN THỊ BÌNH",
            "ChuHoSo_SoDinhDanh": "025203000222",
        }
    })

    res = await agent.run(
        {"doc": [_file("to khai.pdf", "application/pdf")]},
        {"submitterMode": "owner_as_submitter",
         "formContext": {"applicantFullname": "Cán Bộ Đăng Nhập", "applicantIdentityNumber": "001204000555"}},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[fullname]"] == "TRẦN THỊ BÌNH"
    assert d["data[ownerFullname]"] == "NGUYỄN VĂN AN"
    # Cổng khoá họ tên/CCCD người nộp theo VNeID → mở khoá để ghi người đứng ra mai táng.
    assert all(f.get("enableInput") for f in res["fields"] if f["name"] in ("data[fullname]", "data[identityNumber]"))
    assert not res["errors"]


@respx.mock
async def test_ho_tro_mai_tang_thieu_nguoi_chet_bao_loi(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            "ChuHoSo_HoTen": "TRẦN THỊ BÌNH",
            "ChuHoSo_SoDinhDanh": "025203000222",
        }
    })

    res = await agent.run(
        {"doc": [_file("to khai.pdf", "application/pdf")]},
        {"formContext": {"applicantFullname": "TRẦN THỊ BÌNH", "applicantIdentityNumber": "025203000222"}},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["data[fullname]"] == "TRẦN THỊ BÌNH"
    assert "data[ownerFullname]" not in d
    assert "Không đọc được thông tin người chết" in res["errors"][0]


def test_ho_tro_mai_tang_prompt_keeps_output_compact():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "NguoiMat_*" in system_prompt
    assert "Đây là CHỦ HỒ SƠ trên cổng" in system_prompt
    assert "ChuHoSo_*" in system_prompt
    assert "NguoiNop_*" in system_prompt
    assert "Không tạo Person1_*" in system_prompt
    assert "Mẫu số 03" in system_prompt
    assert "vẫn phải trích NguoiMat_* và ChuHoSo_*" in system_prompt
    assert "data[isOwnerDossierCheck]" in system_prompt
    assert "Không trả field UI như" in system_prompt


def test_registry_uses_ho_tro_mai_tang_process_pipeline():
    proc = get_procedure("ho-tro-mai-tang")

    assert get_pipeline("ho-tro-mai-tang") is agent.run
    assert proc["mode"] == "agent"
    assert proc["label"] == "Hỗ trợ chi phí mai táng cho đối tượng bảo trợ xã hội"
    # Đã chuyển sang mã 1.116910, bỏ mã cũ 1.001731.
    assert proc["detect"]["urlIncludes"] == ["maThuTuc=1.116910", "01a0f66e-63a3-749a-a9d8-2dcbeda6af79"]
    assert proc["detect"]["textIncludes"] == ["Hỗ trợ chi phí mai táng cho đối tượng bảo trợ xã hội"]
    assert proc["roles"] == []
    assert "chủ hồ sơ = NGƯỜI CHẾT" in proc["uploadHint"]


def test_ke_khai_link_ho_tro_mai_tang_dung_ma_1116910():
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    link = next(item for item in KE_KHAI_LINKS if item["key"] == "ho-tro-mai-tang")
    assert link["code"] == "1.116910"
    assert link["url"] == "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/01a0f66e-63a3-749a-a9d8-2dcbeda6af79"


def test_ma_1116910_dung_chung_pipeline_ho_tro_mai_tang():
    proc = get_procedure("ho-tro-mai-tang-1116910")

    assert get_pipeline("ho-tro-mai-tang-1116910") is agent.run
    assert get_attach_pipeline("ho-tro-mai-tang-1116910") is get_attach_pipeline("ho-tro-mai-tang")
    assert proc["label"] == "[Tỉnh Ninh Bình] Hỗ trợ chi phí mai táng cho đối tượng bảo trợ xã hội"
    assert "maThuTuc=1.116910" in proc["detect"]["urlIncludes"]
    # Cùng tên và cùng mã với "ho-tro-mai-tang" → phải kèm mã để thắng khi khớp theo chữ trên trang.
    assert proc["detect"]["textIncludes"] == ["Hỗ trợ chi phí mai táng cho đối tượng bảo trợ xã hội", "1.116910"]
    assert proc["uploadHint"] == get_procedure("ho-tro-mai-tang")["uploadHint"]


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
    assert "Mẫu số 04" in proc["uploadHint"]
