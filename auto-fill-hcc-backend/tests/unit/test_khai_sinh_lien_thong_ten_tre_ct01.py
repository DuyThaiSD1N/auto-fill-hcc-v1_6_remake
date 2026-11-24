from app.pipelines.khai_sinh_lien_thong.thanh_tra import dinh_danh, trang

_TK = ("TỜ KHAI ĐĂNG KÝ KHAI SINH\nKính gửi: UBND phường X\nĐề nghị cơ quan đăng ký khai sinh cho người dưới đây:\n"
       "Họ, chữ đệm, tên: {ten}\n")
_CT01 = ("Mẫu CT01\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nTỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ\n"
         "1. Họ, chữ đệm và tên khai sinh: {ten}\n7. Họ, chữ đệm và tên chủ hộ: TRẦN VĂN B\n")
_GCS = "GIẤY CHỨNG SINH\nBệnh viện X\nDự định đặt tên con: {ten}\n"
_CHILD = dinh_danh.CHILD[0]


def _finding(values, *texts):
    pages = trang.pages([{"name": f"{i}.pdf", "text": t} for i, t in enumerate(texts)])
    return dinh_danh.ct01_child_finding(_CHILD, values, pages)


def test_to_khai_va_ct01_chi_lech_dau_thi_theo_ct01():
    values = {"Tk_HoTenCon": "TRẦN MÃN A", "Ct01_HoTen": "TRẦN MẪN A"}
    found = _finding(values, _TK.format(ten="TRẦN MÃN A"), _CT01.format(ten="TRẦN MẪN A"))
    assert found.values == {"Tk_HoTenCon": "TRẦN MẪN A"}
    assert found.backed


def test_giay_in_ghi_theo_to_khai_thi_giu():
    values = {"Tk_HoTenCon": "TRẦN MÃN A", "Ct01_HoTen": "TRẦN MẪN A"}
    assert _finding(values, _TK.format(ten="TRẦN MÃN A"), _CT01.format(ten="TRẦN MẪN A"),
                    _GCS.format(ten="TRẦN MÃN A")) is None


def test_khac_chu_cai_hoac_ct01_roi_dau_thi_khong_de_xuat():
    values = {"Tk_HoTenCon": "TRẦN MẪN A", "Ct01_HoTen": "TRẦN MINH A"}
    assert _finding(values, _TK.format(ten="TRẦN MẪN A"), _CT01.format(ten="TRẦN MINH A")) is None
    values = {"Tk_HoTenCon": "TRẦN MẪN A", "Ct01_HoTen": "TRAN MAN A"}
    assert _finding(values, _TK.format(ten="TRẦN MẪN A"), _CT01.format(ten="TRAN MAN A")) is None


def test_ten_lay_theo_giay_chung_sinh_hoac_ct01_khong_co_tren_trang_thi_khong_de_xuat():
    values = {"Gcs_HoTenCon": "TRẦN MÃN A", "Ct01_HoTen": "TRẦN MẪN A"}
    pages = trang.pages([{"name": "0.pdf", "text": _CT01.format(ten="TRẦN MẪN A")}])
    assert dinh_danh.ct01_child_finding(dinh_danh.CHILD[1], values, pages) is None
    values = {"Tk_HoTenCon": "TRẦN MÃN A", "Ct01_HoTen": "TRẦN MẪN A"}
    assert _finding(values, _TK.format(ten="TRẦN MÃN A")) is None
