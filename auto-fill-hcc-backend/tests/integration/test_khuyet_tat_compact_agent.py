"""Compact agent xác định mức độ khuyết tật: đơn đề nghị + CCCD -> Form.io fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.khuyet_tat import process as agent
from app.pipelines.khuyet_tat.process import mapper
from app.pipelines.khuyet_tat.process import runner as process_runner
from app.pipelines.khuyet_tat.process.prompt import EXTRA_RULES
from app.pipelines.khuyet_tat.process.schema import CONTEXT_FIELDS, FIELDS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name, typ="application/pdf"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")


def _mapped_values(source_fields, options=None):
    return {
        field["name"]: field["value"]
        for field in mapper.enrich(source_fields, options or {})
    }


def test_khuyet_tat_requester_is_omitted_without_ui_context():
    values = _mapped_values([
        {"name": "ChuHoSo_HoTen", "value": "LẠI NGỌC MINH"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "012084000160"},
    ])

    assert "data[fullname]" not in values
    assert "data[identityNumber]" not in values
    assert values["data[isOwnerDossierCheck]"] is False
    assert values["data[ownerFullname]"] == "LẠI NGỌC MINH"
    assert values["data[ownerIdentityNumber]"] == "012084000160"


def test_khuyet_tat_owner_copy_requires_all_available_ui_anchors_to_match():
    source = [
        {"name": "ChuHoSo_HoTen", "value": "LẠI NGỌC MINH"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "012084000160"},
    ]
    mapped = mapper.enrich(source, {
        "formContext": {
            "applicantFullname": "LẠI NGỌC MINH",
            "applicantIdentityNumber": "012084000160",
        }
    })
    values = {field["name"]: field["value"] for field in mapped}

    assert mapped[0] == {
        "name": "data[isOwnerDossierCheck]",
        "comp": "dom-checkbox",
        "value": True,
    }
    assert values["data[fullname]"] == "LẠI NGỌC MINH"
    assert values["data[identityNumber]"] == "012084000160"
    assert values["data[isOwnerDossierCheck]"] is True
    assert values["data[ownerFullname]"] == "LẠI NGỌC MINH"
    assert values["data[ownerIdentityNumber]"] == "012084000160"

    mismatch = _mapped_values(source, {
        "formContext": {
            "applicantFullname": "NGƯỜI KHÁC",
            "applicantIdentityNumber": "012084000160",
        }
    })
    assert mismatch["data[isOwnerDossierCheck]"] is False
    assert mismatch["data[ownerFullname]"] == "LẠI NGỌC MINH"

    identity_mismatch = _mapped_values(source, {
        "formContext": {
            "applicantFullname": "LẠI NGỌC MINH",
            "applicantIdentityNumber": "999999999999",
        }
    })
    assert identity_mismatch["data[isOwnerDossierCheck]"] is False
    assert identity_mismatch["data[fullname]"] == "LẠI NGỌC MINH"
    assert identity_mismatch["data[identityNumber]"] == "999999999999"
    assert identity_mismatch["data[ownerIdentityNumber]"] == "012084000160"


def test_khuyet_tat_rejects_requester_details_when_ocr_identity_mismatches_ui():
    values = _mapped_values([
        {"name": "NguoiNop_HoTen", "value": "VŨ ĐÌNH THIẾT"},
        {"name": "NguoiNop_SoDinhDanh", "value": "999999999999"},
        {"name": "NguoiNop_NgaySinh", "value": "26/04/2003"},
        {"name": "NguoiNop_GioiTinh", "value": "Nam"},
        {"name": "ChuHoSo_HoTen", "value": "BÙI THỊ YẾN NGỌC"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "051197014913"},
    ], {
        "formContext": {
            "applicantFullname": "VŨ ĐÌNH THIẾT",
            "applicantIdentityNumber": "040203015844",
        }
    })

    # Hai mỏ neo UI vẫn được giữ, nhưng dữ liệu OCR sai người không được bù vào.
    assert values["data[fullname]"] == "VŨ ĐÌNH THIẾT"
    assert values["data[identityNumber]"] == "040203015844"
    assert "data[birthday]" not in values
    assert "data[gender]" not in values


def test_khuyet_tat_unticks_owner_checkbox_when_llm_omits_owner_group():
    """Mẫu số 01 có mục II: chủ hồ sơ suy từ người đại diện, phải bỏ tích ô chủ hồ sơ."""
    values = _mapped_values([
        {"name": "Nkt_HoTen", "value": "HOÀNG THỊ LÀNH"},
        {"name": "Nkt_SoDinhDanh", "value": "010183007970"},
        {"name": "Ndd_HoTen", "value": "HOÀNG THỊ QUỲNH"},
        {"name": "Ndd_SoDinhDanh", "value": "010190008941"},
        {"name": "Ndd_SoDienThoai", "value": "0388.082.382"},
        {"name": "Ndd_NoiCuTru", "value": {
            "tinh": "Lào Cai", "xa": "phường Cam Đường", "diaChi": "Tổ 29",
        }},
    ], {
        "formContext": {
            "applicantFullname": "NGUYỄN DUY THÁI",
            "applicantIdentityNumber": "001204018566",
        }
    })

    assert values["data[isOwnerDossierCheck]"] is False
    assert values["data[ownerFullname]"] == "HOÀNG THỊ QUỲNH"
    assert values["data[ownerIdentityNumber]"] == "010190008941"
    assert values["data[ownerPhoneNumber]"] == "0388082382"
    assert values["data[ownerProvince]"] == "Lào Cai"
    assert values["data[ownerDistrict]"] == "Phường Cam Đường"
    assert values["data[ownerAddress]"] == "Tổ 29"
    # Người khuyết tật ở mục I không bị chủ hồ sơ (người đại diện) ghi đè.
    assert values["data[NktHoTen]"] == "HOÀNG THỊ LÀNH"
    assert values["data[NktSoDinhdanh]"] == "010183007970"


def test_khuyet_tat_owner_falls_back_to_disabled_person_without_representative():
    values = _mapped_values([
        {"name": "Nkt_HoTen", "value": "NGƯỜI KHUYẾT TẬT"},
        {"name": "Nkt_SoDinhDanh", "value": "012345678901"},
        {"name": "Nkt_NgaySinh", "value": "02/02/1990"},
        {"name": "Nkt_GioiTinh", "value": "Nữ"},
    ])

    assert values["data[isOwnerDossierCheck]"] is False
    assert values["data[ownerFullname]"] == "NGƯỜI KHUYẾT TẬT"
    assert values["data[ownerIdentityNumber]"] == "012345678901"
    assert values["data[ownerBirthday]"] == "02/02/1990"
    assert values["data[ownerGender]"] == "Nữ"


def test_khuyet_tat_owner_group_still_wins_over_fallback():
    values = _mapped_values([
        {"name": "ChuHoSo_HoTen", "value": "NGƯỜI ĐỨNG ĐƠN"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "099999999999"},
        {"name": "Ndd_HoTen", "value": "NGƯỜI ĐẠI DIỆN"},
        {"name": "Ndd_SoDinhDanh", "value": "012345678901"},
    ])

    assert values["data[ownerFullname]"] == "NGƯỜI ĐỨNG ĐƠN"
    assert values["data[ownerIdentityNumber]"] == "099999999999"


def test_khuyet_tat_representative_owner_is_not_copied_to_disabled_person():
    values = _mapped_values([
        {"name": "ChuHoSo_HoTen", "value": "NGƯỜI ĐẠI DIỆN"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "012345678901"},
        {"name": "ChuHoSo_NgaySinh", "value": "01/01/1980"},
        {"name": "Nkt_HoTen", "value": "NGƯỜI KHUYẾT TẬT"},
        {"name": "Ndd_HoTen", "value": "NGƯỜI ĐẠI DIỆN"},
        {"name": "Ndd_SoDinhDanh", "value": "012345678901"},
    ])

    assert values["data[ownerFullname]"] == "NGƯỜI ĐẠI DIỆN"
    assert values["data[NktHoTen]"] == "NGƯỜI KHUYẾT TẬT"
    assert "data[NktSoDinhdanh]" not in values
    assert "data[NktNgaySinh]" not in values


def test_khuyet_tat_self_applicant_can_fill_missing_nkt_fields_from_owner():
    values = _mapped_values([
        {"name": "ChuHoSo_HoTen", "value": "NGƯỜI KHUYẾT TẬT"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "012345678901"},
        {"name": "ChuHoSo_NgaySinh", "value": "02/02/1990"},
        {"name": "Nkt_HoTen", "value": "NGƯỜI KHUYẾT TẬT"},
    ])

    assert values["data[NktHoTen]"] == "NGƯỜI KHUYẾT TẬT"
    assert values["data[NktSoDinhdanh]"] == "012345678901"
    assert values["data[NktNgaySinh]"] == "02/02/1990"


@respx.mock
async def test_khuyet_tat_compact_agent_maps_application_and_cccd(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "OCR TEXT"}] * 20})
    )
    llm_out = {
        "fields": {
            "NguoiNop_HoTen": "VŨ ĐÌNH THIẾT",
            "NguoiNop_NgaySinh": "26/04/2003",
            "NguoiNop_GioiTinh": "Nam",
            "NguoiNop_SoDinhDanh": "040203015844",
            "NguoiNop_NgayCap": "02/07/2021",
            "NguoiNop_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "NguoiNop_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Nghệ An",
                "xa": "Tam Hợp",
                "diaChi": "Xóm Long Thành",
            },
            "NguoiNop_QuocTich": "Việt Nam",
            "ChuHoSo_HoTen": "LẠI NGỌC MINH",
            "ChuHoSo_SoDinhDanh": "012084000160",
            "ChuHoSo_NgaySinh": "01/01/1984",
            "ChuHoSo_GioiTinh": "Nam",
            "ChuHoSo_NgayCap": "25/04/2021",
            "ChuHoSo_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "ChuHoSo_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh Lai Châu",
                "xa": "Phường Tân Phong",
                "diaChi": "Số nhà 003, phố Yết Kiêu, Tổ 16",
            },
            "ChuHoSo_DienThoai": "0984456132",
            "ChuHoSo_QuocTich": "Việt Nam",
            "DeNghi_NoiDung": "xac_dinh",
            "Nkt_HoTen": "LẠI MINH QUANG",
            "Nkt_NgaySinh": "27/10/2019",
            "Nkt_SoDinhDanh": "012219003077",
            "Nkt_GioiTinh": "Nam",
            "Nkt_ThuongTru": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Tân Phong",
                "diaChi": "Số nhà 003, phố Yết Kiêu, Tổ 16",
            },
            "Nkt_NoiOHienNay": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Tân Phong",
                "diaChi": "Số nhà 003, phố Yết Kiêu, Tổ 16",
            },
            "Ndd_HoTen": "LẠI NGỌC MINH",
            "Ndd_SoDinhDanh": "012084000160",
            "Ndd_QuanHe": "bố đẻ",
            "Ndd_SoDienThoai": "0984456132",
            "Ndd_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Tân Phong",
                "diaChi": "Số nhà 003, phố Yết Kiêu, Tổ 16",
            },
            "KhuyetTat_DanhMuc": ["kt5"],
            "KhuyetTat_ChiTiet": ["kt5_1", "kt5_3"],
            "MucDo_HoatDong": {
                "1": "THD",
                "2": "THD",
                "3": "THD",
                "4": "CTG",
                "5": "THD",
                "6": "THD",
                "7": "THD",
                "8": "KTHD",
                "9": "CTG",
                "10": "CTG",
            },
        }
    }
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(llm_out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )

    res = await agent.run(
        {"doc": [_file("khuyết tật quang.pdf"), _file("cccd.pdf")]},
        {
            "formContext": {
                "applicantFullname": "VŨ ĐÌNH THIẾT",
                "applicantIdentityNumber": "040203015844",
            }
        },
    )
    fields = res["fields"]
    d = {f["name"]: f["value"] for f in fields}

    assert fields[0] == {
        "name": "data[isOwnerDossierCheck]",
        "comp": "dom-checkbox",
        "value": False,
    }
    # UI chốt đúng người; các field còn lại được bóc từ CCCD đã khớp mỏ neo UI.
    assert d["data[fullname]"] == "VŨ ĐÌNH THIẾT"
    assert d["data[identityNumber]"] == "040203015844"
    assert d["data[birthday]"] == "26/04/2003"
    assert d["data[gender]"] == "Nam"
    assert d["data[identityDate]"] == "02/07/2021"
    assert d["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["data[province]"] == "Nghệ An"
    assert d["data[district]"] == "Xã Tam Hợp"
    assert d["data[address]"] == "Xóm Long Thành"
    assert "data[phoneNumber]" not in d

    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[ownerFullname]"] == "LẠI NGỌC MINH"
    assert d["data[ownerIdentityNumber]"] == "012084000160"
    assert d["data[ownerIdentityDate]"] == "25/04/2021"
    assert d["data[ownerIdIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["data[ownerProvince]"] == "Lai Châu"
    assert d["data[ownerDistrict]"] == "Phường Tân Phong"
    assert d["data[ownerAddress]"] == "Số nhà 003, phố Yết Kiêu, Tổ 16"
    assert d["data[ownerPhoneNumber]"] == "0984456132"
    assert d["data[ownerNation]"] == "Việt Nam"

    assert d["data[chonNoiDungDeNghi][]"] is True
    assert d["data[NktHoTen]"] == "LẠI MINH QUANG"
    assert d["data[NktNgaySinh]"] == "27/10/2019"
    assert d["data[NktSoDinhdanh]"] == "012219003077"
    assert d["data[NktGioiTinh]"] == "Nam"
    assert d["data[NktMaTinh]"] == "Lai Châu"
    assert d["data[NktMaXa]"] == "Phường Tân Phong"
    assert d["data[NktDiachi]"] == "Số nhà 003, phố Yết Kiêu, Tổ 16"

    assert d["data[NddHoTen]"] == "LẠI NGỌC MINH"
    assert d["data[NddSoDinhdanh]"] == "012084000160"
    assert d["data[NddQuanheNkt]"] == "Cha"
    assert d["data[NddSodienthoai]"] == "0984456132"
    assert d["data[NddMaTinh]"] == "Lai Châu"
    assert d["data[NddMaXa]"] == "Phường Tân Phong"

    assert d["data[khuyetTat5Obj][khuyetTatRadio]"] == "co"
    assert d["data[khuyetTat5Obj][khuyetTatRadio1]"] == "co"
    assert d["data[khuyetTat5Obj][khuyetTatRadio3]"] == "co"
    assert d["data[mucDoKhuyetTatObj][mucDoRadio4]"] == "CTG"
    assert d["data[mucDoKhuyetTatObj][mucDoRadio8]"] == "KTHD"
    assert d["data[mucDoKhuyetTatObj][mucDoRadio10]"] == "CTG"
    assert not res["errors"]


def test_khuyet_tat_compact_prompt_contract():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "ĐƠN ĐỀ NGHỊ XÁC ĐỊNH" in system_prompt
    assert "Không trả field UI" in system_prompt
    assert "Đơn đề nghị là nguồn chính" in system_prompt
    assert "KhuyetTat_DanhMuc" in system_prompt
    assert "MucDo_HoatDong" in system_prompt
    assert "kt5_1" in system_prompt
    assert "kt5_3" in system_prompt
    assert "vỡ dòng" in system_prompt
    assert "tách riêng" in system_prompt
    assert "THD" in system_prompt
    assert "ChuHoSo_HoTen" in system_prompt
    assert "matched_requester_ocr" in system_prompt
    assert "BẮT BUỘC trả mọi NguoiNop_*" in system_prompt
    assert "NguoiNop_NgaySinh" in system_prompt
    assert "CẢ HAI nhóm ChuHoSo_* và Ndd_*" in system_prompt
    assert "Ndd_NoiCuTru -> ChuHoSo_NoiCuTru" in system_prompt
    assert "không suy đoán field không có nguồn" in system_prompt
    assert "Thường người nộp là chủ hồ sơ" not in system_prompt
    assert "Cccd_HoTen" not in system_prompt


def test_khuyet_tat_schema_uses_ui_anchors_to_extract_requester_from_ocr():
    context_names = {field["name"] for field in CONTEXT_FIELDS}
    llm_names = {field["name"] for field in FIELDS}

    assert context_names == {"NguoiNop_HoTen", "NguoiNop_SoDinhDanh"}
    assert context_names <= llm_names
    assert {
        "NguoiNop_NgaySinh",
        "NguoiNop_GioiTinh",
        "NguoiNop_NgayCap",
        "NguoiNop_NoiCap",
        "NguoiNop_NoiCuTru",
    } <= llm_names
    assert "ChuHoSo_HoTen" in llm_names
    assert "ChuHoSo_SoDinhDanh" in llm_names
    assert not any(name.startswith("Cccd_") for name in llm_names)


async def test_khuyet_tat_requester_context_only_marks_matching_document():
    context = await process_runner._requester_context(
        [
            {"name": "don.pdf", "text": "Người đại diện: BÙI THỊ YẾN NGỌC 051197014913"},
            {"name": "cccd.pdf", "text": "Họ và tên: VŨ ĐÌNH THIẾT Số: 040203015844 Ngày sinh: 26/04/2003"},
        ],
        {"formContext": {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        }},
    )

    assert 'result="document_match"' in context
    assert 'document="2"' in context
    assert 'document="1"' not in context
    assert "BÙI THỊ YẾN NGỌC" not in context


def test_registry_uses_khuyet_tat_process_pipeline():
    proc = get_procedure("xac-dinh-muc-do-khuyet-tat")

    assert get_pipeline("xac-dinh-muc-do-khuyet-tat") is agent.run
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["label"] == "Xác định, xác định lại mức độ khuyết tật và cấp Giấy xác nhận khuyết tật"
    assert proc["detect"]["textIncludes"] == [proc["label"]]
    assert get_attach_pipeline("xac-dinh-muc-do-khuyet-tat") is not None
    assert proc["roles"] == []
    assert "Đơn đề nghị" in proc["uploadHint"]
