"""Trích lục hộ tịch: số định danh KHỚP số trên thẻ căn cước → lấy HỌ TÊN in trên thẻ.

Cùng quy tắc đã áp cho xác nhận tình trạng hôn nhân, nay cho cả hai khối của trích lục:
người yêu cầu (mục I) và người được đăng ký (mục II).

Tờ khai là bản VIẾT TAY nên OCR tên hay sai (rơi dấu, đọc nhầm chữ) và số cũng hay rơi mất một chữ
số. Thẻ căn cước là bản IN, và đó mới là tên/số phải khớp với CSDLQG về dân cư khi cổng đối chiếu.

Ranh giới phải giữ: số của HAI NGƯỜI KHÁC NHAU (đủ 12 chữ số mà lệch) thì không được mượn tên sang.
"""
from app.pipelines.trich_luc.process.mapper import enrich


def _run(options=None, **kv):
    fields = [{"name": k, "value": v} for k, v in kv.items()]
    return {f["name"]: f["value"] for f in enrich(fields, options)}


# --------------------------------------------------------------------------------------
# MỤC I — người yêu cầu (người đứng đăng ký)
# --------------------------------------------------------------------------------------

def test_muc_i_trung_so_thi_lay_ten_tren_the():
    out = _run(
        TkNyc_HoTen="NGUYEN THI HOA",              # OCR chữ viết tay, mất dấu
        TkNyc_SoGiayToTuyThan="036301012326",
        Nyc_HoTen="NGUYỄN THỊ HOÀ",                # bản in trên thẻ
        Nyc_SoDinhDanh="036301012326",
        HoTich_LoaiSuKien="birth",
        HoTich_HoTenNguoiDuocDangKy="TRẦN MINH KHOA",
        HoTich_SoDinhDanh="001210004567",
    )
    assert out["HoVaTenC"] == "NGUYỄN THỊ HOÀ"


def test_muc_i_ocr_roi_mot_chu_so_van_la_cung_nguoi():
    """Tờ khai ghi thiếu một chữ số → vẫn là chủ thẻ, lấy cả tên lẫn số theo thẻ."""
    out = _run(
        TkNyc_HoTen="NGUYEN THI HOA",
        TkNyc_SoGiayToTuyThan="03630101236",       # thiếu chữ "2" áp chót
        Nyc_HoTen="NGUYỄN THỊ HOÀ",
        Nyc_SoDinhDanh="036301012326",
        HoTich_LoaiSuKien="birth",
        HoTich_HoTenNguoiDuocDangKy="TRẦN MINH KHOA",
        HoTich_SoDinhDanh="001210004567",
    )
    assert out["HoVaTenC"] == "NGUYỄN THỊ HOÀ"
    assert out["SoDinhDanhC"] == "036301012326"


def test_muc_i_the_cua_nguoi_khac_thi_giu_ten_to_khai():
    """Ranh giới quan trọng nhất: khác số đủ 12 chữ số là hai người khác nhau."""
    out = _run(
        TkNyc_HoTen="PHAM TRUONG GIANG",
        TkNyc_SoGiayToTuyThan="036200002580",
        Nyc_HoTen="LÊ THỊ NGỌC BÍCH",
        Nyc_SoDinhDanh="036301012326",
        HoTich_LoaiSuKien="birth",
        HoTich_HoTenNguoiDuocDangKy="LÊ THỊ NGỌC BÍCH",
        HoTich_SoDinhDanh="036301012326",
    )
    assert out["HoVaTenC"] == "PHAM TRUONG GIANG"


# --------------------------------------------------------------------------------------
# MỤC II — người được đăng ký
# --------------------------------------------------------------------------------------

def test_muc_ii_trung_so_thi_lay_ten_tren_the():
    out = _run(
        HoTich_LoaiSuKien="birth",
        HoTich_HoTenNguoiDuocDangKy="NGUYEN THI HOA",   # tờ khai viết tay, mất dấu
        HoTich_SoDinhDanh="036301012326",
        ChuThe_HoTen="NGUYỄN THỊ HOÀ",                  # bản in trên thẻ
        ChuThe_SoDinhDanh="036301012326",
        ChuThe_NgaySinh="12/02/2000",
    )
    assert out["NDK_HoVaTen"] == "NGUYỄN THỊ HOÀ"
    assert out["NDK_SoDinhDanh"] == "036301012326"


def test_muc_ii_ocr_roi_mot_chu_so_van_la_cung_nguoi():
    out = _run(
        HoTich_LoaiSuKien="birth",
        HoTich_HoTenNguoiDuocDangKy="NGUYEN THI HOA",
        HoTich_SoDinhDanh="03630101236",                # thiếu chữ "2" áp chót
        ChuThe_HoTen="NGUYỄN THỊ HOÀ",
        ChuThe_SoDinhDanh="036301012326",
        ChuThe_NgaySinh="12/02/2000",
    )
    assert out["NDK_HoVaTen"] == "NGUYỄN THỊ HOÀ"
    assert out["NDK_SoDinhDanh"] == "036301012326"


def test_muc_ii_the_cua_nguoi_khac_thi_giu_ten_giay_ho_tich():
    out = _run(
        HoTich_LoaiSuKien="birth",
        HoTich_HoTenNguoiDuocDangKy="TRẦN VĂN NAM",
        HoTich_SoDinhDanh="001099000111",
        ChuThe_HoTen="NGUYỄN THỊ HOÀ",
        ChuThe_SoDinhDanh="036301012326",
    )
    assert out["NDK_HoVaTen"] == "TRẦN VĂN NAM"


def test_muc_ii_khong_co_so_thi_giu_thu_tu_cu():
    """Thiếu số một bên → không kết luận được cùng người → không mượn tên."""
    out = _run(
        HoTich_LoaiSuKien="birth",
        HoTich_HoTenNguoiDuocDangKy="LE VAN BINH",
        ChuThe_HoTen="LE VAN BINH",
        ChuThe_SoDinhDanh="036301012326",
    )
    assert out["NDK_HoVaTen"] == "LE VAN BINH"


# --------------------------------------------------------------------------------------
# Ngày sinh / giới tính / ngày-nơi cấp / tên đường cũng theo thẻ khi trùng số
# --------------------------------------------------------------------------------------

def test_muc_i_trung_so_thi_ngay_noi_cap_theo_the_va_sua_ten_duong():
    out = _run(
        TkNyc_HoTen="NGUYEN THI HOA",
        TkNyc_SoGiayToTuyThan="036301012326",
        TkNyc_NgayCapGiayToTuyThan="01/09/2022",   # OCR tờ khai sai
        TkNyc_NoiCuTru={"tinh": "Lâm Đồng", "xa": "Phường Xuân Hương", "diaChi": "64 Nguyễn Thế Oan Khai"},
        Nyc_HoTen="NGUYỄN THỊ HOÀ",
        Nyc_SoDinhDanh="036301012326",
        Nyc_NgayCap="06/08/2022",
        Nyc_NoiCuTru={"tinh": "Lâm Đồng", "xa": "Phường 1", "diaChi": "64, Nguyễn Thị Minh Khai"},
        HoTich_LoaiSuKien="birth",
        HoTich_HoTenNguoiDuocDangKy="TRẦN MINH KHOA",
        HoTich_SoDinhDanh="001210004567",
    )
    assert out["NgayCapDDC"] == "06/08/2022"
    assert out["NYC_NoiCuTru_TrongNuoc"]["diaChi"] == "64 Nguyễn Thị Minh Khai"


def test_muc_i_khac_so_thi_ngay_cap_giu_to_khai():
    out = _run(
        TkNyc_HoTen="TRẦN VĂN NAM",
        TkNyc_SoGiayToTuyThan="001099000111",
        TkNyc_NgayCapGiayToTuyThan="01/09/2022",
        Nyc_HoTen="NGUYỄN THỊ HOÀ",
        Nyc_SoDinhDanh="036301012326",
        Nyc_NgayCap="06/08/2022",
        HoTich_LoaiSuKien="birth",
        HoTich_HoTenNguoiDuocDangKy="TRẦN MINH KHOA",
        HoTich_SoDinhDanh="001210004567",
    )
    assert out["NgayCapDDC"] == "01/09/2022"


def test_muc_ii_trung_so_thi_ngay_sinh_gioi_tinh_ngay_cap_theo_the():
    out = _run(
        HoTich_LoaiSuKien="marriage",
        HoTich_HoTenNguoiDuocDangKy="LE VAN BINH",
        HoTich_SoDinhDanh="036301012326",
        HoTich_NgaySinh="12/03/2001",              # OCR giấy hộ tịch sai
        HoTich_GioiTinh="Nữ",
        HoTich_NgayCapGiayToTuyThan="01/01/2020",
        ChuThe_HoTen="LÊ VĂN BÌNH",
        ChuThe_SoDinhDanh="036301012326",
        ChuThe_NgaySinh="21/03/2001",
        ChuThe_GioiTinh="Nam",
        ChuThe_NgayCap="06/08/2022",
    )
    assert out["NDK_NgaySinh"] == "21/03/2001"
    assert out["NDK_GioiTinh"] == "Nam"
    assert out["NDK_NgayCap"] == "06/08/2022"
