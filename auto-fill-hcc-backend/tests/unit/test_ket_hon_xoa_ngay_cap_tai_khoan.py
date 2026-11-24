"""Kết hôn: cổng đổ sẵn nhân thân tài khoản vào khối bên cùng giới — bên đó là người khác mà giấy không có ngày cấp
thì xoá ô ngày cấp (không để ngày cấp của tài khoản ghép sang người này)."""
from app.pipelines.ket_hon.process import mapper

_OPTIONS = {"formContext": {"applicantFullname": "TRẦN THỊ TÀI KHOẢN", "applicantIdentityNumber": "001196000001",
                            "applicantBirthday": "01/01/1996", "applicantGender": "2", "applicantIdDate": "09/01/2025"}}


def _issue(fields, side="BenNu"):
    return [f for f in mapper.enrich(fields, _OPTIONS) if f["name"] == f"NgayCapDD_{side}"]


def test_ben_nu_la_nguoi_khac_khong_co_ngay_cap_thi_xoa():
    fields = [{"name": "BenNu_HoTen", "value": "NGUYỄN THỊ KHÁC"}, {"name": "BenNu_SoDinhDanh", "value": "001154000002"},
              {"name": "BenNu_NgaySinh", "value": "10/10/1954"}]
    assert _issue(fields) == [{"name": "NgayCapDD_BenNu", "comp": "x-date", "value": "", "clear": True}]


def test_giay_co_ngay_cap_hoac_la_chinh_chu_tai_khoan_thi_khong_xoa():
    with_date = [{"name": "BenNu_HoTen", "value": "NGUYỄN THỊ KHÁC"}, {"name": "BenNu_SoDinhDanh", "value": "001154000002"},
                 {"name": "BenNu_NgayCap", "value": "28/06/2021"}]
    assert not any(f.get("clear") for f in _issue(with_date))
    # Tờ khai viết tay lệch hai chữ số và ngày sinh nhưng vẫn là chủ tài khoản.
    owner = [{"name": "ToKhaiNu_HoTen", "value": "Trần Thị Tài Khoản"},
             {"name": "ToKhaiNu_SoDinhDanh", "value": "001196000091"}, {"name": "ToKhaiNu_NgaySinh", "value": "07/01/1996"}]
    assert not any(f.get("clear") for f in _issue(owner))
