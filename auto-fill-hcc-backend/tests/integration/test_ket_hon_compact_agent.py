"""Compact agent đăng ký kết hôn: OCR text -> BenNam/BenNu -> legacy UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.ket_hon import process as agent
from app.pipelines.ket_hon.process import mapper, runner as ket_hon_runner
from app.pipelines.ket_hon.process import base_prompt as ket_hon_base_prompt
from app.pipelines.ket_hon.process.prompt import EXTRA_RULES
from app.pipelines.ket_hon.process.schema import FIELDS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")


@respx.mock
async def test_ket_hon_compact_agent_derives_ui_fields(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 20})
    )
    out = {
        "fields": {
            "BenNam_HoTen": "VŨ ĐÌNH THIẾT",
            "BenNam_SoDinhDanh": "040203015844",
            "BenNam_NgaySinh": "26/4/2003",
            "BenNam_NgayCap": "2/7/2021",
            "BenNam_NoiCuTru_TrongNuoc": {
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
            "BenNu_HoTen": "PHẠM NGỌC THỦY",
            "BenNu_SoDinhDanh": "012193000851",
            "BenNu_NgaySinh": "20/03/1993",
            "BenNu_NgayCap": "06/02/2024",
            "BenNu_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "BenNu_NoiCuTru_TrongNuoc": {
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
    assert d["LoaiGiayToDinhDanh_BenNam"] == "Căn cước công dân"
    assert d["NgaySinhBenNam"] == "26/04/2003"
    assert d["NgayCapDD_BenNam"] == "02/07/2021"
    assert d["NoiCapDD_BenNam"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["QuocTichBenNam"] == "Việt Nam"
    assert d["LoaiCuTru_BenNam"] == "Thường trú"
    assert d["NoiCuTru_BenNam"] == "1"
    assert d["NoiCuTru_BenNam_TrongNuoc"] == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương",
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
        "xa": "Xã Đạ Huoai",
        "diaChi": "94 Lê Hồng Phong, Thôn 4",
    }
    assert d["CapBanSao"] == "Có"
    assert d["SoLuong"] == "2"

    # Field UI agent tự trả ("Độc thân") bị bỏ; ô tình trạng hôn nhân chỉ mang mặc định nghiệp vụ
    # của form (không giấy tờ nào nói gì) và được đánh dấu default để FE tô vàng.
    status = next(f for f in res["fields"] if f["name"] == "LoaiTinhTrangHonNhan_BenNam")
    assert status["value"] == "Hiện tại chưa đăng ký kết hôn với ai"
    assert status.get("default") is True
    assert not res["errors"]


def test_ket_hon_compact_prompt_instructs_gender_split():
    system_prompt = ket_hon_base_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    field_desc = {field["name"]: field["desc"] for field in FIELDS}

    assert "Nam -> nhóm BenNam_*" in system_prompt
    assert "Nữ -> nhóm BenNu_*" in system_prompt
    assert "Không phân biệt nam/nữ theo tên file" in system_prompt
    assert "CHỈ đọc ở MẶT TRƯỚC" in system_prompt
    assert "TUYỆT ĐỐI không" in system_prompt and "MRZ/IDVNM ở mặt sau" in system_prompt
    assert "không dùng MRZ để bù" in system_prompt
    assert "CHỈ đọc ở MẶT TRƯỚC" in field_desc["BenNam_SoDinhDanh"]
    assert "CHỈ đọc ở MẶT TRƯỚC" in field_desc["BenNu_SoDinhDanh"]
    assert "không đọc, ghép hoặc suy ra từ MRZ/IDVNM" in field_desc["BenNam_SoDinhDanh"]
    assert "không đọc, ghép hoặc suy ra từ MRZ/IDVNM" in field_desc["BenNu_SoDinhDanh"]
    assert "BẮT BUỘC cố đọc BenNam_NoiCap/BenNu_NoiCap" in system_prompt
    assert "Bộ Công an" in system_prompt
    assert "HoTenBenNam" in system_prompt
    assert "Không trả field UI/default" in system_prompt
    assert '"TỜ KHAI ĐĂNG KÝ KẾT HÔN"' in system_prompt
    assert "Nếu có số lượng dương thì BẮT BUỘC trả CopyRequest_WantsCopy" in system_prompt
    assert "TUYỆT ĐỐI không mặc định" in system_prompt
    assert "CHỈ lấy từ CCCD/CMND của bên nam" in field_desc["BenNam_NoiCuTru_TrongNuoc"]
    assert "CHỈ lấy từ CCCD/CMND của bên nữ" in field_desc["BenNu_NoiCuTru_TrongNuoc"]
    assert "CHỈ lấy từ tờ khai" in field_desc["ToKhaiNam_NoiCuTru_TrongNuoc"]
    assert "CHỈ lấy từ tờ khai" in field_desc["ToKhaiNu_NoiCuTru_TrongNuoc"]
    assert "mapper sẽ tự ưu tiên tờ khai" in system_prompt
    assert "giấy xác nhận tình trạng hôn nhân" in system_prompt
    assert 'nhãn rõ "Xã ..." hoặc "Phường ..."' in system_prompt
    assert "TUYỆT ĐỐI không fuzzy/sửa họ tên để tạo khớp" in system_prompt
    assert 'Cấp tỉnh Hồ Chí Minh luôn trả đúng "Thành phố Hồ Chí Minh"' in system_prompt
    assert 'P9/P.9/P 9 → "Phường 9"' in system_prompt


def test_ket_hon_ethnicity_requires_explicit_labeled_source():
    system_prompt = ket_hon_base_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    field_desc = {field["name"]: field["desc"] for field in FIELDS}

    assert 'không xuất hiện nhãn "Dân tộc" → BỎ CẢ HAI field dân tộc' in system_prompt
    assert "không suy đoán dân tộc" in system_prompt
    assert "Dân tộc phổ biến" not in system_prompt
    assert "thiếu nhãn thì bỏ field" in field_desc["BenNam_DanToc"]
    assert "thiếu nhãn thì bỏ field" in field_desc["BenNu_DanToc"]

    # Hai CCCD không cung cấp dân tộc: compact output không có field dân tộc thì mapper
    # cũng tuyệt đối không tự tạo giá trị cho form.
    mapped = {
        field["name"]: field["value"]
        for field in mapper.enrich([
            {"name": "BenNam_HoTen", "value": "NGƯỜI NAM"},
            {"name": "BenNam_SoDinhDanh", "value": "001001001001"},
            {"name": "BenNu_HoTen", "value": "NGƯỜI NỮ"},
            {"name": "BenNu_SoDinhDanh", "value": "002002002002"},
        ])
    }
    assert "DanTocBenNam" not in mapped
    assert "DanTocBenNu" not in mapped


def test_ket_hon_drops_inferred_ethnicity_when_two_cccd_have_no_ethnicity_label():
    hallucinated = {
        "BenNam_HoTen": "NGƯỜI NAM",
        "BenNam_DanToc": "DÂN TỘC SUY ĐOÁN",
        "BenNu_HoTen": "NGƯỜI NỮ",
        "BenNu_DanToc": "DÂN TỘC SUY ĐOÁN",
    }
    two_identity_cards = [
        {"text": "CĂN CƯỚC - Họ và tên: NGƯỜI NAM - Giới tính: Nam - Nơi cư trú: Bản A"},
        {"text": "CĂN CƯỚC - Họ và tên: NGƯỜI NỮ - Giới tính: Nữ - Nơi cư trú: Bản B"},
    ]

    filtered = ket_hon_runner._compact_field_fallback(hallucinated, two_identity_cards)

    assert filtered["BenNam_HoTen"] == "NGƯỜI NAM"
    assert filtered["BenNu_HoTen"] == "NGƯỜI NỮ"
    assert "BenNam_DanToc" not in filtered
    assert "BenNu_DanToc" not in filtered


def test_ket_hon_keeps_ethnicity_when_document_has_explicit_label():
    extracted = {"BenNam_DanToc": "Kinh", "BenNu_DanToc": "Mông"}
    declaration = [{"text": "TỜ KHAI ĐĂNG KÝ KẾT HÔN\nDân tộc | Kinh | Mông"}]

    assert ket_hon_runner._compact_field_fallback(extracted, declaration) == extracted


def test_ket_hon_does_not_recheck_divorce_status_after_llm():
    extracted = {
        "BenNu_HoTen": "NGƯỜI NỮ",
        "BenNu_TinhTrangHonNhan": "3",
        "BenNam_HoTen": "NGƯỜI NAM",
        "BenNam_TinhTrangHonNhan": "3",
    }
    documents = [{"text": "QUYẾT ĐỊNH LY HÔN"}]

    assert ket_hon_runner._compact_field_fallback(extracted, documents) == extracted


_HAI_THE_LIEN_NHAU = "\n".join([
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
    "CĂN CƯỚC CÔNG DÂN",
    "Citizen Identity Card",
    "Số / No.: 001190000111",
    "Họ và tên / Full name:",
    "TRẦN THỊ MẪU",
    "Giới tính / Sex: Nữ Quốc tịch / Nationality: Việt Nam",
    "Nơi thường trú / Place of residence: 12 Lê Lợi",
    "Phường 3, Thành phố Đà Lạt, Lâm Đồng",
    "Có giá trị đến: 01/01/2030",
    "",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
    "CĂN CƯỚC",
    "IDENTITY CARD",
    "Số định danh cá nhân / Personal identification number:",
    "002095000222",
    "LÊ VĂN THỬ",
    "Giới tính / Sex:",
    "Nam",
    "───── Trang 2/2 ─────",
    "Đặc điểm nhận dạng / Personal identification:",
    "Ngày, tháng, năm / Date, month, year: 10/05/2021",
    "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "IDVNM1900001115001190000111<<0",
    "9001011F3001010VNM<<<<<<<<<<<<8",
    "TRAN<<THI<MAU<<<<<<<<<<<<<<<<<",
    "Nơi cư trú / Place of residence: Thôn 7",
    "Gia Hiệp, Di Linh, Lâm Đồng",
    "Nơi đăng ký khai sinh / Place of birth:",
    "Gia Hiệp, Di Linh, Lâm Đồng",
    "Ngày, tháng, năm cấp / Date of issue:",
    "05/08/2024",
    "BỘ CÔNG AN/MINISTRY OF PUBLIC SECURITY",
    "IDVNMO950002229002095000222<<<8",
    "9501013M3501014VNM<<<<<<<<<<<<4",
    "LE<<VAN<THU<<<<<<<<<<<<<<<<<<<",
])
_DIA_CHI_NU = {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường 3", "diaChi": "12 Lê Lợi"}
_DIA_CHI_NAM = {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Gia Hiệp", "diaChi": "Thôn 7"}


def test_ket_hon_dao_lai_noi_cu_tru_va_ngay_cap_lay_nham_mat_sau_the_nguoi_kia():
    """Mặt sau thẻ Căn cước của nam đứng ngay sau MRZ của nữ → LLM gán nhầm nơi cư trú, ngày/nơi cấp cho nữ."""
    docs = [{"name": "the.pdf", "text": _HAI_THE_LIEN_NHAU}]
    extracted = {
        "CccdNu_SoDinhDanh": "001190000111", "CccdNam_SoDinhDanh": "002095000222",
        "CccdNu_NgayCap": "05/08/2024", "CccdNu_NoiCap": "Bộ Công an",
        "CccdNam_NgayCap": "05/08/2024", "CccdNam_NoiCap": "Bộ Công an",
        "CccdNu_NoiCuTru_TrongNuoc": dict(_DIA_CHI_NAM),
        "CccdNam_NoiCuTru_TrongNuoc": dict(_DIA_CHI_NU),
    }

    fixed = ket_hon_runner._compact_field_fallback(extracted, docs)

    assert fixed["CccdNu_NoiCuTru_TrongNuoc"] == _DIA_CHI_NU
    assert fixed["CccdNam_NoiCuTru_TrongNuoc"] == _DIA_CHI_NAM
    assert fixed["CccdNu_NgayCap"] == "10/05/2021"
    assert fixed["CccdNu_NoiCap"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert fixed["CccdNam_NgayCap"] == "05/08/2024"
    assert fixed["CccdNam_NoiCap"] == "Bộ Công an"


def test_ket_hon_bo_trong_dia_chi_nu_khi_ca_hai_ben_deu_lay_dia_chi_nam():
    docs = [{"name": "the.pdf", "text": _HAI_THE_LIEN_NHAU}]
    extracted = {
        "CccdNu_SoDinhDanh": "001190000111", "CccdNam_SoDinhDanh": "002095000222",
        "CccdNu_NoiCuTru_TrongNuoc": dict(_DIA_CHI_NAM),
        "CccdNam_NoiCuTru_TrongNuoc": {**_DIA_CHI_NAM, "diaChi": "Thôn Gia Hiệp 9", "xa": "Di Linh"},
    }

    fixed = ket_hon_runner._compact_field_fallback(extracted, docs)

    assert fixed["CccdNam_NoiCuTru_TrongNuoc"] == _DIA_CHI_NAM
    assert "CccdNu_NoiCuTru_TrongNuoc" not in fixed


def test_ket_hon_giu_nguyen_khi_gan_dung_hoac_hai_ben_chung_dia_chi():
    docs = [{"name": "the.pdf", "text": _HAI_THE_LIEN_NHAU}]
    dung = {
        "CccdNu_SoDinhDanh": "001190000111", "CccdNam_SoDinhDanh": "002095000222",
        "CccdNu_NgayCap": "10/05/2021", "CccdNam_NgayCap": "05/08/2024",
        "CccdNu_NoiCuTru_TrongNuoc": dict(_DIA_CHI_NU),
        "CccdNam_NoiCuTru_TrongNuoc": dict(_DIA_CHI_NAM),
    }
    assert ket_hon_runner._compact_field_fallback(dung, docs) == dung

    chung = _HAI_THE_LIEN_NHAU.replace("Nơi cư trú / Place of residence: Thôn 7\nGia Hiệp, Di Linh",
                                       "Nơi cư trú / Place of residence: 12 Lê Lợi\nPhường 3, Thành phố Đà Lạt")
    cung_dia_chi = {**dung, "CccdNam_NoiCuTru_TrongNuoc": dict(_DIA_CHI_NU)}
    assert ket_hon_runner._compact_field_fallback(cung_dia_chi, [{"name": "the.pdf", "text": chung}]) == cung_dia_chi


def test_ket_hon_khong_gan_hang_noi_cu_tru_tren_to_khai_cho_the():
    to_khai = "\n".join([
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "TỜ KHAI ĐĂNG KÝ KẾT HÔN",
        "Số định danh cá nhân: 001190000111 002095000222",
        "Nơi cư trú: Thôn 7, Gia Hiệp, Di Linh, Lâm Đồng",
    ])
    extracted = {
        "CccdNu_SoDinhDanh": "001190000111", "CccdNam_SoDinhDanh": "002095000222",
        "CccdNu_NoiCuTru_TrongNuoc": dict(_DIA_CHI_NU),
        "CccdNam_NoiCuTru_TrongNuoc": dict(_DIA_CHI_NAM),
    }
    assert ket_hon_runner._compact_field_fallback(extracted, [{"name": "tk.pdf", "text": to_khai}]) == extracted


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
            {"name": "BenNam_HoTen", "value": "NGƯỜI NAM"},
            {"name": "BenNam_SoDinhDanh", "value": "079000000001"},
            {"name": "BenNam_NoiCuTru_TrongNuoc", "value": {
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


def test_ket_hon_registration_type_has_no_default_but_keeps_explicit_declaration():
    def mapped(compact_fields):
        return {field["name"]: field for field in mapper.enrich(compact_fields)}

    without_declaration = mapped([{"name": "BenNam_HoTen", "value": "NGƯỜI NAM"}])
    assert "loaiDangKy" not in without_declaration

    explicit = mapped([
        {"name": "BenNam_HoTen", "value": "NGƯỜI NAM"},
        {"name": "ToKhai_LoaiDangKy", "value": "Đăng ký lần đầu"},
    ])
    assert explicit["loaiDangKy"]["value"] == "1"
    assert "default" not in explicit["loaiDangKy"]


def test_registry_uses_ket_hon_compact_agent_mode():
    proc = get_procedure("ket-hon")

    assert get_pipeline("ket-hon") is agent.run
    assert get_attach_pipeline("ket-hon") is not None
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["roles"] == []
