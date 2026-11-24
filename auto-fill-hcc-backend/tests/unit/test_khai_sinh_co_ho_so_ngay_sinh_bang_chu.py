"""Khai sinh cho người đã có hồ sơ: tháng sinh theo phần "ghi bằng chữ" khi OCR đọc sai chữ số tháng trên tờ khai."""
from app.pipelines.khai_sinh_co_ho_so.process import mapper


def test_thang_theo_phan_chu_khi_ngay_khop():
    values = {"Subject_BirthDate": "27/04/1966", "Subject_BirthDateInWords": "Hai bảy tháng một Năm Một ngàn chín trăm"}
    assert mapper._subject_birth_date(values) == "27/01/1966"
    assert mapper._month_from_words("09/01/1973", "mùng chín tháng mười một năm một nghìn") == "09/11/1973"


def test_giu_phan_so_khi_ngay_lech_hoac_cum_thang_dinh_chu_so_nam():
    assert mapper._month_from_words("10/10/1967", "ngày mười tháng mười một chín sáu bảy") == "10/10/1967"
    assert mapper._month_from_words("12/04/1966", "hai bảy tháng một năm") == "12/04/1966"
    assert mapper._month_from_words("25/05/1971", "một ngàn chín trăm bảy mươi") == "25/05/1971"


def test_the_cua_chinh_nguoi_do_van_dung_truoc():
    values = {"Subject_BirthDateFromId": "27/01/1966", "Subject_BirthDate": "27/04/1966",
              "Subject_BirthDateInWords": "hai bảy tháng tư năm"}
    assert mapper._subject_birth_date(values) == "27/01/1966"
