"""Tên con liên thông: đọc ở "Dự định đặt tên con là", lọc ký hiệu đường kẻ điền tay."""

from app.pipelines.khai_sinh_lien_thong.process.mapper import _clean_child_name, enrich


def _values(fields):
    return {field["name"]: field["value"] for field in fields}


def test_ky_hieu_bam_hai_dau_ten_con_bi_cat():
    for raw, expect in (
        ("NGUYỄN VĂN A /", "NGUYỄN VĂN A"),
        ("/ NGUYỄN VĂN A", "NGUYỄN VĂN A"),
        ("... NGUYỄN VĂN A", "NGUYỄN VĂN A"),
        ("NGUYỄN VĂN A ......", "NGUYỄN VĂN A"),
        (": NGUYỄN VĂN A", "NGUYỄN VĂN A"),
        ("NGUYỄN VĂN A -", "NGUYỄN VĂN A"),
        ("(NGUYỄN VĂN A)", "NGUYỄN VĂN A"),
        ('"NGUYỄN VĂN A"', "NGUYỄN VĂN A"),
        ("•  Hoàng Bảo Nam …", "Hoàng Bảo Nam"),
    ):
        assert _clean_child_name(raw, "LÙ THỊ PÀ") == expect, raw


def test_gia_tri_chi_gom_ky_hieu_thi_coi_nhu_chua_dat_ten():
    for raw in ("/", "\\", "-", "...", ". / .", "…", "(...)", ":", "   ", ""):
        assert _clean_child_name(raw, "LÙ THỊ PÀ") == "", raw


def test_placeholder_va_ten_me_van_bi_chan_khi_co_ky_hieu_bao_quanh():
    assert _clean_child_name("... chưa đặt tên ...", "LÙ THỊ PÀ") == ""
    assert _clean_child_name("/ LÙ THỊ PÀ /", "LÙ THỊ PÀ") == ""


def test_giu_nguyen_dau_nhay_don_trong_ten_tay_nguyen():
    """Tên Cơ Ho/Chu Ru có nháy đơn thật ("K'Rajan") — không được coi là ký hiệu rác."""
    assert _clean_child_name("K'Rajan Ha Xuân", "LÙ THỊ PÀ") == "K'Rajan Ha Xuân"


def test_ky_hieu_khong_lot_vao_ho_chu_dem_ten_tren_form():
    values = _values(enrich([
        {"name": "Gcs_HoTenCon", "value": "/ Nguyễn Văn Bé ..."},
        {"name": "ThongTinMe_HoTen", "value": "Trần Thị Mẹ"},
        {"name": "ThongTinMe_SoDinhDanh", "value": "098765432109"},
    ]))

    assert (values["Ho"], values["ChuDem"], values["Ten"]) == ("NGUYỄN", "VĂN", "BÉ")


def test_to_khai_van_duoc_uu_tien_hon_giay_chung_sinh():
    values = _values(enrich([
        {"name": "Tk_HoTenCon", "value": "Nguyễn Bảo Khai"},
        {"name": "Gcs_HoTenCon", "value": "Nguyễn Chứng Sinh"},
        {"name": "ThongTinMe_HoTen", "value": "Trần Thị Mẹ"},
        {"name": "ThongTinMe_SoDinhDanh", "value": "098765432109"},
    ]))

    assert values["Ten"] == "KHAI"


def test_ho_so_gcs_dinh_nguyen_hoang_minh_tach_dung_ho_chu_dem_ten():
    """Giấy chứng sinh in sẵn dấu "/" trước chỗ viết tay: tên vẫn phải vào form."""
    values = _values(enrich([
        {"name": "Gcs_HoTenCon", "value": "/ ĐINH NGUYỄN HOÀNG MINH"},
        {"name": "Gcs_NgaySinhCon", "value": "18/08/2026"},
        {"name": "Gcs_GioiTinhCon", "value": "Nam"},
        {"name": "ThongTinMe_HoTen", "value": "NGUYỄN VŨ THÚY NGA"},
        {"name": "ThongTinMe_SoDinhDanh", "value": "068198006172"},
        {"name": "ThongTinBo_HoTen", "value": "ĐINH HỮU PHƯỚC"},
        {"name": "ThongTinBo_SoDinhDanh", "value": "070095001216"},
    ]))

    assert (values["Ho"], values["ChuDem"], values["Ten"]) == ("ĐINH", "NGUYỄN HOÀNG", "MINH")


def test_prompt_va_schema_khong_con_bao_bo_field_khi_gap_dau_gach_cheo():
    from app.pipelines.khai_sinh_lien_thong.process.prompt import EXTRA_RULES
    from app.pipelines.khai_sinh_lien_thong.process.schema import FIELDS

    desc = next(f for f in FIELDS if f["name"] == "Gcs_HoTenCon")["desc"]
    assert "KÝ HIỆU PHÂN CÁCH KHÔNG PHẢI LÀ" in EXTRA_RULES
    assert "ĐINH NGUYỄN HOÀNG MINH" in EXTRA_RULES
    assert "XOÁ ký hiệu ở hai đầu rồi mới xét" in desc
    # Luật cũ (bỏ hẳn field khi thấy "/") không được còn tồn tại ở dạng vô điều kiện.
    assert "Nếu sau nhãn là rỗng" not in EXTRA_RULES
    assert "Nếu sau nhãn là trống" not in desc


NL = chr(10)
_GCS_OCR = NL.join([
    "Giới tính của con: Nam Cân nặng (Gram): 3000",
    "Dự định đặt tên con là: / ĐINH NGUYỄN HOÀNG MINH",
    "Ghi chú:",
    "Tỉnh Lâm Đồng, Ngày 18 tháng 08 năm 2026",
])

# Đúng output LLM trả về cho hồ sơ này: KHÔNG có Gcs_HoTenCon vì model tưởng "/" là chưa đặt tên.
_LLM_FIELDS = [
    {"name": "Gcs_NgaySinhCon", "value": "18/08/2026"},
    {"name": "Gcs_GioiTinhCon", "value": "Nam"},
    {"name": "ThongTinMe_HoTen", "value": "NGUYỄN VŨ THÚY NGA"},
    {"name": "ThongTinMe_SoDinhDanh", "value": "068198006172"},
    {"name": "ThongTinBo_HoTen", "value": "ĐINH HỮU PHƯỚC"},
    {"name": "ThongTinBo_SoDinhDanh", "value": "070095001216"},
]


def test_vot_ten_con_tu_ocr_khi_llm_bo_sot_field():
    values = _values(enrich(_LLM_FIELDS, ocr_text=_GCS_OCR))

    assert (values["Ho"], values["ChuDem"], values["Ten"]) == ("ĐINH", "NGUYỄN HOÀNG", "MINH")


def test_khong_co_ocr_thi_giu_nguyen_hanh_vi_cu():
    values = _values(enrich(_LLM_FIELDS))

    assert "Ten" not in values


def test_llm_tra_ten_thi_khong_dung_ocr():
    """LLM là nguồn chính; OCR chỉ vớt khi LLM không cho tên nào dùng được."""
    values = _values(enrich(
        _LLM_FIELDS + [{"name": "Tk_HoTenCon", "value": "Nguyễn Bảo Khai"}],
        ocr_text=_GCS_OCR,
    ))

    assert values["Ten"] == "KHAI"


def test_vot_ocr_van_chan_placeholder_va_ten_me():
    from app.pipelines.khai_sinh_lien_thong.process.mapper import _child_name_from_ocr

    assert _child_name_from_ocr("Dự định đặt tên con là: /" + NL + "Ghi chú:") == ""
    assert _child_name_from_ocr("Dự định đặt tên con là:" + NL + "Ghi chú:") == ""
    # Placeholder được trả về nguyên văn nhưng _clean_child_name chặn lại ở bước sau.
    assert _values(enrich(
        _LLM_FIELDS,
        ocr_text="Dự định đặt tên con là: chưa đặt tên" + NL + "Ghi chú:",
    )).get("Ten") is None
    assert _values(enrich(
        _LLM_FIELDS,
        ocr_text="Dự định đặt tên con là: NGUYỄN VŨ THÚY NGA" + NL + "Ghi chú:",
    )).get("Ten") is None


def test_vot_ocr_nhan_bien_the_va_gia_tri_xuong_dong():
    from app.pipelines.khai_sinh_lien_thong.process.mapper import _child_name_from_ocr

    assert _child_name_from_ocr("Đặt tên con là: TRẦN GIA HÂN") == "TRẦN GIA HÂN"
    assert _child_name_from_ocr("Dự kiến đặt tên con: VŨ KHÁNH LINH") == "VŨ KHÁNH LINH"
    assert _child_name_from_ocr("Du dinh dat ten con la: NGUYEN VAN BE") == "NGUYEN VAN BE"
    assert _child_name_from_ocr(
        "Dự định đặt tên con là:" + NL + "   HOÀNG BẢO NAM" + NL + "Ghi chú:"
    ) == "HOÀNG BẢO NAM"
    assert _child_name_from_ocr("Dự định đặt tên con là: LÙ MINH ANH Cân nặng: 3200") == "LÙ MINH ANH"


def test_vot_ocr_khong_dinh_nham_dong_ten_me_hoac_so():
    from app.pipelines.khai_sinh_lien_thong.process.mapper import _child_name_from_ocr

    assert _child_name_from_ocr("Họ, chữ đệm, tên khai sinh của mẹ: NGUYỄN VŨ THÚY NGA") == ""
    assert _child_name_from_ocr("Giới tính của con: Nam") == ""
    assert _child_name_from_ocr("Dự định đặt tên con là: 3000") == ""
