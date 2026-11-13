"""Compact agent xác định mức độ khuyết tật: đơn đề nghị + CCCD -> Form.io fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.khuyet_tat import process as agent
from app.pipelines.khuyet_tat.process import mapper
from app.pipelines.khuyet_tat.process import runner as process_runner
from app.pipelines.khuyet_tat.process import vision
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
        {"name": "NguoiNop_GioiTinh", "value": "Nữ"},
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
    # Giới tính OCR sai người ("Nữ") không được bù; chỉ suy từ số định danh tài khoản (chữ số thứ 4 chẵn → Nam).
    assert values["data[gender]"] == "Nam"


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


def _area_field(name, tinh, xa, dia_chi):
    return {"name": name, "value": {"quocGia": "Việt Nam", "tinh": tinh, "xa": xa, "diaChi": dia_chi}}


def test_khuyet_tat_old_city_in_province_slot_maps_to_current_ward():
    """Đơn chỉ ghi "phường X NT - KH" / "Phường Tây Nha Trang": LLM đặt thành phố cũ vào ô tỉnh, có lúc chẻ tên
    phường mới thành xã "Tây" + tỉnh "Nha Trang" → ô tỉnh và phường/xã đều trượt option."""
    values = _mapped_values([
        {"name": "ChuHoSo_HoTen", "value": "TRẦN VĂN BÌNH"},
        _area_field("ChuHoSo_NoiCuTru", "Nha Trang", "Vĩnh Phước", "Tổ 5 Đường Số 2"),
        {"name": "Nkt_HoTen", "value": "TRẦN VĂN BÌNH"},
        _area_field("Nkt_ThuongTru", "Nha Trang", "Vĩnh Phước", "Tổ 5 Đường Số 2"),
        _area_field("Nkt_NoiOHienNay", "Nha Trang", "Tây", "Tổ 3"),
        {"name": "Ndd_HoTen", "value": "LÊ THỊ HOA"},
        _area_field("Ndd_NoiCuTru", "Thành phố Nha Trang", "Phường Vĩnh Phước", "Tổ 5"),
    ])

    assert values["data[ownerProvince]"] == "Khánh Hòa"
    assert values["data[ownerDistrict]"] == "Phường Bắc Nha Trang"
    assert values["data[NktMaTinh]"] == "Khánh Hòa"
    assert values["data[NktMaXa]"] == "Phường Bắc Nha Trang"
    assert values["data[NktDiachi]"] == "Tổ 5 Đường Số 2"
    assert values["data[NktNOHTMaTinh]"] == "Khánh Hòa"
    assert values["data[NktNOHTMaXa]"] == "Phường Tây Nha Trang"
    assert values["data[NktNOHTDiaChi]"] == "Tổ 3"
    assert values["data[NddMaTinh]"] == "Khánh Hòa"
    assert values["data[NddMaXa]"] == "Phường Bắc Nha Trang"


async def test_khuyet_tat_truncated_ward_is_recovered_from_ocr(monkeypatch):
    """LLM trả đúng tỉnh nhưng cắt cụt phường ("Nam"): runner đưa OCR cho mapper dò lại cụm có nhãn trên giấy."""
    monkeypatch.setattr(vision, "ENABLED", False)

    async def fake_run(files_by_role, **kwargs):
        return {
            "fields": [
                {"name": "Nkt_HoTen", "comp": "x-input", "value": "TRẦN VĂN BÌNH"},
                {"name": "Nkt_NoiOHienNay", "comp": "x-select-area",
                 "value": {"quocGia": "Việt Nam", "tinh": "Khánh Hòa", "xa": "Nam", "diaChi": "Tổ 7"}},
            ],
            "ocr_text": "I. THÔNG TIN NGƯỜI KHUYẾT TẬT\n- Nơi ở hiện nay: Tổ 7 Phường Nam Nha Trang\n",
            "errors": [],
        }

    monkeypatch.setattr(process_runner.runner, "run", fake_run)
    res = await agent.run({"doc": [_file("don.pdf")]}, {})
    d = {f["name"]: f for f in res["fields"]}

    assert d["data[NktNOHTMaTinh]"]["value"] == "Khánh Hòa"
    assert d["data[NktNOHTMaXa]"]["value"] == "Phường Nam Nha Trang"
    assert d["data[NktNOHTDiaChi]"]["value"] == "Tổ 7"
    assert "default" not in d["data[NktNOHTDiaChi]"]


def test_khuyet_tat_unselectable_ward_is_left_blank_and_flagged():
    """Không dò được phường/xã hiện hành: không phát tên trượt danh mục (extension vớ nhầm option gần giống), giữ tên
    đã đọc cuối địa chỉ chi tiết và tô vàng."""
    mapped = mapper.enrich([
        {"name": "Nkt_HoTen", "value": "TRẦN VĂN BÌNH"},
        _area_field("Nkt_ThuongTru", "Khánh Hòa", "Tây", "Tổ 3"),
    ], {})
    d = {f["name"]: f for f in mapped}

    assert d["data[NktMaTinh]"]["value"] == "Khánh Hòa"
    assert "data[NktMaXa]" not in d
    assert d["data[NktDiachi]"]["value"] == "Tổ 3, Tây"
    assert d["data[NktDiachi]"]["default"] is True


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
            "ChuHoSo_HoTen": "LẠI MINH QUANG",
            "ChuHoSo_SoDinhDanh": "012219003077",
            "ChuHoSo_NgaySinh": "27/10/2019",
            "ChuHoSo_GioiTinh": "Nam",
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
    # Chủ hồ sơ là người ở mục I (người khuyết tật), không phải người đại diện đứng đơn.
    assert d["data[ownerFullname]"] == "LẠI MINH QUANG"
    assert d["data[ownerIdentityNumber]"] == "012219003077"
    assert d["data[ownerBirthday]"] == "27/10/2019"
    assert "data[ownerIdentityDate]" not in d
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
    # Không đọc được ảnh Mục III → giữ bảng từ OCR + LLM, kèm cảnh báo cho cán bộ soát lại;
    # tắt hẳn bước đọc ảnh (vision.ENABLED=False) thì không có lượt đọc nào để cảnh báo.
    assert res["errors"] == ([vision.SECTION_III_WARNING] if vision.ENABLED else [])


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
    assert "CẢ HAI nhóm ChuHoSo_* và Nkt_*" in system_prompt
    assert "Nkt_ThuongTru -> ChuHoSo_NoiCuTru" in system_prompt
    assert "KHÔNG phải chủ hồ sơ" in system_prompt
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
