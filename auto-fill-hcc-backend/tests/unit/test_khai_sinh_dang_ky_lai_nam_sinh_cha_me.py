"""Đăng ký lại khai sinh: năm sinh cha/mẹ trên tờ khai viết tay bị OCR đọc lệch (mẹ "trẻ hơn" con) không được xoá
trắng cả khối mẹ mà tờ khai đã ghi rõ."""
from app.pipelines.khai_sinh_dang_ky_lai.process import reason

PREFIX = reason._DECLARATION_BASIS_PREFIX
CON = "Họ tên: Nguyễn Thị A\nNgày sinh: 24/02/1962\nGiới tính: Nữ\nTrạng thái: còn sống"


def _me(year, basis=PREFIX + " mục người mẹ."):
    return (f"Họ tên: Lê Thị B\nSố CCCD/CMND: Không xác định\nNgày sinh: {year}\nGiới tính: Nữ\nDân tộc: Kinh\n"
            f"Trạng thái: đã chết\nCăn cứ phân vai: {basis}")


def test_cuu_nam_sinh_me_bang_ket_qua_agent_phan_vai():
    out = reason._validate_family_sections({"con": CON, "me": _me("1981")}, (), {"me": _me("1935", "Bản cam đoan")})
    assert reason._labeled_value(out["me"], "Ngày sinh") == "1935"
    assert reason._labeled_value(out["me"], "Họ tên") == "Lê Thị B"


def test_khong_cuu_duoc_thi_giu_khoi_me_tren_to_khai_nam_sinh_dung_ocr():
    out = reason._validate_family_sections({"con": CON, "me": _me("1981")}, (), {})
    assert reason._labeled_value(out["me"], "Ngày sinh") == "1981"
    assert reason._labeled_value(out["me"], "Dân tộc") == "Kinh"
    assert reason._labeled_value(out["me"], reason._GENERATION_MISMATCH_LABEL)


def test_khoi_khong_tu_nhan_to_khai_sai_the_he_van_xoa():
    out = reason._validate_family_sections({"con": CON, "me": _me("1981", "Suy theo thế hệ")}, (), {})
    assert reason._is_unknown(out["me"])


def test_nam_sinh_trich_xuat_phi_ly_lay_theo_khoi_vai_hoac_bo():
    fields = [{"name": "Subject_BirthDate", "value": "24/02/1962"},
              {"name": "Mother_BirthDateOrYear", "value": "1981"},
              {"name": "Father_BirthDateOrYear", "value": "1990"}]
    context = f"<con>\n{CON}\n</con>\n<me>\n{_me('1935')}\n</me>\n<cha>\nHọ tên: X\nNgày sinh: Không xác định\n</cha>"
    out = {f["name"]: f["value"] for f in reason._parent_birth_from_context(fields, context)}
    assert out["Mother_BirthDateOrYear"] == "1935" and "Father_BirthDateOrYear" not in out


def test_ngay_sinh_day_du_cung_nam_thay_nam_sinh_to_khai():
    death = "Họ tên: Lê Thị B\nSố CCCD/CMND: Không xác định\nNgày sinh: 25/11/1945\nTrạng thái: đã chết"
    merged = reason._merge_role_section(_me("1945"), death)
    assert reason._labeled_value(merged, "Ngày sinh") == "25/11/1945"
    # Khác năm → giữ theo tờ khai.
    assert reason._labeled_value(reason._merge_role_section(_me("1946"), death), "Ngày sinh") == "1946"


def test_trich_luc_khai_tu_khong_lay_so_dinh_danh_cua_trang_ghep_sau():
    text = ("TRÍCH LỤC KHAI TỬ\nHọ, chữ đệm, tên: NGUYỄN VĂN C\nNgày, tháng, năm sinh: 01/01/1938\n"
            "Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam\nSố định danh cá nhân:\nGiấy tờ tùy thân:\n"
            "PHIẾU TỪ CHỐI TIẾP NHẬN GIẢI QUYẾT HỒ SƠ\nSố định danh cá nhân/tổ chức: 001182000001\n")
    person = reason._person_from_document({"name": "x", "text": text})
    assert "001182000001" not in person["section"]
    same_line = text.replace("Số định danh cá nhân:\n", "Số định danh cá nhân: 001038000002\n")
    assert "001038000002" in reason._person_from_document({"name": "x", "text": same_line})["section"]


def test_nam_sinh_agent_chi_co_nam_lay_ngay_du_cung_nam_tu_khoi_vai():
    fields = [{"name": "Subject_BirthDate", "value": "24/02/1962"},
              {"name": "Mother_BirthDateOrYear", "value": "1935"},
              {"name": "Father_BirthDateOrYear", "value": "1930"}]
    context = (f"<con>\n{CON}\n</con>\n<me>\n{_me('12/03/1935')}\n</me>\n"
               "<cha>\nHọ tên: X\nNgày sinh: 01/01/1931\n</cha>")
    out = {f["name"]: f["value"] for f in reason._parent_birth_from_context(fields, context)}
    assert out["Mother_BirthDateOrYear"] == "12/03/1935" and out["Father_BirthDateOrYear"] == "1930"
