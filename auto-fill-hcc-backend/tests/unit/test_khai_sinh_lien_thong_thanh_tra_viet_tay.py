"""Thanh tra liên thông khai sinh: chữ viết tay trên CT01 đọc sai mà giấy in ghi đúng; tên phường có chữ trùng tiền tố."""

from datetime import date, timedelta

from app.pipelines.khai_sinh_lien_thong.thanh_tra import dia_chi, dinh_danh, trang

_CT01 = ("Mẫu CT01\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nTỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ\n"
         "1. Họ, chữ đệm và tên khai sinh: {ten}\n7. Họ, chữ đệm và tên chủ hộ: TRẦN VĂN B\n{muc10}\n")
_GCS = ("GIẤY CHỨNG SINH\nBệnh viện X\nHọ, chữ đệm, tên khai sinh của mẹ: LÊ THỊ C\n"
        "Nơi cư trú: {noi}\nDự định đặt tên con là: {ten}\n")
_CHILD = next(person for person in dinh_danh.CHILD if person.name == "Ct01_HoTen")


def _pages(*texts):
    return trang.pages([{"name": f"{i}.pdf", "text": t} for i, t in enumerate(texts)])


def _child(ct01, gcs, muc10):
    born = (date.today() - timedelta(days=5)).strftime("%d/%m/%Y")
    values = {"Ct01_HoTen": ct01, "Ct01_NgaySinh": born, "Gcs_HoTenCon": gcs}
    pages = _pages(_CT01.format(ten=ct01, muc10=muc10), _GCS.format(ten=gcs, noi="Thôn 1, Xã Y, Tỉnh Z"))
    return values, pages


def test_ten_ct01_doc_sai_ma_giay_chung_sinh_va_muc_10_ghi_dung_thi_de_xuat():
    values, pages = _child("TRẦN THỊ ANH", "TRẦN THỊ NHI", "10. Nội dung đề nghị: cho cháu Trần Thị Nhi nhập hộ khẩu")
    found = dinh_danh.gcs_child_finding(_CHILD, values, pages)
    assert found.values == {"Ct01_HoTen": "TRẦN THỊ NHI"}
    assert found.backed


def test_cha_me_dat_ten_khac_ten_du_dinh_thi_giu_ct01():
    values, pages = _child("TRẦN THỊ LAN", "TRẦN THỊ NHI", "10. Nội dung đề nghị: cho cháu Trần Thị Lan nhập hộ khẩu")
    assert dinh_danh.gcs_child_finding(_CHILD, values, pages) is None
    values, pages = _child("TRẦN THỊ LAN", "TRẦN THỊ NHI", "10. Nội dung đề nghị: nhập hộ khẩu")
    assert dinh_danh.gcs_child_finding(_CHILD, values, pages) is None


def test_ten_phuong_khong_khop_nham_qua_chu_trung_tien_to():
    area = dia_chi._new_boundary_area("TDP Vân Mẫu, Phường Nam Sơn, Tỉnh Bắc Ninh")
    assert area["xa"] == "Phường Nam Sơn"
    assert area["diaChi"] == "TDP Vân Mẫu"


def _dktt(detail, printed):
    values = {"Ct01_NoiDeNghiDktt": {"tinh": "Khánh Hòa", "xa": "Tây Nha Trang", "diaChi": detail}}
    pages = _pages(_GCS.format(ten="TRẦN THỊ NHI", noi=f"{printed}, Phường Tây Nha Trang, Tỉnh Khánh Hòa"))
    return dia_chi.dktt_fix(values, pages)


def test_noi_de_nghi_dktt_doc_sai_chu_viet_tay_thi_theo_ban_in():
    fix = _dktt("MB đường Lê Lai Tổ 3", "12 B Lê Lợi, Tổ 3")
    assert fix["diaChi"] == "12 B Lê Lợi, Tổ 3"


def test_noi_de_nghi_dktt_khac_so_nha_hoac_chi_rut_gon_thi_giu():
    assert _dktt("20 Lê Lợi, Tổ 3", "12 B Lê Lợi, Tổ 3") is None
    assert _dktt("Lê Lợi Tổ 3", "12 B Lê Lợi, Tổ 3") is None
    assert _dktt("Nguyễn Trãi Tổ 3", "12 B Lê Lợi, Tổ 3") is None
