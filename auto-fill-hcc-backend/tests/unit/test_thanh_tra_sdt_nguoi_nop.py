"""Thanh tra định danh người nộp — số điện thoại (tư pháp cổng DVC mới): nhận chủ của số theo chỗ ghi trên giấy."""
from app.pipelines._shared.thanh_tra import sdt_nguoi_nop as t
from app.pipelines._shared.thanh_tra.ho_so import Case


def _ctx(name="Nguyễn Văn An", present="Có", role="Người yêu cầu"):
    return f"<nguoi_nop>\nHọ tên: {name}\nSố định danh: 001080000001\nCó trong hồ sơ: {present}\nVai trong hồ sơ: {role}\n</nguoi_nop>"


def _find(text, current=None, **ctx):
    case = Case([{"name": "a.pdf", "text": text}], _ctx(**ctx), {t.FIELD: current}, {})
    found = t.phone_findings(t.INSPECTOR, case)
    return found[0].values[t.FIELD] if found else None


_TO_KHAI = """TỜ KHAI ĐĂNG KÝ KHAI SINH
Họ, chữ đệm, tên người yêu cầu: NGUYỄN VĂN AN ĐT: 0912 345 678
Giấy tờ tùy thân: CCCD số 001080000001
"""
_KY_TEN = """Làm tại: phường Một, ngày 01 tháng 01 năm 2026
Người yêu cầu
(Ký, ghi rõ họ, chữ đệm, tên)
Nguyễn Văn An
0987 654 321
"""
_UY_QUYEN = """GIẤY ỦY QUYỀN
I. Bên ủy quyền:
Họ tên: Trần Thị Bình
Điện thoại: 0911111111
II. Bên được ủy quyền:
Họ tên: Nguyễn Văn An
Số CCCD: 001080000001
Điện thoại: 0922222222
"""


def test_so_cung_dong_ho_ten_nguoi_nop_bo_sung_khi_trong():
    assert _find(_TO_KHAI) == "0912345678"


def test_so_viet_duoi_chu_ky_nguoi_nop():
    assert _find(_KY_TEN) == "0987654321"


def test_giay_uy_quyen_lay_so_ben_duoc_uy_quyen_thay_so_nguoi_khac():
    assert _find(_UY_QUYEN, current="0911111111", role="Người được ủy quyền") == "0922222222"


def test_khong_de_xuat_khi_da_dung_hoac_nguoi_nop_khong_co_trong_ho_so():
    assert _find(_TO_KHAI, current="0912345678") is None
    assert _find(_TO_KHAI, present="Không") is None


def test_so_cccd_va_so_nguoi_khac_khong_phai_sdt_nguoi_nop():
    assert _find("Giấy tờ tùy thân: CCCD số 0240 850 131 54\nHọ tên: Nguyễn Văn An") is None
    assert _find("Họ tên: Trần Thị Bình\nSố điện thoại: 0933333333") is None


def test_nhan_dien_thoai_so_van_la_sdt():
    text = "Người yêu cầu\n(Ký, ghi rõ họ, chữ đệm, tên)\nNguyễn Văn An\nSố lượng: ....bản\nĐiện thoại số: 0905 123 456"
    assert _find(text) == "0905123456"


_TO_KHAI_SO_DAU_TRANG = """0987 654 321
TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH
Họ, chữ đệm, tên người yêu cầu: Nguyễn Văn An
Giấy tờ tùy thân: CCCD số 001080000001
Người yêu cầu
(Ký, ghi rõ họ, chữ đệm, tên)
An
"""


def test_so_dung_rieng_tren_to_khai_cua_nguoi_nop_la_so_nguoi_yeu_cau():
    assert _find(_TO_KHAI_SO_DAU_TRANG) == "0987654321"
    # Chữ ký chỉ ghi tên gọi, số viết ngay dưới.
    assert _find(_TO_KHAI_SO_DAU_TRANG.replace("0987 654 321\n", "") + "0987 654 321\n") == "0987654321"


def test_so_dung_rieng_tren_to_khai_cua_nguoi_khac_hoac_nguoi_nop_khong_la_nguoi_yeu_cau_thi_bo():
    other = _TO_KHAI_SO_DAU_TRANG.replace("Nguyễn Văn An", "Trần Thị Bình")
    assert _find(other) is None
    assert _find(_TO_KHAI_SO_DAU_TRANG, role="Người được ủy quyền") is None


def test_so_ocr_ghep_vao_dong_in_san_tren_to_khai_cua_nguoi_nop():
    text = _TO_KHAI_SO_DAU_TRANG.replace("0987 654 321\n", "") + "Đề nghị cấp bản sao: Có\nChú thích: 0987654321\n"
    assert _find(text) == "0987654321"


def test_so_cccd_rot_mot_chu_so_tren_to_khai_khong_thanh_sdt():
    text = _TO_KHAI_SO_DAU_TRANG.replace("0987 654 321\n", "") + "Đề nghị cấp bản sao: Có\nGhi chú 02409700185\n"
    assert _find(text) is None
