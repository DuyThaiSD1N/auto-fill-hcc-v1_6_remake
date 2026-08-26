"""Compact agent xác nhận tình trạng hôn nhân: 1 CCCD -> self fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.xac_nhan_tthn import process as agent
from app.pipelines.xac_nhan_tthn.process import mapper
from app.pipelines.xac_nhan_tthn.process.prompt import EXTRA_RULES
from app.pipelines.xac_nhan_tthn.process.schema import FIELDS
from app.procedures.registry import get_pipeline, get_procedure


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")


def test_xac_nhan_tthn_maps_declared_purpose_to_other_detail():
    mapped = mapper.enrich([
        {"name": "Purpose", "comp": "x-input", "value": "Bổ sung hồ sơ giao dịch dân sự"},
    ])
    values = {field["name"]: field["value"] for field in mapped}

    assert values["mucdich"] == "Sử dụng vào mục đích khác"
    assert values["nhapmucdichkhac"] == "Bổ sung hồ sơ giao dịch dân sự"


def test_xac_nhan_tthn_prompt_requires_purpose_from_current_declaration():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert 'BẮT BUỘC trả Purpose khi TỜ KHAI có dòng "Mục đích sử dụng' in system_prompt
    assert "TỜ KHAI hiện tại →" in system_prompt
    assert "Python sẽ mặc định chọn" in system_prompt


def test_xac_nhan_tthn_maps_declared_married_and_self_relation():
    mapped = mapper.enrich(
        [
            {"name": "Cccd_HoTen", "comp": "x-input", "value": "NGUYỄN THỊ A"},
            {"name": "Cccd_SoDinhDanh", "comp": "x-input", "value": "0123456789"},
            {"name": "ToKhai_LaBanThan", "comp": "x-input", "value": True},
            {
                "name": "TinhTrangHonNhanC1",
                "comp": "x-select",
                "value": "Hiện tại đang có vợ/chồng",
            },
        ],
        {
            "formContext": {
                "applicantFullname": "NGUYỄN THỊ A",
                "applicantIdentityNumber": "012345678901",
            }
        },
    )
    values = {field["name"]: field["value"] for field in mapped}

    assert values["quanhevoinguoiduocxacminh"] == "1"
    assert values["TinhTrangHonNhanC1"] == "Hiện tại đang có vợ/chồng"


def test_xac_nhan_tthn_prompt_allows_declared_married_and_self_relation():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert 'nội dung bắt đầu bằng "Chưa kết hôn"' in system_prompt
    assert '"Chưa kết hôn lần hai"' in system_prompt
    assert '"hiện tại đang có chồng" hoặc "hiện tại đang có vợ"' in system_prompt
    assert 'TinhTrangHonNhanC1 = "Hiện tại đang có vợ/chồng"' in system_prompt
    assert "ToKhai_LaBanThan=true" in system_prompt
    assert 'dòng quan hệ ghi "Tự khai"/"Bản thân"' in system_prompt


def test_xac_nhan_tthn_maps_declared_spouse_name_without_marriage_certificate():
    mapped = mapper.enrich([
        {
            "name": "TinhTrangHonNhanC1",
            "comp": "x-select",
            "value": "Hiện tại đang có vợ/chồng",
        },
        {"name": "Marriage_SpouseName", "comp": "x-input", "value": "TRẦN VĂN B"},
    ])
    values = {field["name"]: field["value"] for field in mapped}

    assert values["TinhTrangHonNhanC1"] == "Hiện tại đang có vợ/chồng"
    assert values["nxnLoaiTinhTrangHonNhan=2"] == {"voChongHoTen": "TRẦN VĂN B"}


def test_xac_nhan_tthn_maps_all_available_marriage_certificate_fields():
    mapped = mapper.enrich([
        {
            "name": "TinhTrangHonNhanC1",
            "comp": "x-select",
            "value": "Hiện tại đang có vợ/chồng",
        },
        {"name": "Marriage_SpouseName", "comp": "x-input", "value": "TRẦN VĂN B"},
        {"name": "Marriage_Number", "comp": "x-input", "value": "12/2020"},
        {"name": "Marriage_Date", "comp": "x-date", "value": "02/03/2020"},
        {"name": "Marriage_Agency", "comp": "x-input", "value": "Ủy ban nhân dân xã Minh Sơn"},
    ])
    values = {field["name"]: field["value"] for field in mapped}
    names = [field["name"] for field in mapped]

    assert values["nxnLoaiTinhTrangHonNhan=2"] == {
        "voChongHoTen": "TRẦN VĂN B",
        "soGiayTo": "12/2020",
        "ngayCapGiayTo": "02/03/2020",
        "coQuanCapGiayTo": "Ủy ban nhân dân xã Minh Sơn",
    }
    assert values["soGiayTo"] == "12/2020"
    assert values["ngayCapGiayTo-day"] == "02"
    assert values["ngayCapGiayTo-month"] == "03"
    assert values["ngayCapGiayTo-year"] == "2020"
    assert values["ngayCapGiayTo-name-date-input"] == "2020-03-02"
    assert values["coQuanCapGiayTo"] == "Ủy ban nhân dân xã Minh Sơn"
    assert names.index("nxnLoaiTinhTrangHonNhan=2") < names.index("soGiayTo")


def test_xac_nhan_tthn_prompt_does_not_mix_spouse_identity_with_marriage_certificate():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert 'sau cụm "đang có chồng là"' in system_prompt
    assert "thiếu field nào thì bỏ field đó" in system_prompt
    assert "Không lấy số CCCD/CMND, ngày sinh, ngày cấp CCCD" in system_prompt


def test_xac_nhan_tthn_expands_commune_abbreviations():
    def mapped_area(xa):
        mapped = mapper.enrich([
            {"name": "Cccd_HoTen", "comp": "x-input", "value": "NGUYỄN VĂN A"},
            {
                "name": "Cccd_NoiCuTru",
                "comp": "x-select-area",
                "value": {
                    "quocGia": "Việt Nam",
                    "tinh": "Lâm Đồng",
                    "xa": xa,
                    "diaChi": "12 Đường Mẫu",
                },
            },
        ])
        values = {field["name"]: field["value"] for field in mapped}
        return values["nycNoiCuTru_TrongNuoc"]

    assert mapped_area("P.10")["xa"] == "Phường 10"
    assert mapped_area("X. Tân Hà")["xa"] == "Xã Tân Hà"


def test_xac_nhan_tthn_prefers_declaration_residence_over_identity_card():
    mapped = mapper.enrich([
        {"name": "Cccd_HoTen", "comp": "x-input", "value": "NGUYỄN VĂN A"},
        {
            "name": "Cccd_NoiCuTru",
            "comp": "x-select-area",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Lâm Đồng",
                "xa": "P.10",
                "diaChi": "10 Đường Cũ",
            },
        },
        {
            "name": "ToKhai_NoiCuTru",
            "comp": "x-select-area",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Lâm Đồng",
                "xa": "Phường Xuân Hương - Đà Lạt",
                "diaChi": "20 Đường Mới",
            },
        },
    ])
    values = {field["name"]: field["value"] for field in mapped}

    assert values["nycNoiCuTru_TrongNuoc"] == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương - Đà Lạt",
        "diaChi": "20 Đường Mới",
    }
    assert values["nxnNoiCuTru_TrongNuoc"] == values["nycNoiCuTru_TrongNuoc"]


def test_xac_nhan_tthn_relative_declares_on_behalf_without_poa_fills_requester_from_tokhai():
    """Con khai hộ cha, không có giấy ủy quyền: Mục I phải lấy khối 'người yêu cầu' đầu tờ khai
    (Nguyễn Văn Cung), KHÔNG được lấy nhầm sang người được cấp giấy (Nguyễn Văn Hoan, Mục II).
    Tờ khai ghi rõ quan hệ "là con đẻ" → phải tick "Khác" (2), và ô quan hệ phải được add() TRƯỚC
    HoVaTenC (cổng dựng lại Mục I khi đổi quan hệ, tick sau sẽ xóa mất dữ liệu vừa điền)."""
    mapped = mapper.enrich([
        {"name": "ToKhaiYeuCau_HoTen", "comp": "x-input", "value": "Nguyễn Văn Cung"},
        {"name": "ToKhaiYeuCau_SoDinhDanh", "comp": "x-input", "value": "027067009711"},
        {"name": "ToKhaiYeuCau_NgayCapGiayTo", "comp": "x-date", "value": "18/12/2021"},
        {"name": "ToKhaiYeuCau_NoiCapGiayTo", "comp": "x-input",
         "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
        {
            "name": "ToKhaiYeuCau_NoiCuTru", "comp": "x-select-area",
            "value": {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Nam Sơn", "diaChi": "TDP Sơn Tự"},
        },
        {"name": "ToKhaiYeuCau_QuanHe", "comp": "x-input", "value": "là con đẻ"},
        {"name": "ToKhai_HoTen", "comp": "x-input", "value": "Nguyễn Văn Hoan"},
        {"name": "ToKhai_SoDinhDanh", "comp": "x-input", "value": "027038003070"},
        {"name": "ToKhai_NgaySinh", "comp": "x-date", "value": "15/07/1938"},
    ])
    values = {field["name"]: field["value"] for field in mapped}
    names = [field["name"] for field in mapped]

    # Mục I (người yêu cầu) = Cung, KHÔNG phải Hoan.
    assert values["HoVaTenC"] == "Nguyễn Văn Cung"
    assert values["SoDinhDanhC"] == "027067009711"
    assert values["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Mục II (người được cấp) vẫn đúng là Hoan.
    assert values["HoVaTenC1"] == "Nguyễn Văn Hoan"
    assert values["SoDinhDanhC1"] == "027038003070"
    # Tờ khai ghi rõ "là con đẻ" → quan hệ = "Khác" (2), không phải bỏ trống, không phải "1".
    assert values["quanhevoinguoiduocxacminh"] == "2"
    # Ô quan hệ phải đứng TRƯỚC HoVaTenC trong danh sách field phát ra (tick trước, điền đè sau).
    assert names.index("quanhevoinguoiduocxacminh") < names.index("HoVaTenC")


def test_xac_nhan_tthn_self_declares_via_tokhaiyeucau_block_still_marks_self():
    """Tờ khai ghi quan hệ "Bản thân" → tick "1", đứng TRƯỚC HoVaTenC trong danh sách field."""
    mapped = mapper.enrich([
        {"name": "ToKhaiYeuCau_HoTen", "comp": "x-input", "value": "Nguyễn Văn A"},
        {"name": "ToKhaiYeuCau_SoDinhDanh", "comp": "x-input", "value": "012345678901"},
        {"name": "ToKhaiYeuCau_QuanHe", "comp": "x-input", "value": "Bản thân"},
        {"name": "ToKhai_HoTen", "comp": "x-input", "value": "Nguyễn Văn A"},
        {"name": "ToKhai_SoDinhDanh", "comp": "x-input", "value": "012345678901"},
    ])
    values = {field["name"]: field["value"] for field in mapped}
    names = [field["name"] for field in mapped]

    assert values["HoVaTenC"] == "Nguyễn Văn A"
    assert values["quanhevoinguoiduocxacminh"] == "1"
    assert names.index("quanhevoinguoiduocxacminh") < names.index("HoVaTenC")


def test_xac_nhan_tthn_relation_text_wins_over_name_comparison():
    """Chữ quan hệ trên tờ khai LUÔN ưu tiên hơn so tên/CCCD: dù người yêu cầu và người được cấp
    trùng tên/số định danh (OCR ghi cùng), tờ khai ghi rõ "là mẹ đẻ" thì vẫn phải tick "Khác"."""
    mapped = mapper.enrich([
        {"name": "ToKhaiYeuCau_HoTen", "comp": "x-input", "value": "Nguyễn Thị B"},
        {"name": "ToKhaiYeuCau_SoDinhDanh", "comp": "x-input", "value": "012345678901"},
        {"name": "ToKhaiYeuCau_QuanHe", "comp": "x-input", "value": "là mẹ đẻ"},
        {"name": "ToKhai_HoTen", "comp": "x-input", "value": "Nguyễn Thị B"},
        {"name": "ToKhai_SoDinhDanh", "comp": "x-input", "value": "012345678901"},
    ])
    values = {field["name"]: field["value"] for field in mapped}

    assert values["quanhevoinguoiduocxacminh"] == "2"


def test_xac_nhan_tthn_falls_back_to_name_match_when_relation_text_missing():
    """Không có dòng quan hệ trên tờ khai → lùi về so tên/CCCD như cũ (không phải bỏ trống ngay)."""
    mapped = mapper.enrich([
        {"name": "ToKhaiYeuCau_HoTen", "comp": "x-input", "value": "Nguyễn Văn A"},
        {"name": "ToKhaiYeuCau_SoDinhDanh", "comp": "x-input", "value": "012345678901"},
        {"name": "ToKhai_HoTen", "comp": "x-input", "value": "Nguyễn Văn A"},
        {"name": "ToKhai_SoDinhDanh", "comp": "x-input", "value": "012345678901"},
    ])
    values = {field["name"]: field["value"] for field in mapped}

    assert values["quanhevoinguoiduocxacminh"] == "1"


def test_xac_nhan_tthn_no_requester_no_cccd_does_not_override_muc_i():
    """Không có khối người yêu cầu riêng, không có CCCD upload → Mục I để trống (giữ VNeID cổng)."""
    mapped = mapper.enrich([
        {"name": "ToKhai_HoTen", "comp": "x-input", "value": "Nguyễn Văn Hoan"},
        {"name": "ToKhai_SoDinhDanh", "comp": "x-input", "value": "027038003070"},
    ])
    values = {field["name"]: field["value"] for field in mapped}

    assert "HoVaTenC" not in values
    assert "SoDinhDanhC" not in values
    assert values["HoVaTenC1"] == "Nguyễn Văn Hoan"


def test_xac_nhan_tthn_poa_relation_is_khac_and_ticked_before_identity():
    """Có giấy ủy quyền thật: quan hệ luôn "Khác" (2), và phải add() TRƯỚC HoVaTenC — cổng dựng
    lại Mục I khi đổi quan hệ, tick sau sẽ xóa mất dữ liệu vừa điền."""
    mapped = mapper.enrich([
        {"name": "Cccd_HoTen", "comp": "x-input", "value": "NGUYỄN VĂN B"},
        {"name": "Cccd_SoDinhDanh", "comp": "x-input", "value": "011122223333"},
        {"name": "PoA_SubjectName", "comp": "x-input", "value": "Nguyễn Văn A"},
        {"name": "PoA_SubjectIdNumber", "comp": "x-input", "value": "012345678901"},
    ])
    values = {field["name"]: field["value"] for field in mapped}
    names = [field["name"] for field in mapped]

    assert values["quanhevoinguoiduocxacminh"] == "2"
    assert names.index("quanhevoinguoiduocxacminh") < names.index("HoVaTenC")


def test_xac_nhan_tthn_prompt_requires_separate_declaration_residence():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "ToKhai_NoiCuTru = dòng" in system_prompt
    assert "BẮT BUỘC trả ToKhai_NoiCuTru" in system_prompt
    assert "ToKhai_NoiCuTru → Cccd_NoiCuTru" in system_prompt
    assert "output phải có ToKhai_NoiCuTru" in system_prompt


@respx.mock
async def test_xac_nhan_tthn_compact_agent_derives_self_ui_fields(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 20})
    )
    out = {
        "fields": {
            "Cccd_HoTen": "VŨ ĐÌNH THIẾT",
            "Cccd_SoDinhDanh": "040203015844",
            "Cccd_NgaySinh": "26/4/2003",
            "Cccd_GioiTinh": "Nam",
            "Cccd_DanToc": "Kinh",
            "Cccd_NgayCap": "2/7/2021",
            "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Cccd_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Nghệ An",
                "diaChi": "Xóm Long Thành",
            },
            "Purpose": "Bổ sung hồ sơ giao dịch dân sự",
            "HoVaTenC1": "UI_SAI",
            "TinhTrangHonNhanC1": "Hiện tại chưa đăng ký kết hôn với ai",
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

    res = await agent.run({"doc": [_file("cccd truoc.jpg"), _file("cccd sau.jpg")]}, {})
    by_name = {f["name"]: f for f in res["fields"]}
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert "loaiDangKy" not in d
    assert d["HoVaTenC"] == "VŨ ĐÌNH THIẾT"
    assert d["SoDinhDanhC"] == "040203015844"
    assert d["LoaiGiayToDinhDanhC"] == "Căn cước công dân"
    assert d["NgayCapDDC"] == "02/07/2021"
    assert d["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["nycLoaiCuTru"] == "Thường trú"
    assert d["nycNoiCuTru"] == "1"
    assert d["nycNoiCuTru_TrongNuoc"]["tinh"] == "Nghệ An"

    assert d["quanhevoinguoiduocxacminh"] == "1"
    assert d["HoVaTenC1"] == "VŨ ĐÌNH THIẾT"
    assert d["NgaySinhC1"] == "26/04/2003"
    assert d["GioiTinhC1"] == "Nam"
    assert d["DanTocC1"] == "Kinh"
    assert d["QuocTichC1"] == "Việt Nam"
    assert d["SoDinhDanhC1"] == "040203015844"
    assert d["SoGiayToTuyThanC1"] == "040203015844"
    assert by_name["SoGiayToTuyThanC1"]["aliases"] == ["SoGiayToDinhDanhC1"]
    assert d["LoaiGiayToDinhDanhC1"] == "Căn cước công dân"
    assert d["NgayCapDDC1"] == "02/07/2021"
    assert d["NoiCapDDC1"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["nxnLoaiCuTru"] == "Thường trú"
    assert d["nxnNoiCuTru"] == "1"
    assert d["nxnNoiCuTru_TrongNuoc"]["diaChi"] == "Xóm Long Thành"
    assert d["mucdich"] == "Sử dụng vào mục đích khác"
    assert d["nhapmucdichkhac"] == "Bổ sung hồ sơ giao dịch dân sự"
    assert d["TraKQ"] == "1"

    assert d["TinhTrangHonNhanC1"] == "Hiện tại chưa đăng ký kết hôn với ai"
    assert not res["errors"]


@respx.mock
async def test_xac_nhan_tthn_compact_agent_maps_divorce_decision(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 20})
    )
    out = {
        "fields": {
            "Cccd_HoTen": "PHẠM MINH TUÂN",
            "Cccd_SoDinhDanh": "012071000001",
            "Cccd_NgaySinh": "01/01/1971",
            "Cccd_GioiTinh": "Nam",
            "Cccd_NgayCap": "02/02/2021",
            "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "DivorceDecision_Number": "16/2012/QĐST-HNGĐ",
            "DivorceDecision_Date": "03/05/2012",
            "DivorceDecision_Agency": "Tòa án nhân dân thị xã Lai Châu, tỉnh Lai Châu",
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

    res = await agent.run({"doc": [_file("cccd.pdf", "application/pdf"), _file("qd-ly-hon.pdf", "application/pdf")]}, {})
    by_name = {f["name"]: f for f in res["fields"]}
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["TinhTrangHonNhanC1"] == (
        "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; "
        "hiện tại chưa đăng ký kết hôn với ai"
    )
    assert by_name["nxnLoaiTinhTrangHonNhan=3"]["aliases"] == ["nxnLoaiTinhTrangHonNhan=2"]
    divorce_detail = d["nxnLoaiTinhTrangHonNhan=3"]
    assert divorce_detail["soBanAnQuyetDinhLyHon"] == "16/2012/QĐST-HNGĐ"
    assert divorce_detail["ngayCapBanAnQuyetDinhLyHon"] == "03/05/2012"
    assert divorce_detail["coQuanCapBanAnQuyetDinhLyHon"] == "Tòa án nhân dân thị xã Lai Châu, tỉnh Lai Châu"


@respx.mock
async def test_xac_nhan_tthn_compact_agent_defaults_issuer(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 20})
    )
    out = {"fields": {"Cccd_HoTen": "NGUYỄN VĂN A", "Cccd_SoDinhDanh": "012345678901"}}
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )

    res = await agent.run({"doc": [_file("cccd.jpg")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["HoVaTenC"] == "NGUYỄN VĂN A"
    assert d["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["NoiCapDDC1"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_xac_nhan_tthn_compact_prompt_allows_declared_never_married_status():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "mặc định NGƯỜI YÊU CẦU là BẢN THÂN" in system_prompt
    assert "Cccd_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND" in system_prompt
    assert "Không trả field UI/default" in system_prompt
    assert "quanhevoinguoiduocxacminh" in system_prompt
    assert "DivorceDecision_* lấy từ OCR" in system_prompt
    assert "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN CŨ" in system_prompt  # nguồn giấy XNTTHN cũ
    assert 'RIÊNG TinhTrangHonNhanC1 được trả khi TỜ KHAI ghi rõ' in system_prompt
    assert '"Hiện tại chưa đăng ký kết hôn với ai"' in system_prompt
    assert "Không suy luận tình trạng hôn nhân từ CCCD" in system_prompt
    assert 'BẮT BUỘC trả Purpose khi TỜ KHAI có dòng "Mục đích sử dụng' in system_prompt
    assert "TỜ KHAI hiện tại →" in system_prompt
    assert "Python sẽ mặc định chọn" in system_prompt


def test_registry_uses_xac_nhan_tthn_compact_agent_mode():
    proc = get_procedure("xac-nhan-tinh-trang-hon-nhan")

    assert get_pipeline("xac-nhan-tinh-trang-hon-nhan") is agent.run
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["roles"] == []
    assert "useRequestMode" not in proc
    assert "Mặc định người yêu cầu là bản thân" in proc["uploadHint"]
