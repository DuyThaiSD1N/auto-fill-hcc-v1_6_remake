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


async def _fake_ocr_per_file(files):
    return [{"name": f.get("name"), "text": "...", "provider": "test"} for f in files]


@respx.mock
async def test_khai_sinh_compact_agent_derives_angular_fields(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    monkeypatch.setattr(ocr, "ocr_per_file", _fake_ocr_per_file)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 20})
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
            "ThongTinBo_HoTen": "TRẦN THÀNH CÔNG",
            "ThongTinBo_SoDinhDanh": "025203007360",
            "ThongTinBo_NgaySinh": "11/7/2003",
            "ThongTinBo_QueQuan": {
                "tinh": "Nghệ An",
                "diaChi": "Xóm Long Thành",
            },
            "ThongTinBo_NoiCuTru": {
                "tinh": "Phú Thọ",
                "diaChi": "Khu 2",
            },
            "ThongTinMe_HoTen": "PHẠM NGỌC THỦY",
            "ThongTinMe_SoDinhDanh": "012193000851",
            "ThongTinMe_NgaySinh": "20/03/1993",
            "ThongTinMe_NoiCuTru": {
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
    assert 'dạng "/ NGUYỄN VĂN BÉ" phải trả "NGUYỄN VĂN BÉ"' in system_prompt
    assert "TOÀN BỘ phần còn lại sau nhãn" in system_prompt
    assert "phía sau vẫn còn chữ" in system_prompt
    assert "trẻ CHƯA CÓ TÊN: BỎ HẲN Gcs_HoTenCon" in system_prompt
    assert "Nếu ứng viên trùng tên mẹ thì BỎ Gcs_HoTenCon" in system_prompt
    assert "Tân Phong" not in system_prompt
    assert "THÔNG TIN THEO VAI TRÒ BỐ/MẸ" in system_prompt
    assert "CopyRequest_Quantity CHỈ lấy từ mục \"Đề nghị cấp bản sao\"" in system_prompt
    assert "TUYỆT ĐỐI không tự mặc định 1" in system_prompt
    assert "Không trả field mặc định hoặc field UI" in system_prompt
    assert "Ho, ChaHo, MeHo" in system_prompt
    assert "BanSaoSoLuong" in system_prompt


def test_khai_sinh_prompt_prioritizes_mother_ethnicity_sources():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    field_desc = {field["name"]: field["desc"] for field in FIELDS}

    desc = field_desc["ThongTinMe_DanToc"]
    assert desc.index("GIẤY CHỨNG SINH") < desc.index("GIẤY CHỨNG NHẬN KẾT HÔN")
    assert desc.index("GIẤY CHỨNG NHẬN KẾT HÔN") < desc.index("TỜ KHAI ĐĂNG KÝ KHAI SINH")
    assert "Đọc được giá trị thì phải trả field dù cách ghi ít gặp" in desc

    mother_rule = system_prompt.index("RIÊNG DÂN TỘC MẸ (ThongTinMe_DanToc)")
    birth_proof = system_prompt.index("(1) GIẤY CHỨNG SINH", mother_rule)
    marriage_certificate = system_prompt.index("(2) Nếu giấy chứng sinh", birth_proof)
    birth_form = system_prompt.index("(3) Chỉ khi hai nguồn trên", marriage_certificate)
    assert mother_rule < birth_proof < marriage_certificate < birth_form
    assert "KHÔNG được bỏ field vì cách ghi ít gặp" in system_prompt
    assert "Chỉ bỏ ThongTinMe_DanToc khi CẢ BA nguồn" in system_prompt


def test_khai_sinh_prompt_requires_father_ethnicity_from_birth_form_or_marriage_certificate():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    field_desc = {field["name"]: field["desc"] for field in FIELDS}

    desc = field_desc["ThongTinBo_DanToc"]
    assert desc.index("TỜ KHAI ĐĂNG KÝ KHAI SINH") < desc.index("GIẤY CHỨNG NHẬN KẾT HÔN")
    assert "bố đẻ/cha/người cha" in desc
    assert "chồng/bên nam" in desc
    assert "bắt buộc trả ThongTinBo_DanToc" in desc

    father_rule = system_prompt.index("RIÊNG DÂN TỘC CHA (ThongTinBo_DanToc)")
    birth_form = system_prompt.index("(1) TỜ KHAI ĐĂNG KÝ KHAI SINH", father_rule)
    marriage_certificate = system_prompt.index("(2) Nếu tờ khai", birth_form)
    mandatory_scan = system_prompt.index("PHẢI chủ động soát đúng khối cha/chồng", marriage_certificate)
    assert father_rule < birth_form < marriage_certificate < mandatory_scan
    assert "Chỉ khi CẢ HAI nguồn chính" in system_prompt
    assert "giấy chứng sinh/giấy khai sinh" in system_prompt


def test_khai_sinh_compact_contract_uses_parent_roles_not_cccd_gender_names():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    field_names = {field["name"] for field in FIELDS}

    assert {
        "ThongTinBo_HoTen",
        "ThongTinBo_SoDinhDanh",
        "ThongTinBo_DanToc",
        "ThongTinBo_NoiCuTru",
        "ThongTinMe_HoTen",
        "ThongTinMe_SoDinhDanh",
        "ThongTinMe_DanToc",
        "ThongTinMe_QueQuan",
        "ThongTinMe_NoiCuTru",
    } <= field_names
    assert not any(name.startswith(("CccdNam_", "CccdNu_")) for name in field_names)
    assert "CccdNam_" not in system_prompt
    assert "CccdNu_" not in system_prompt


def test_khai_sinh_prompt_keeps_mother_hometown_separate_from_residence():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    field_desc = {field["name"]: field["desc"] for field in FIELDS}

    assert "ThongTinMe_QueQuan" in field_desc
    assert "Quê quán / Place of origin:" in field_desc["ThongTinMe_QueQuan"]
    assert "BẮT BUỘC trích" in field_desc["ThongTinMe_QueQuan"]
    assert "không dùng nơi cư trú mẹ thay quê quán" in field_desc["ThongTinMe_QueQuan"]
    assert 'ThongTinMe_QueQuan: BẮT BUỘC trích' in system_prompt
    assert '"Quê quán / Place of origin:"' in system_prompt
    assert "tối thiểu `tinh`" in system_prompt
    assert "không được gán tên huyện vào `xa`" in system_prompt


def test_mapper_uses_mother_hometown_for_lam_dong_child_not_mother_residence():
    out = mapper.enrich(_fields({
        "Gcs_NgaySinhCon": "17/07/2026",
        "Gcs_NoiSinh": {
            "tinh": "Lâm Đồng",
            "diaChi": "Bệnh viện Đa khoa tỉnh Lâm Đồng",
        },
        "ThongTinMe_HoTen": "NGƯỜI MẸ",
        "ThongTinMe_QueQuan": {
            "tinh": "Quảng Ngãi",
            "xa": "Nghĩa Hòa",
        },
        "ThongTinMe_NoiCuTru": {
            "tinh": "Lâm Đồng",
            "xa": "Phường 12",
            "diaChi": "2/14 Thái Phiên",
        },
    }))
    values = {field["name"]: field["value"] for field in out}

    assert values["QqDiaChi"]["tinh"] == "Quảng Ngãi"
    assert values["QqDiaChi"]["xa"] == "Xã Tư Nghĩa"
    assert "2/14 Thái Phiên" not in str(values["QqDiaChi"])


def test_mapper_does_not_fallback_to_mother_residence_when_hometown_missing():
    out = mapper.enrich(_fields({
        "Gcs_NgaySinhCon": "17/07/2026",
        "Gcs_NoiSinh": {
            "tinh": "Lâm Đồng",
            "diaChi": "Bệnh viện Đa khoa tỉnh Lâm Đồng",
        },
        "ThongTinMe_HoTen": "NGƯỜI MẸ",
        "ThongTinMe_NoiCuTru": {
            "tinh": "Lâm Đồng",
            "xa": "Phường 12",
            "diaChi": "2/14 Thái Phiên",
        },
    }))
    values = {field["name"]: field["value"] for field in out}

    assert "QqDiaChi" not in values
    assert "QqMaQuocGia" not in values


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


def test_mapper_routes_cil_cill_to_other_ethnicity_fields():
    out = mapper.enrich(_fields({
        "Gcs_NgaySinhCon": "24/04/2026",
        "Gcs_DanTocCon": "Cill",
        "ThongTinMe_HoTen": "NGƯỜI MẸ",
        "ThongTinMe_DanToc": "Cil",
        "ThongTinBo_HoTen": "NGƯỜI CHA",
        "ThongTinBo_DanToc": " cill ",
    }))
    values = {field["name"]: field for field in out}
    names = [field["name"] for field in out]

    assert values["MaDanToc"]["value"] == "Khác"
    assert values["DantocKhac"]["value"] == "Cill"
    assert names.index("MaDanToc") < names.index("DantocKhac")

    assert values["MeMaDanToc"]["value"] == "Khác"
    assert values["MeDantocKhac"]["value"] == "Cil"
    assert names.index("MeMaDanToc") < names.index("MeDantocKhac")

    assert values["ChaMaDanToc"]["value"] == "Khác"
    assert values["ChaDantocKhac"]["value"] == "cill"
    assert names.index("ChaMaDanToc") < names.index("ChaDantocKhac")


def test_mapper_maps_role_based_parent_fields_for_cill_dossier():
    out = mapper.enrich(_fields({
        "Gcs_NgaySinhCon": "23/07/2026",
        "Gcs_GioiTinhCon": "Nữ",
        "Gcs_NoiSinh": {
            "tinh": "Lâm Đồng",
            "diaChi": "Bệnh viện Đa khoa tỉnh Lâm Đồng",
        },
        "ThongTinBo_HoTen": "CIL PAM LÊ NISH",
        "ThongTinBo_SoDinhDanh": "068095001840",
        "ThongTinBo_NgaySinh": "11/05/1995",
        "ThongTinBo_DanToc": "Cill",
        "ThongTinMe_HoTen": "KA SĂ K' TRINH",
        "ThongTinMe_SoDinhDanh": "068195008008",
        "ThongTinMe_NgaySinh": "20/09/1995",
        "ThongTinMe_DanToc": "Cơ Ho",
    }))
    values = {field["name"]: field["value"] for field in out}

    assert values["ChaHoTen"] == "CIL PAM LÊ NISH"
    assert values["ChaSoGiayTo"] == "068095001840"
    assert values["ChaMaDanToc"] == "Khác"
    assert values["ChaDantocKhac"] == "Cill"
    assert values["MeSoGiayTo"] == "068195008008"
    assert values["MeMaDanToc"] == "Cơ Ho"
    assert "MeDantocKhac" not in values


def test_mapper_keeps_known_ethnicity_as_direct_select():
    out = mapper.enrich(_fields({
        "Gcs_NgaySinhCon": "24/04/2026",
        "Gcs_DanTocCon": "Kinh",
        "ThongTinMe_HoTen": "NGƯỜI MẸ",
        "ThongTinMe_DanToc": "Cơ Ho",
        "ThongTinBo_HoTen": "NGƯỜI CHA",
        "ThongTinBo_DanToc": "Mông",
    }))
    values = {field["name"]: field["value"] for field in out}

    assert values["MaDanToc"] == "Kinh"
    assert values["MeMaDanToc"] == "Cơ Ho"
    assert values["ChaMaDanToc"] == "Mông"
    assert "DantocKhac" not in values
    assert "MeDantocKhac" not in values
    assert "ChaDantocKhac" not in values


def test_mapper_routes_lam_dong_child_inferred_cil_to_other_as_default():
    out = mapper.enrich(_fields({
        "Gcs_NgaySinhCon": "24/04/2026",
        "Gcs_NoiSinh": {
            "tinh": "Lâm Đồng",
            "diaChi": "Trung Tâm Y Tế Khu Vực Đơn Dương",
        },
        "ThongTinMe_HoTen": "KA KHÔN",
        "ThongTinMe_DanToc": "Cil",
    }))
    values = {field["name"]: field for field in out}

    assert values["MeMaDanToc"]["value"] == "Khác"
    assert values["MeDantocKhac"]["value"] == "Cil"
    assert values["MaDanToc"] == {"name": "MaDanToc", "comp": "select", "value": "Khác", "default": True}
    assert values["DantocKhac"] == {"name": "DantocKhac", "comp": "text", "value": "Cil", "default": True}


def test_mapper_rejects_mother_name_as_child_but_keeps_birth_facts():
    out = mapper.enrich(_fields({
        "Gcs_HoTenCon": "PHAN THỊ BÌNH",
        "Gcs_NgaySinhCon": "13/06/2026",
        "Gcs_GioiTinhCon": "Nữ",
        "Gcs_NoiSinh": {
            "tinh": "Lâm Đồng",
            "diaChi": "Bệnh viện Đa khoa tỉnh Lâm Đồng",
        },
        "ThongTinMe_HoTen": "PHAN THỊ BÌNH",
        "ThongTinMe_SoDinhDanh": "040194019162",
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
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 20})
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


def test_prompt_dang_ky_lai_khai_sinh_uu_tien_ngay_sinh_gioi_tinh_theo_cccd():
    from app.pipelines.khai_sinh_dang_ky_lai.process.prompt import EXTRA_RULES as dang_ky_lai

    assert "NGÀY SINH + GIỚI TÍNH theo CCCD" in dang_ky_lai
