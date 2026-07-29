"""Cổng suy luận tất định cho đăng ký lại khai sinh: chốt con/cha/mẹ đúng dù LLM roster lỗi.

Ca gốc gây bug: hồ sơ có CCCD (con) + giấy KẾT HÔN + 2 giấy KHAI TỬ (cha, mẹ). Lần chạy xấu,
LLM tưởng giấy kết hôn là khai sinh -> map chồng->cha, vợ->mẹ, bỏ 2 khai tử. Cổng phải sửa lại.
"""

from app.pipelines.khai_sinh_dang_ky_lai.process import reason


def _roster_bad_case() -> dict:
    """Roster LLM trả về ở lần chạy XẤU: chồng bị gán 'cha', vợ (chính là con) bị gán 'me'."""
    return {
        "documents": [
            {"name": "cccd.pdf", "loai": "cccd", "ve_ai": "LƯƠNG THỊ KHOẢN"},
            {"name": "gks.pdf", "loai": "ket_hon", "ve_ai": "HOÀNG VĂN KHANH"},
            {"name": "khai tu bo.jpeg", "loai": "khai_tu", "ve_ai": "LƯƠNG VĂN DẦU"},
            {"name": "khai tu me.jpeg", "loai": "khai_tu", "ve_ai": "HỒ THỊ SIÊU"},
        ],
        "persons": [
            {"ten": "LƯƠNG THỊ KHOẢN", "gioi_tinh": "Nữ", "nam_sinh": "1987",
             "so_dinh_danh": "012187003358", "da_chet": False, "vai_tro": "me",
             "nguon": ["cccd.pdf", "gks.pdf"]},
            {"ten": "HOÀNG VĂN KHANH", "gioi_tinh": "Nam", "nam_sinh": "1979",
             "so_dinh_danh": "", "da_chet": False, "vai_tro": "cha", "nguon": ["gks.pdf"]},
            {"ten": "LƯƠNG VĂN DẦU", "gioi_tinh": "Nam", "nam_sinh": "1971",
             "so_dinh_danh": "", "da_chet": False, "vai_tro": "khac", "nguon": ["khai tu bo.jpeg"]},
            {"ten": "HỒ THỊ SIÊU", "gioi_tinh": "Nữ", "nam_sinh": "1951",
             "so_dinh_danh": "", "da_chet": False, "vai_tro": "khac", "nguon": ["khai tu me.jpeg"]},
        ],
    }


def _role(roster: dict, ten: str) -> dict:
    return next(p for p in roster["persons"] if p["ten"] == ten)


def test_gate_khai_tu_thanh_cha_me_da_chet():
    r = reason._apply_gate(_roster_bad_case(), {})
    assert _role(r, "LƯƠNG VĂN DẦU")["vai_tro"] == "cha"
    assert _role(r, "LƯƠNG VĂN DẦU")["da_chet"] is True
    assert _role(r, "HỒ THỊ SIÊU")["vai_tro"] == "me"
    assert _role(r, "HỒ THỊ SIÊU")["da_chet"] is True


def test_gate_chong_ket_hon_khong_thanh_cha():
    r = reason._apply_gate(_roster_bad_case(), {})
    # HOÀNG VĂN KHANH chỉ từ giấy kết hôn + đã có cha từ khai tử -> hạ về "chong".
    assert _role(r, "HOÀNG VĂN KHANH")["vai_tro"] == "chong"


def test_gate_con_la_nguoi_co_cccd_con_song():
    r = reason._apply_gate(_roster_bad_case(), {})
    # KHOẢN bị LLM gán nhầm "me" nhưng SIÊU (khai tử, Nữ) đã chiếm vai mẹ; KHOẢN còn sống + có CCCD -> con.
    assert _role(r, "LƯƠNG THỊ KHOẢN")["vai_tro"] == "con"


def test_render_ghim_vai_tro_va_canh_bao():
    ctx = reason._render(reason._apply_gate(_roster_bad_case(), {}))
    assert "con): LƯƠNG THỊ KHOẢN" in ctx
    assert "CHA: LƯƠNG VĂN DẦU (đã chết)" in ctx
    assert "MẸ: HỒ THỊ SIÊU (đã chết)" in ctx
    assert "HOÀNG VĂN KHANH là chồng" in ctx
    # Không mỏ neo formContext -> người yêu cầu để mặc định.
    assert "NGƯỜI YÊU CẦU: không xác định" in ctx
    # Lưu ý số đăng ký khai sinh trước đây: bỏ qua giấy KẾT HÔN và khai tử.
    assert "PreviousRegistration_Number" in ctx
    assert "KẾT HÔN" in ctx and "BỎ QUA" in ctx


def test_gate_gender_lech_thi_xoa_vai():
    roster = {
        "documents": [{"name": "a.pdf", "loai": "cccd", "ve_ai": "NGUYỄN VĂN A"}],
        "persons": [{"ten": "NGUYỄN VĂN A", "gioi_tinh": "Nam", "nam_sinh": "1990",
                     "so_dinh_danh": "1", "da_chet": False, "vai_tro": "me", "nguon": ["a.pdf"]}],
    }
    r = reason._apply_gate(roster, {})
    # Nam mà bị gán "me" -> xóa vai (không điền bừa), rồi thành con vì là người còn sống có CCCD duy nhất.
    assert _role(r, "NGUYỄN VĂN A")["vai_tro"] == "con"


def _roster_cccd_parents() -> dict:
    """Khai sinh con + 2 CCCD (bố/mẹ). Khai sinh KHÔNG ghi tên cha; LLM tag lỏng (khac) -> cổng phải cứu."""
    return {
        "documents": [
            {"name": "cccd bố.pdf", "loai": "cccd", "ve_ai": "HÀNG A SINH"},
            {"name": "cccd mẹ.pdf", "loai": "cccd", "ve_ai": "QUẢNG THỊ PHƯƠNG"},
            {"name": "Giấy khai sinh.pdf", "loai": "khai_sinh_cu", "ve_ai": "QUÀNG CHẤN PHONG"},
        ],
        "persons": [
            {"ten": "HÀNG A SINH", "gioi_tinh": "Nam", "nam_sinh": "1997",
             "so_dinh_danh": "012097006327", "da_chet": False, "vai_tro": "khac", "nguon": ["cccd bố.pdf"]},
            {"ten": "QUẢNG THỊ PHƯƠNG", "gioi_tinh": "Nữ", "nam_sinh": "1998",
             "so_dinh_danh": "011198002034", "da_chet": False, "vai_tro": "khac", "nguon": ["cccd mẹ.pdf"]},
            {"ten": "QUÀNG CHẤN PHONG", "gioi_tinh": "Nam", "nam_sinh": "2020",
             "so_dinh_danh": "", "da_chet": False, "vai_tro": "khac", "nguon": ["Giấy khai sinh.pdf"]},
        ],
    }


def test_gate_cccd_by_filename_and_gender():
    """Khai sinh thiếu tên cha -> gán CCCD bố (Nam, tên file 'cccd bố') = cha, CCCD mẹ = mẹ, con = trẻ có khai sinh."""
    r = reason._apply_gate(_roster_cccd_parents(), {})
    assert _role(r, "HÀNG A SINH")["vai_tro"] == "cha"
    assert _role(r, "QUẢNG THỊ PHƯƠNG")["vai_tro"] == "me"
    assert _role(r, "QUÀNG CHẤN PHONG")["vai_tro"] == "con"


def test_render_cccd_parents_nguon():
    ctx = reason._render(reason._apply_gate(_roster_cccd_parents(), {}))
    assert "CHA: HÀNG A SINH — nguồn: cccd bố.pdf" in ctx
    assert "MẸ: QUẢNG THỊ PHƯƠNG — nguồn: cccd mẹ.pdf" in ctx
    assert "con): QUÀNG CHẤN PHONG" in ctx


def _roster_three_cccd() -> dict:
    """Người lớn tự đăng ký lại khai sinh: CCCD của chính mình + CCCD bố + CCCD mẹ (không có khai sinh).
    Bẫy: tên file "cccd chà" (tên người = CHÀ) gấp dấu thành "cccd cha" — KHÔNG được nhầm là bố."""
    return {
        "documents": [
            {"name": "cccd bo.pdf", "loai": "cccd", "ve_ai": "LÈNG VĂN PỦN"},
            {"name": "cccd chà.pdf", "loai": "cccd", "ve_ai": "LÈNG VĂN CHÀ"},
            {"name": "cccd mẹ.pdf", "loai": "cccd", "ve_ai": "LÔ THỊ TỆT"},
        ],
        "persons": [
            {"ten": "LÈNG VĂN PỦN", "gioi_tinh": "Nam", "nam_sinh": "1964",
             "so_dinh_danh": "012064000527", "da_chet": False, "vai_tro": "khac", "nguon": ["cccd bo.pdf"]},
            {"ten": "LÈNG VĂN CHÀ", "gioi_tinh": "Nam", "nam_sinh": "1990",
             "so_dinh_danh": "012090004364", "da_chet": False, "vai_tro": "khac", "nguon": ["cccd chà.pdf"]},
            {"ten": "LÔ THỊ TỆT", "gioi_tinh": "Nữ", "nam_sinh": "1962",
             "so_dinh_danh": "012162000451", "da_chet": False, "vai_tro": "khac", "nguon": ["cccd mẹ.pdf"]},
        ],
    }


def test_gate_three_cccd_detects_con():
    """cccd bố→cha, cccd mẹ→mẹ, còn lại (CHÀ) = con; 'chà' KHÔNG bị nhầm thành 'cha'."""
    r = reason._apply_gate(_roster_three_cccd(), {})
    assert _role(r, "LÈNG VĂN PỦN")["vai_tro"] == "cha"
    assert _role(r, "LÔ THỊ TỆT")["vai_tro"] == "me"
    assert _role(r, "LÈNG VĂN CHÀ")["vai_tro"] == "con"


def test_gate_three_cccd_con_is_requester_banthan():
    """Người tự đăng ký (con) khớp formContext → vẫn là con, không bị loại khỏi con-fallback."""
    r = reason._apply_gate(
        _roster_three_cccd(),
        {"formContext": {"applicantFullname": "Lèng Văn Chà",
                         "applicantIdentityNumber": "012090004364"}},
    )
    assert _role(r, "LÈNG VĂN CHÀ")["vai_tro"] == "con"


def test_gate_requester_khop_formcontext():
    r = reason._apply_gate(
        _roster_bad_case(),
        {"formContext": {"applicantFullname": "LƯƠNG THỊ KHOẢN",
                         "applicantIdentityNumber": "012187003358"}},
    )
    assert _role(r, "LƯƠNG THỊ KHOẢN").get("_requester") is True
    ctx = reason._render(r)
    assert "NGƯỜI YÊU CẦU: LƯƠNG THỊ KHOẢN" in ctx
