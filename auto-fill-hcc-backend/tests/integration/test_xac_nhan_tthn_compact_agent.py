"""Compact agent xác nhận tình trạng hôn nhân: 1 CCCD -> self fields."""

import json

import httpx
import pytest
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


def test_xac_nhan_tthn_maps_divorce_without_decision_date():
    """OCR quyết định ly hôn mất dòng ngày ban hành -> vẫn phải chọn "đã ly hôn" + điền số bản án.

    Ca thật: dấu treo đè lên dòng "Đà Lạt, ngày ... tháng ... năm ...", OCR chỉ còn số quyết định
    và tên tòa. Trước đây mapper đòi đủ cả ba nên bỏ trắng cả ô tình trạng hôn nhân lẫn số bản án.
    """
    mapped = mapper.enrich([
        {"name": "Cccd_HoTen", "value": "LÊ MINH TUYÊN"},
        {"name": "Cccd_SoDinhDanh", "value": "068094003777"},
        {"name": "DivorceDecision_Number", "value": "87/2022/QĐST-HNGD"},
        {"name": "DivorceDecision_Agency", "value": "Tòa án nhân dân thành phố Đà Lạt, tỉnh Lâm Đồng"},
    ])
    values = {field["name"]: field["value"] for field in mapped}

    assert values["TinhTrangHonNhanC1"] == (
        "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; "
        "hiện tại chưa đăng ký kết hôn với ai"
    )
    detail = values["nxnLoaiTinhTrangHonNhan=3"]
    assert detail["soBanAnQuyetDinhLyHon"] == "87/2022/QĐST-HNGD"
    assert detail["coQuanCapBanAnQuyetDinhLyHon"] == "Tòa án nhân dân thành phố Đà Lạt, tỉnh Lâm Đồng"
    assert "ngayCapBanAnQuyetDinhLyHon" not in detail


def test_xac_nhan_tthn_maps_death_cert_without_date():
    """Cùng luật với ly hôn: giấy chứng tử đọc thiếu ngày vẫn phải chốt trạng thái GÓA."""
    mapped = mapper.enrich([
        {"name": "Cccd_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "DeathCert_Number", "value": "123"},
        {"name": "DeathCert_Agency", "value": "UBND phường Hải Châu"},
    ])
    values = {field["name"]: field["value"] for field in mapped}

    assert values["TinhTrangHonNhanC1"] == (
        "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng vợ/chồng đã chết; "
        "hiện tại chưa đăng ký kết hôn với ai"
    )
    assert values["nxnLoaiTinhTrangHonNhan=4"]["soBanAnQuyetDinhLyHon"] == "123"


_DIVORCED_LABEL = (
    "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; "
    "hiện tại chưa đăng ký kết hôn với ai"
)


def _status_of(extra):
    base = [
        {"name": "Cccd_HoTen", "value": "LÊ MINH TUYÊN"},
        {"name": "Cccd_SoDinhDanh", "value": "068094003777"},
    ]
    mapped = mapper.enrich(base + [{"name": k, "value": v} for k, v in extra.items()])
    return {field["name"]: field["value"] for field in mapped}


_DIVORCE_DOC = {
    "DivorceDecision_Number": "87/2022/QĐST-HNGD",
    "DivorceDecision_Date": "20/03/2022",
    "DivorceDecision_Agency": "Tòa án nhân dân thành phố Đà Lạt",
}


@pytest.mark.parametrize("declared", [
    "Đã ly hôn",                                   # LLM rút gọn
    "đã ly hôn.",                                  # thừa dấu chấm cuối
    _DIVORCED_LABEL,                               # nguyên văn nhãn cổng
    _DIVORCED_LABEL + ".",                         # nguyên văn + dấu chấm
])
def test_xac_nhan_tthn_accepts_declared_divorce_wording_variants(declared):
    """Tờ khai khai ly hôn bằng chữ nào cũng phải ra đúng option + số bản án.

    Bản cũ so `==` với nguyên văn nhãn cổng: lệch một chữ là không phát gì, mà chuỗi `if/elif`
    còn chặn luôn fallback đọc từ quyết định ly hôn → trắng cả hai ô.
    """
    values = _status_of({**_DIVORCE_DOC, "TinhTrangHonNhanC1": declared})

    assert values["TinhTrangHonNhanC1"] == _DIVORCED_LABEL
    assert values["nxnLoaiTinhTrangHonNhan=3"]["soBanAnQuyetDinhLyHon"] == "87/2022/QĐST-HNGD"


def test_xac_nhan_tthn_unreadable_declared_status_falls_back_to_documents():
    """Chữ tình trạng hôn nhân không hiểu được thì BỎ QUA, không được nuốt lượt của giấy tờ."""
    values = _status_of({**_DIVORCE_DOC, "TinhTrangHonNhanC1": "khong doc duoc"})

    assert values["TinhTrangHonNhanC1"] == _DIVORCED_LABEL
    assert values["nxnLoaiTinhTrangHonNhan=3"]["coQuanCapBanAnQuyetDinhLyHon"] == (
        "Tòa án nhân dân thành phố Đà Lạt"
    )


@pytest.mark.parametrize("declared", ["Độc thân", "Chưa kết hôn"])
def test_xac_nhan_tthn_accepts_never_married_wording_variants(declared):
    values = _status_of({"TinhTrangHonNhanC1": declared})

    assert values["TinhTrangHonNhanC1"] == "Hiện tại chưa đăng ký kết hôn với ai"


def test_xac_nhan_tthn_declared_remarriage_beats_past_divorce():
    """Tờ khai ghi gộp "đã ly hôn, hiện tại đã kết hôn với..." → phải là ĐANG CÓ VỢ/CHỒNG.

    Hai option ly hôn/góa đều kết thúc bằng "hiện tại chưa đăng ký kết hôn với ai" nên chọn
    chúng cho người đã cưới lại là khai sai sự thật.
    """
    values = _status_of({
        **_DIVORCE_DOC,
        "Marriage_SpouseName": "Trần Thị B",
        "Marriage_Number": "55",
        "Marriage_Date": "01/06/2023",
        "TinhTrangHonNhanC1": "Đã ly hôn, hiện tại đã kết hôn với bà Trần Thị B",
    })

    assert values["TinhTrangHonNhanC1"] == "Hiện tại đang có vợ/chồng"
    assert values["nxnLoaiTinhTrangHonNhan=2"]["voChongHoTen"] == "Trần Thị B"


def test_xac_nhan_tthn_period_option_survives_declared_status():
    """Xác nhận chưa ĐKKH trong một KHOẢNG đã qua (option 5) vẫn thắng chữ tự khai."""
    values = _status_of({
        "Marriage_SpouseName": "Trần Thị B",
        "Marriage_Number": "55",
        "Marriage_Date": "01/06/2023",
        "Period_TuNgay": "27/04/2016",
        "Period_DenNgay": "14/09/2016",
        "TinhTrangHonNhanC1": "Hiện tại đang có vợ/chồng",
    })

    assert values["TinhTrangHonNhanC1"].startswith("Từ ngày…")
    assert values["nxnLoaiTinhTrangHonNhan=5"]["thoiDiemBatDau"] == "27/04/2016"


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


# --- Loại giấy tờ theo số: 9 chữ số = CMND, 12 chữ số = CCCD ---

def _tthn_out(**kv):
    return {f["name"]: f["value"] for f in mapper.enrich([{"name": k, "value": v} for k, v in kv.items()])}


def test_so_9_chu_so_thi_chon_chung_minh_nhan_dan():
    out = _tthn_out(
        ToKhai_HoTen="TRẦN VĂN NAM",
        ToKhai_SoDinhDanh="245123456",
        ToKhaiYeuCau_HoTen="TRẦN VĂN NAM",
        ToKhaiYeuCau_SoDinhDanh="245123456",
        ToKhaiYeuCau_QuanHe="Bản thân",
    )
    assert out["LoaiGiayToDinhDanhC1"] == "Chứng minh nhân dân"
    assert out["LoaiGiayToDinhDanhC"] == "Chứng minh nhân dân"


def test_so_12_chu_so_van_la_can_cuoc():
    out = _tthn_out(
        ToKhai_HoTen="NGUYỄN THỊ HOÀ",
        ToKhai_SoDinhDanh="036301012326",
        ToKhai_NoiCapGiayTo="Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    )
    assert out["LoaiGiayToDinhDanhC1"] == "Thẻ căn cước công dân"


# --- LLM bỏ sót Cccd_HoTen: đọc lại tên in trên đúng thẻ theo số định danh ---

_OCR_CCCD_NHUNG = [
    {"name": "CCCD mặt sau.jpg", "text": "IDVNM1930052419036193005241<<4\nNGUYEN<<THI<BICH<NHUNG"},
    {"name": "CCCD mặt trước.jpg", "text": (
        "CĂN CƯỚC CÔNG DÂN\nSố / No.: 036193005241\nHọ và tên / Full name:\n"
        "NGUYỄN THỊ BÍCH NHUNG\nNgày sinh / Date of birth: 26/10/1993"
    )},
    {"name": "Đăng ký kết hôn.jpg", "text": "Họ, chữ đệm, tên chồng: VŨ HỮU NINH"},
]


def test_llm_bo_sot_ten_thi_doc_lai_ten_tren_the():
    from app.pipelines.xac_nhan_tthn.process.runner import _compact_field_fallback

    fields = _compact_field_fallback({"Cccd_SoDinhDanh": "036193005241"}, _OCR_CCCD_NHUNG)
    assert fields["Cccd_HoTen"] == "NGUYỄN THỊ BÍCH NHUNG"


def test_so_khong_khop_the_thi_khong_muon_ten():
    from app.pipelines.xac_nhan_tthn.process.runner import _compact_field_fallback

    fields = _compact_field_fallback({"Cccd_SoDinhDanh": "001099000111"}, _OCR_CCCD_NHUNG)
    assert "Cccd_HoTen" not in fields
