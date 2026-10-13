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


def test_khong_cuu_duoc_thi_giu_khoi_me_tren_to_khai_chi_bo_nam_sinh():
    out = reason._validate_family_sections({"con": CON, "me": _me("1981")}, (), {})
    assert reason._labeled_value(out["me"], "Ngày sinh") == "Không xác định"
    assert reason._labeled_value(out["me"], "Dân tộc") == "Kinh"


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
