"""near_match_ward() — gỡ lỗi OCR đọc lệch MỘT dấu trong tên xã, có ba lớp chặn."""
from app.pipelines._shared.area_remap import _off_by_one, near_match_ward


def test_lech_dung_mot_ky_tu_va_duy_nhat_mot_ung_vien():
    assert near_match_ward("Bắc Giang", "Xã Đông Lễ") == "Xã Hiệp Hòa"
    # Giấy cấp lại mang tỉnh MỚI nhưng vẫn ghi tên xã cũ đọc sai.
    assert near_match_ward("Bắc Ninh", "Xã Đông Lễ") == "Xã Hiệp Hòa"


def test_ten_doc_dung_khong_kich_hoat():
    """Khớp chính xác đã có các bảng tra lo; dò gần đúng chỉ chạy khi mọi bảng trượt."""
    assert near_match_ward("Bắc Giang", "Xã Đông Lỗ") == ""


def test_ten_qua_ngan_khong_do():
    # "thang" — một ký tự lệch là phần quá lớn của tên, dễ đụng sang xã khác.
    assert near_match_ward("Bắc Giang", "Thị trấn Thắng") == ""


def test_khong_do_ra_ngoai_pham_vi_tinh():
    assert near_match_ward("Lai Châu", "Xã Đông Lễ") == ""
    assert near_match_ward("", "Xã Đông Lễ") == ""
    assert near_match_ward("Bắc Giang", "") == ""


def test_lech_tu_hai_ky_tu_tro_len_khong_do():
    assert near_match_ward("Bắc Giang", "Xã Đằng Lễ") == ""


def test_off_by_one():
    assert _off_by_one("dong le", "dong lo")      # thay
    assert _off_by_one("dong lo", "dong los")     # thêm
    assert _off_by_one("dong los", "dong lo")     # bớt
    assert not _off_by_one("dong lo", "dong lo")  # bằng nhau
    assert not _off_by_one("dong le", "dang lo")  # lệch hai
    assert not _off_by_one("abc", "abcde")
