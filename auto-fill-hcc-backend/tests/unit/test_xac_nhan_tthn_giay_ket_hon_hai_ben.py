"""XNTTHN: giấy chứng nhận kết hôn in CẢ HAI bên — vợ/chồng là bên KHÔNG phải người xin giấy.

Ca thật: chỉ upload giấy kết hôn số 87/1999 (vợ NGUYỄN THỊ OANH | chồng NGUYỄN DUY THÁI). Schema cũ
chỉ có một field tên vợ/chồng nên agent đoán bừa một bên và rơi mất tên người chồng.
"""
from app.pipelines.xac_nhan_tthn.process.mapper import enrich

_GCN = dict(
    Marriage_WifeName="NGUYỄN THỊ OANH",
    Marriage_WifeIdNumber="022170000913",
    Marriage_HusbandName="NGUYỄN DUY THÁI",
    Marriage_HusbandIdNumber="001204018566",
    Marriage_Number="87/1999",
    Marriage_Date="21/04/1999",
    Marriage_Agency="Uỷ ban nhân dân Thị trấn Cô Tô, huyện Cô Tô, tỉnh Quảng Ninh",
)


def _fields(**kv):
    return [{"name": k, "value": v} for k, v in kv.items()]


def _field(out, name):
    return next(f for f in out if f["name"] == name)


def _ctx(name=None, id_number=None):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": id_number}}


def test_chi_giay_ket_hon_nguoi_dang_nhap_la_vo_thi_vo_chong_la_chong():
    out = enrich(_fields(**_GCN), _ctx("Nguyễn Thị Oanh", "022170000913"))
    field = _field(out, "nxnLoaiTinhTrangHonNhan=2")
    assert field["value"]["voChongHoTen"] == "NGUYỄN DUY THÁI"
    assert not field.get("default")


def test_chi_giay_ket_hon_nguoi_dang_nhap_la_chong_thi_vo_chong_la_vo():
    out = enrich(_fields(**_GCN, Marriage_SpouseName="NGUYỄN DUY THÁI"), _ctx(id_number="001204018566"))
    assert _field(out, "nxnLoaiTinhTrangHonNhan=2")["value"]["voChongHoTen"] == "NGUYỄN THỊ OANH"


def test_cccd_trong_ho_so_thang_tai_khoan_dang_nhap():
    out = enrich(
        _fields(**_GCN, Cccd_HoTen="NGUYỄN DUY THÁI", Cccd_SoDinhDanh="001204018566"),
        _ctx("NGUYỄN THỊ OANH", "022170000913"),
    )
    assert _field(out, "nxnLoaiTinhTrangHonNhan=2")["value"]["voChongHoTen"] == "NGUYỄN THỊ OANH"


def test_gioi_tinh_chot_khi_khong_so_duoc_ten_so():
    out = enrich(_fields(**_GCN, ToKhai_HoTen="NGUYEN THI 0ANH", ToKhai_GioiTinh="Nữ"))
    assert _field(out, "nxnLoaiTinhTrangHonNhan=2")["value"]["voChongHoTen"] == "NGUYỄN DUY THÁI"


def test_khong_biet_ai_xin_giay_thi_danh_dau_de_soat():
    out = enrich(_fields(**_GCN))
    field = _field(out, "nxnLoaiTinhTrangHonNhan=2")
    assert field["value"]["voChongHoTen"] in {"NGUYỄN THỊ OANH", "NGUYỄN DUY THÁI"}
    assert field["default"] is True
