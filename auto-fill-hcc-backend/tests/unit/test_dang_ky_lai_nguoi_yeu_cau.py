"""Khối "Thông tin người yêu cầu" của thủ tục đăng ký lại khai sinh.

Luồng bắt buộc: chốt ô tích "(5) Quan hệ với người được khai sinh" TRƯỚC, rồi mới điền nhân
thân theo đúng vai đã tick. Ưu tiên tờ khai; không có tờ khai thì luôn fallback CCCD của con.
"""

from app.pipelines.khai_sinh_dang_ky_lai.process import mapper

SUBJECT = {
    "Subject_FullName": "NGUYỄN THỊ HOÀI MINH",
    "Subject_BirthDate": "17/11/1976",
    "Subject_Gender": "Nữ",
    "Subject_Ethnicity": "Kinh",
    "Subject_IdNumber": "012176000644",
    "Subject_IdIssueDate": "25/04/2021",
    "Subject_IdIssuePlace": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "Subject_ResidenceDomestic": {
        "quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Phường Đoàn Kết", "diaChi": "Tổ 2",
    },
}
FATHER = {
    "Father_FullName": "TRẦN THÀNH CÔNG",
    "Father_IdNumber": "025203007360",
    "Father_IdIssueDate": "12/06/2021",
    "Father_Ethnicity": "Mông",
    "Father_ResidenceDomestic": {"quocGia": "Việt Nam", "tinh": "Phú Thọ", "diaChi": "Khu 2"},
}
DECLARATION = {"Requester_SourceDocumentTitle": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH"}


def _context(to_khai: str, vai: str = "không xác định") -> str:
    return (
        "<phan_vai_da_xac_dinh>\n"
        f"<nguoi_yeu_cau>\nHọ tên: x\nVai trò đồng thời: {vai}\n</nguoi_yeu_cau>\n"
        "<con>\nHọ tên: NGUYỄN THỊ HOÀI MINH\n</con>\n"
        "<me>\nHọ tên: Không xác định\n</me>\n"
        "<cha>\nHọ tên: TRẦN THÀNH CÔNG\n</cha>\n"
        "<dang_ky_khai_sinh_truoc_day>\nCó tài liệu khai sinh hợp lệ: Có\n"
        "</dang_ky_khai_sinh_truoc_day>\n"
        f"<to_khai_dang_ky_lai>\nCó tờ khai đăng ký lại khai sinh: {to_khai}\n"
        "</to_khai_dang_ky_lai>\n"
        "</phan_vai_da_xac_dinh>"
    )


def _enrich(values: dict, context: str) -> list[dict]:
    fields = [{"name": name, "value": value} for name, value in values.items()]
    return mapper.enrich(fields, {"_reasoning_context": context})


def _by_name(out: list[dict]) -> dict:
    return {field["name"]: field for field in out}


def test_quan_he_duoc_tick_truoc_moi_field_nguoi_yeu_cau():
    out = _enrich(SUBJECT, _context("Không"))
    names = [field["name"] for field in out]
    assert names.index("QuanHe") < names.index("HoVaTenC")
    assert names.index("QuanHe") < names.index("nycNoiCuTru_TrongNuoc")


def test_khong_co_to_khai_thi_fallback_cccd_cua_con():
    d = _by_name(_enrich(SUBJECT, _context("Không")))

    assert d["QuanHe"]["value"] == "BanThan"
    assert d["QuanHe"]["comp"] == "x-radio"
    assert d["HoVaTenC"]["value"] == "NGUYỄN THỊ HOÀI MINH"
    assert d["SoDinhDanhC"]["value"] == "012176000644"
    assert d["SoGiayToDinhDanhC"]["value"] == "012176000644"
    assert d["LoaiGiayToDinhDanhC"]["value"] == "Căn cước công dân"
    assert d["NgayCapDDC"]["value"] == "25/04/2021"
    assert d["nycNoiCuTru_TrongNuoc"]["value"]["tinh"] == "Lai Châu"
    assert d["DanTocC"]["value"] == "Kinh"


def test_khong_co_to_khai_van_uu_tien_con_du_ho_so_co_cha():
    """Cổng neo người yêu cầu vào cha, nhưng không có tờ khai thì vẫn tick Bản thân + CCCD con."""
    d = _by_name(_enrich({**SUBJECT, **FATHER}, _context("Không", vai="cha")))

    assert d["QuanHe"]["value"] == "BanThan"
    assert d["HoVaTenC"]["value"] == "NGUYỄN THỊ HOÀI MINH"
    assert d["SoDinhDanhC"]["value"] == "012176000644"


def test_to_khai_ghi_ban_than_thi_tick_ban_than():
    values = {
        **SUBJECT, **FATHER, **DECLARATION,
        "Requester_RelationToSubject": "Bản thân",
        "Requester_FullName": "NGUYỄN THỊ HOÀI MINH",
    }
    d = _by_name(_enrich(values, _context("Có")))

    assert d["QuanHe"]["value"] == "BanThan"
    # Tờ khai thiếu số/ngày cấp → lấy bù từ CCCD của chính người đó, không lấy của cha.
    assert d["HoVaTenC"]["value"] == "NGUYỄN THỊ HOÀI MINH"
    assert d["SoDinhDanhC"]["value"] == "012176000644"
    assert d["nycNoiCuTru_TrongNuoc"]["value"]["tinh"] == "Lai Châu"


def test_to_khai_ghi_cha_thi_tick_cha_va_lay_thong_tin_cha():
    values = {**SUBJECT, **FATHER, **DECLARATION, "Requester_RelationToSubject": "Cha"}
    d = _by_name(_enrich(values, _context("Có", vai="cha")))

    assert d["QuanHe"]["value"] == "ChaDe"
    assert d["HoVaTenC"]["value"] == "TRẦN THÀNH CÔNG"
    assert d["SoDinhDanhC"]["value"] == "025203007360"
    assert d["nycNoiCuTru_TrongNuoc"]["value"]["tinh"] == "Phú Thọ"
    assert d["DanTocC"]["value"] == "Mông"


def test_to_khai_ghi_nguoi_thu_ba_thi_tick_khac_va_khong_bia_dan_toc():
    values = {
        **SUBJECT, **DECLARATION,
        "Requester_RelationToSubject": "Khác",
        "Requester_Relationship": "Chị dâu",
        "Requester_FullName": "LÊ THỊ B",
        "Requester_IdNumber": "001180000111",
        "Requester_IdIssueDate": "01/02/2022",
    }
    d = _by_name(_enrich(values, _context("Có")))

    assert d["QuanHe"]["value"] == "Khac"
    assert d["HoVaTenC"]["value"] == "LÊ THỊ B"
    assert d["SoDinhDanhC"]["value"] == "001180000111"
    # Người thứ ba không có nguồn dân tộc trong hồ sơ → không mượn của con/cha/mẹ.
    assert "DanTocC" not in d


def test_to_khai_khong_ghi_quan_he_thi_suy_tu_nhan_than():
    values = {**SUBJECT, **DECLARATION, "Requester_FullName": "NGUYỄN THỊ HOÀI MINH"}
    d = _by_name(_enrich(values, _context("Có")))

    assert d["QuanHe"]["value"] == "BanThan"
    assert d["SoDinhDanhC"]["value"] == "012176000644"


def test_khong_co_nhan_than_con_thi_moi_dung_mo_neo_cha_cua_cong():
    d = _by_name(_enrich(FATHER, _context("Không", vai="cha")))

    assert d["QuanHe"]["value"] == "ChaDe"
    assert d["HoVaTenC"]["value"] == "TRẦN THÀNH CÔNG"


def test_ho_so_trong_van_tick_ban_than_nhung_danh_dau_la_mac_dinh():
    d = _by_name(_enrich({}, ""))

    assert d["QuanHe"]["value"] == "BanThan"
    assert d["QuanHe"].get("default") is True
    assert "HoVaTenC" not in d


def test_canonical_relation_khong_nuot_chau_thanh_cha():
    assert mapper._canonical_relation("Bản thân") == "BanThan"
    assert mapper._canonical_relation("BanThan") == "BanThan"
    assert mapper._canonical_relation("Tự khai") == "BanThan"
    assert mapper._canonical_relation("Cha") == "ChaDe"
    assert mapper._canonical_relation("ChaDe") == "ChaDe"
    assert mapper._canonical_relation("Bố đẻ") == "ChaDe"
    assert mapper._canonical_relation("Mẹ") == "MeDe"
    assert mapper._canonical_relation("Mẹ đẻ") == "MeDe"
    # "Cháu"/"Em" chỉ khác "Cha"/"Mẹ" ở ranh giới từ — không được quy nhầm về cha/mẹ.
    assert mapper._canonical_relation("Cháu nội") == "Khac"
    assert mapper._canonical_relation("Em ruột") == "Khac"
    assert mapper._canonical_relation("Chị dâu") == "Khac"
    assert mapper._canonical_relation("Không xác định") == ""
    assert mapper._canonical_relation("") == ""


def test_reason_chi_nhan_dien_to_khai_dang_ky_lai_khai_sinh():
    from app.pipelines.khai_sinh_dang_ky_lai.process import reason

    documents = [
        {"name": "cccd.jpg", "text": "CĂN CƯỚC CÔNG DÂN\nHọ và tên: NGUYỄN VĂN A"},
        {"name": "gks.pdf", "text": "GIẤY KHAI SINH\nBản chính"},
        {"name": "trich-luc.pdf", "text": "TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH"},
    ]
    assert reason._declaration_source_names(documents) == []

    documents.append(
        {"name": "to-khai.pdf", "text": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH\nQuan hệ với người được khai sinh: Bản thân"}
    )
    assert reason._declaration_source_names(documents) == ["to-khai.pdf"]


# ===== Bước tư duy quan hệ ở reason.py (trước khi tick ô) =====

def _reason():
    from app.pipelines.khai_sinh_dang_ky_lai.process import reason
    return reason


def _raw(ket_luan: str, can_cu: str = "Tờ khai ghi rõ.") -> str:
    return (
        "<quan_he_nguoi_yeu_cau>\n"
        "Người yêu cầu: NGUYỄN THỊ HOÀI MINH\n"
        "Người được đăng ký lại khai sinh: NGUYỄN THỊ HOÀI MINH\n"
        f"Kết luận: {ket_luan}\n"
        f"Căn cứ: {can_cu}\n"
        "</quan_he_nguoi_yeu_cau>"
    )


_KNOWN = "Họ tên: NGUYỄN VĂN A\nSố CCCD/CMND: 012176000644\nTrạng thái: còn sống"
_UNKNOWN = "Họ tên: Không xác định"


def test_reason_quy_ket_luan_quan_he_ve_nhan_chuan():
    norm = _reason()._normalized_relation
    assert norm("bản thân") == "bản thân"
    assert norm("Tự khai") == "bản thân"
    assert norm("cha") == "cha"
    assert norm("Bố") == "cha"
    assert norm("mẹ") == "mẹ"
    assert norm("khác") == "khác"
    assert norm("không xác định") == ""
    assert norm("") == ""


def test_reason_giu_ket_luan_cha_khi_co_to_khai_va_khoi_cha_ro_rang():
    sections = {"con": _KNOWN, "cha": _KNOWN, "me": _UNKNOWN}
    value, _ = _reason()._validated_relation(_raw("cha"), sections, has_declaration=True)
    assert value == "cha"


def test_reason_khong_co_to_khai_thi_ep_ve_ban_than():
    """Chỉ có CCCD (kể cả CCCD cha) → nghiệp vụ mặc định là tự đi làm cho chính mình."""
    sections = {"con": _KNOWN, "cha": _KNOWN, "me": _UNKNOWN}
    value, basis = _reason()._validated_relation(_raw("cha"), sections, has_declaration=False)
    assert value == "bản thân"
    assert "không có tờ khai" in basis.lower()


def test_reason_bo_ket_luan_cha_khi_khoi_cha_khong_xac_dinh():
    sections = {"con": _KNOWN, "cha": _UNKNOWN, "me": _UNKNOWN}
    value, basis = _reason()._validated_relation(_raw("cha"), sections, has_declaration=True)
    assert value == "bản thân"          # còn <con> nên rơi về mặc định nghiệp vụ
    assert "<cha> Không xác định" in basis


def test_reason_khong_co_con_va_khong_co_can_cu_thi_de_khong_xac_dinh():
    sections = {"con": _UNKNOWN, "cha": _UNKNOWN, "me": _UNKNOWN}
    value, _ = _reason()._validated_relation(_raw("không xác định"), sections, has_declaration=False)
    assert value == "không xác định"


def test_mapper_tick_theo_ket_luan_cua_buoc_phan_vai():
    """Không có Requester_RelationToSubject nhưng reason đã chốt 'cha' → tick ChaDe."""
    context = (
        "<phan_vai_da_xac_dinh>\n"
        "<nguoi_yeu_cau>\nHọ tên: x\nVai trò đồng thời: không xác định\n</nguoi_yeu_cau>\n"
        "<con>\nHọ tên: NGUYỄN THỊ HOÀI MINH\n</con>\n"
        "<me>\nHọ tên: Không xác định\n</me>\n"
        "<cha>\nHọ tên: TRẦN THÀNH CÔNG\n</cha>\n"
        "<quan_he_nguoi_yeu_cau>\nKết luận: cha\nCăn cứ: Tờ khai ghi Cha.\n"
        "</quan_he_nguoi_yeu_cau>\n"
        "<to_khai_dang_ky_lai>\nCó tờ khai đăng ký lại khai sinh: Có\n</to_khai_dang_ky_lai>\n"
        "</phan_vai_da_xac_dinh>"
    )
    d = _by_name(_enrich({**SUBJECT, **FATHER}, context))

    assert d["QuanHe"]["value"] == "ChaDe"
    assert d["HoVaTenC"]["value"] == "TRẦN THÀNH CÔNG"


def test_mapper_ket_luan_ban_than_thang_khi_khong_co_to_khai():
    context = (
        "<phan_vai_da_xac_dinh>\n"
        "<con>\nHọ tên: NGUYỄN THỊ HOÀI MINH\n</con>\n"
        "<quan_he_nguoi_yeu_cau>\nKết luận: bản thân\nCăn cứ: Hồ sơ chỉ có CCCD.\n"
        "</quan_he_nguoi_yeu_cau>\n"
        "<to_khai_dang_ky_lai>\nCó tờ khai đăng ký lại khai sinh: Không\n</to_khai_dang_ky_lai>\n"
        "</phan_vai_da_xac_dinh>"
    )
    d = _by_name(_enrich({**SUBJECT, **FATHER}, context))

    assert d["QuanHe"]["value"] == "BanThan"
    assert d["HoVaTenC"]["value"] == "NGUYỄN THỊ HOÀI MINH"
