"""[Lai Châu] Hỗ trợ chi phí mai táng đối với người dân tộc thiểu số giai đoạn 2025-2030 (2.002862).

Khóa theo file mapping "HS MAI TÁNG NQ 53" + ảnh ánh xạ đính kèm:
  - process: bộ ô CongDan_* của người nộp (= người đứng ra mai táng), không lẫn người chết;
  - attach: bảng 5 dòng fixed-slot có tick, file gộp Mẫu 01 + Mẫu 02 lên cả dòng 1 và dòng 4, CCCD vào
    "Giấy tờ khác".

Dữ liệu trong test là PLACEHOLDER, không phải hồ sơ thật của người dân.
"""

import base64

from app.pipelines._shared import fold
from app.pipelines.ho_tro_mai_tang_dan_toc_thieu_so_lai_chau.attach import planner
from app.pipelines.ho_tro_mai_tang_dan_toc_thieu_so_lai_chau.process import mapper
from app.pipelines.ho_tro_mai_tang_dan_toc_thieu_so_lai_chau.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "ho-tro-mai-tang-dan-toc-thieu-so-lai-chau"


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _facts(**extra) -> list[dict]:
    base = {
        "Cccd_HoTen": "Lò Văn A",
        "Cccd_SoDinhDanh": "012000000001",
        "Cccd_NgaySinh": "01/02/1980",
        "Cccd_GioiTinh": "Nam",
        "Cccd_NgayCap": "03/04/2025",
        "Cccd_NoiCap": "Bộ Công an",
        "Cccd_NoiCuTru": {"tinh": "Lai Châu", "xa": "Xã Mẫu", "diaChi": "Ban Mau Mot"},
        "ToKhai_HoTen": "Lò Văn A",
        "ToKhai_ThuongTru": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Mẫu", "diaChi": "Bản Mẫu Một"},
        "ToKhai_NoiO": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Mẫu", "diaChi": "Bản Mẫu Hai"},
        "NguoiNop_DienThoai": "0900 000 001",
        "HoNgheo_ChuHo": "Lò Văn A",
        "HoNgheo_DanToc": "Thái",
        "NguoiChet_HoTen": "Lường Thị B",
    }
    base.update(extra)
    return [{"name": name, "value": value} for name, value in base.items() if value is not None]


# ---------------------------------------------------------------- process/mapper


def test_mapper_dien_nguoi_nop_theo_cccd_va_to_khai():
    values = _values(mapper.enrich(_facts()))

    assert values["CongDan_tenCongDan"] == "LÒ VĂN A"
    assert values["CongDan_ngaySinhCongDan"] == "01/02/1980"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_soCmnd"] == values["CongDan_soCCCD"] == "012000000001"
    assert values["CongDan_ngayCapCmnd"] == "03/04/2025"
    assert values["CongDan_noiCapCmnd"] == "Bộ Công an"
    assert values["CongDan_maDMQuocGia"] == "Việt Nam"
    assert values["CongDan_diDong"] == "0900000001"
    # Thẻ Căn cước mới không in dân tộc → lấy dòng chủ hộ của Giấy hộ nghèo (chủ hộ = người nộp).
    assert values["CongDan_danTocCongDan"] == "Thái"
    # Hộ gia đình đứng ra mai táng + thẻ do Bộ Công an cấp → hai ô này để trống.
    assert "CongDan_tenCoQuanToChuc" not in values
    assert "CongDan_maTinhCapCMND" not in values


def test_mapper_dia_chi_uu_tien_to_khai_hon_the_mat_dau():
    values = _values(mapper.enrich(_facts()))

    assert values["CongDan_maTinhThanh"] == "Tỉnh Lai Châu"
    assert values["CongDan_maPhuongXa"] == "Xã Mẫu"
    assert values["CongDan_diaChi"] == "Bản Mẫu Một"
    assert values["CongDan_diaChiThuongTru"] == "Bản Mẫu Một, Xã Mẫu, Tỉnh Lai Châu"
    assert values["CongDan_noiOHienTai"] == "Bản Mẫu Hai, Xã Mẫu, Tỉnh Lai Châu"


def test_mapper_khong_to_khai_thi_dung_dia_chi_tren_the():
    values = _values(mapper.enrich(_facts(ToKhai_ThuongTru=None, ToKhai_NoiO=None)))

    assert values["CongDan_diaChi"] == "Ban Mau Mot"
    assert values["CongDan_noiOHienTai"] == values["CongDan_diaChiThuongTru"]


def test_mapper_khong_lay_dan_toc_khi_chu_ho_ngheo_la_nguoi_chet():
    values = _values(mapper.enrich(_facts(HoNgheo_ChuHo="Lường Thị B")))

    assert "CongDan_danTocCongDan" not in values


def test_mapper_bo_the_cccd_cua_nguoi_chet_dung_to_khai():
    facts = _facts(
        Cccd_HoTen="LƯỜNG THỊ B",
        Cccd_SoDinhDanh="012000000002",
        Cccd_GioiTinh="Nữ",
        ToKhai_SoCccd="012000000001",
        ToKhai_NgaySinh="01/02/1980",
        ToKhai_NgayCap="03/04/2025",
        ToKhai_NoiCap="Bộ công an cấp.",
    )
    values = _values(mapper.enrich(facts))

    assert values["CongDan_tenCongDan"] == "LÒ VĂN A"
    assert values["CongDan_soCmnd"] == "012000000001"
    assert values["CongDan_noiCapCmnd"] == "Bộ Công an"
    # Giới tính chỉ có trên thẻ: thẻ không phải của người nộp thì bỏ trống, không lấy giới tính người chết.
    assert "CongDan_gioiTinhCongDan" not in values


def test_mapper_to_chuc_dung_ra_mai_tang():
    values = _values(mapper.enrich(_facts(ToChuc_Ten="Hội Mẫu xã Mẫu")))

    assert values["CongDan_tenCoQuanToChuc"] == "Hội Mẫu xã Mẫu"


def test_schema_moi_o_ui_deu_co_comp_va_khong_phat_o_khong_nguon():
    values = _values(mapper.enrich(_facts()))

    assert set(values) <= set(UI_COMP_BY_NAME)
    for name in ("CongDan_fax", "CongDan_website", "CongDan_email", "CongDan_soGCNGP", "CongDan_maDMDiaChi"):
        assert name not in UI_COMP_BY_NAME
    assert {"Cccd_HoTen", "ToKhai_ThuongTru", "HoNgheo_DanToc", "NguoiChet_HoTen"} <= ALLOWED


# ---------------------------------------------------------------- attach/planner

_TEXTS = {
    "bien-ban.pdf": "Mẫu số 02\nBIÊN BẢN XÁC NHẬN VIỆC MAI TÁNG\nGiấy trích lục khai tử số: 1",
    "trich-luc.pdf": "UBND XÃ MẪU\nTRÍCH LỤC KHAI TỬ\nGiấy tờ tùy thân: Thẻ Căn cước số 012000000002",
    "ho-ngheo.pdf": "GIẤY CHỨNG NHẬN HỘ NGHÈO, HỘ CẬN NGHÈO\nSố CC/CCCD: 012000000001",
    "to-khai.pdf": "Mẫu số 01\nTỜ KHAI ĐỀ NGHỊ HỖ TRỢ CHI PHÍ MAI TÁNG\n8. Hình thức mai táng (Hỏa táng hoặc không hỏa táng)",
    "hs-mai-tang.docx": "TỜ KHAI ĐỀ NGHỊ HỖ TRỢ CHI PHÍ MAI TÁNG\n...\nBIÊN BẢN XÁC NHẬN VIỆC MAI TÁNG",
    "cccd.pdf": "CĂN CƯỚC\nIDENTITY CARD\nHọ, chữ đệm và tên khai sinh / Full name:\nLÒ VĂN A\nNgày, tháng, năm sinh",
    "hoa-tang.pdf": "GIẤY XÁC NHẬN\nCơ sở hỏa táng xác nhận đã hỏa táng thi thể",
    "anh-khac.jpg": "Sao kê tài khoản",
}


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf", "dataUrl": "data:application/pdf;base64,QQ=="} for name in names]


def _ocr(names: list[str]) -> list[dict]:
    return [{"name": name, "text": _TEXTS[name]} for name in names]


def test_bang_5_dong_dung_ten_va_tu_khoa_khong_chong_nhau():
    assert [slot["slotIndex"] for slot in planner.SLOTS] == [0, 1, 2, 3, 4]
    assert planner.SLOTS[1]["slotName"] == "Bản sao trích lục khai tử; (Bản sao)"
    assert len({slot["slotKey"] for slot in planner.SLOTS}) == 5
    for slot in planner.SLOTS:
        for keyword in slot["slotKeywords"]:
            owners = [other["slotIndex"] for other in planner.SLOTS if keyword in fold(other["slotName"])]
            assert owners == [slot["slotIndex"]], keyword


def test_dinh_tuyen_ho_so_mau_theo_rule_khi_khong_co_llm():
    names = ["cccd.pdf", "bien-ban.pdf", "trich-luc.pdf", "ho-ngheo.pdf", "to-khai.pdf", "hs-mai-tang.docx"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _ocr(names), {})

    slots = [(item["fileName"], item.get("slotIndex")) for item in attachments if item["target"] == "fixed-slot"]
    assert slots == [
        ("bien-ban.pdf", 0),
        ("trich-luc.pdf", 1),
        ("ho-ngheo.pdf", 2),
        ("to-khai.pdf", 3),
        ("hs-mai-tang.docx", 0),
        ("hs-mai-tang.docx", 3),
    ]
    assert all(item["tickRow"] for item in attachments if item["target"] == "fixed-slot")
    # Không có dòng 5 (hỏa táng) khi hồ sơ chôn cất.
    assert all(item.get("slotIndex") != 4 for item in attachments)

    identity = [item for item in attachments if item["target"] == "new"]
    assert len(identity) == 1
    assert identity[0]["fileName"] == "cccd.pdf"
    assert identity[0]["componentName"] == "Căn cước người nộp - Lò Văn A"
    assert identity[0]["needsAddComponent"] is True
    assert warnings == []


def test_file_gop_hai_mau_thang_nhan_don_cua_llm():
    names = ["hs-mai-tang.docx"]
    attachments, _, classified = planner.build_plan_items(_files(names), _ocr(names), {0: "to_khai_de_nghi"})

    assert [item["slotIndex"] for item in attachments] == [0, 3]
    assert classified[0]["docType"] == "to_khai_va_bien_ban"


def test_llm_thang_rule_va_llm_other_thi_ve_rule():
    names = ["hoa-tang.pdf", "trich-luc.pdf"]
    attachments, _, classified = planner.build_plan_items(
        _files(names), _ocr(names), {0: "xac_nhan_hoa_tang", 1: "other"}
    )

    assert [(item["fileName"], item["slotIndex"]) for item in attachments] == [("hoa-tang.pdf", 4), ("trich-luc.pdf", 1)]
    assert [entry["source"] for entry in classified] == ["llm", "rule"]


def test_file_khong_ro_vao_giay_to_khac_kem_canh_bao():
    names = ["anh-khac.jpg"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _ocr(names), {})

    assert attachments[0]["target"] == "new"
    assert attachments[0]["componentName"] == "anh-khac"
    assert "Giấy tờ khác" in warnings[0]


def test_file_qua_6mb_bi_loai_kem_canh_bao():
    oversized = "data:application/pdf;base64," + base64.b64encode(b"x" * (7 * 1024 * 1024)).decode()
    files = [{"name": "to-khai.pdf", "type": "application/pdf", "dataUrl": oversized}]
    attachments, warnings, classified = planner.build_plan_items(files, _ocr(["to-khai.pdf"]), {0: "to_khai_de_nghi"})

    assert attachments == []
    assert "6 MB" in warnings[0]
    assert classified[0]["skipped"] is True


def test_ten_chu_the_cccd_cung_dong_va_khong_doc_duoc():
    assert planner._identity_holder_name("Họ, chữ đệm và tên khai sinh / Full name: NGUYỄN THỊ C\n") == "Nguyễn Thị C"
    assert planner._identity_holder_name("CĂN CƯỚC\nSố định danh cá nhân: 012000000001") is None


# ---------------------------------------------------------------- registry


def test_registry_va_ke_khai_links_cung_key():
    procedure = get_procedure(KEY)

    assert procedure is not None
    assert procedure["label"].startswith("[Lai Châu]")
    assert procedure["hasAttachmentStep"] is True
    assert procedure["detect"]["urlScope"] == ["laichau.gov.vn"]
    assert procedure["detect"]["textPriority"] is True
    assert "6 MB" in procedure["uploadHint"]
    assert callable(get_pipeline(KEY))
    assert callable(get_attach_pipeline(KEY))

    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "2.002862"
