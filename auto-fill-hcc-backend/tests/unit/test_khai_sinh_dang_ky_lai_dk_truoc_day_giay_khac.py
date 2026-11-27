"""Đăng ký lại khai sinh: mục "đăng ký khai sinh trước đây" không lấy số / ngày của giấy kết hôn, khai tử (giá trị giả)."""
from app.pipelines.khai_sinh_dang_ky_lai.process import reason

_UY_QUYEN = ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\nGIẤY ỦY QUYỀN\n"
             "Bên được ủy quyền nộp hồ sơ đăng ký lại khai sinh và nhận trích lục khai sinh.")
_KET_HON = ("ỦY BAN NHÂN DÂN\nTỉnh/thành phố: X Số: 53\nGIẤY CHỨNG NHẬN KẾT HÔN\nHọ và tên chồng: A Họ và tên vợ: B\n"
            "Ngày, tháng, năm sinh: 03.3.1988\nCán bộ Tư pháp hộ tịch Đăng ký ngày 29 tháng 3 năm 2010")
_CAM_DOAN = ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nBẢN CAM ĐOAN\nTrước đây tôi đã được đăng ký khai sinh tại UBND xã Y, "
             "số 12, ngày 05/06/1990, nay giấy khai sinh bị mất.\nGiấy tờ kèm theo: 1. Giấy chứng nhận kết hôn")


def _page(*pages):
    return "\n".join(f"───── Trang {i}/{len(pages)} ─────\n{body}" for i, body in enumerate(pages, start=1))


def test_giay_uy_quyen_nhac_trich_luc_khai_sinh_khong_phai_giay_khai_sinh():
    assert reason._valid_birth_source_names([{"name": "ho-so.pdf", "text": _page(_UY_QUYEN, _KET_HON)}]) == []
    assert reason._valid_birth_source_names([{"name": "cd.pdf", "text": _CAM_DOAN}]) == ["cd.pdf"]


def test_so_ngay_giay_ket_hon_khong_thanh_dang_ky_khai_sinh_truoc_day():
    docs = [{"name": "ho-so.pdf", "text": _page(_CAM_DOAN, _KET_HON)}]
    numbers, dates = reason._other_registration_marks(docs)
    assert numbers == {"53"} and dates == {"29/03/2010"}  # trang cam đoan liệt kê "giấy kết hôn" không tính
    context = reason.render_other_registration(docs)
    assert reason._foreign_previous_registration(
        {"PreviousRegistration_Number": "53", "PreviousRegistration_Date": "29/03/2010"}, context) == {"*"}
    assert reason._foreign_previous_registration(
        {"PreviousRegistration_Number": "53", "PreviousRegistration_Date": "05/06/1990"}, context) == {
        "PreviousRegistration_Number"}
    assert not reason._foreign_previous_registration(
        {"PreviousRegistration_Number": "12", "PreviousRegistration_Date": "05/06/1990"}, context)


_KS_MAU_CU = ("ỦY BAN NHÂN DÂN    CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY KHAI SINH\n(BẢN SAO)\n"
              "Họ và tên: {ten}    Nam hay nữ:\nNgày, tháng, năm sinh: 15 tháng 10 năm 1977\n"
              "| Họ và tên | Lê Thị C | Trần Văn D |\n")


def test_giay_khai_sinh_mau_cu_cua_nguoi_khac_khong_thanh_dang_ky_truoc_day():
    con = "Họ tên: LÊ THỊ C\nNgày sinh: 1949"
    docs = [{"name": "ks-con.pdf", "text": _KS_MAU_CU.format(ten="Trần Văn E")}]
    assert reason._valid_birth_source_names(docs) == ["ks-con.pdf"]
    assert reason._subject_birth_source_names(docs, con) == []
    docs = [{"name": "ks.pdf", "text": _KS_MAU_CU.format(ten="Lê Thị C")}]
    assert reason._subject_birth_source_names(docs, con) == ["ks.pdf"]
