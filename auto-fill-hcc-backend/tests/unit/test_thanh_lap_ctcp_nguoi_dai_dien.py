"""Thành lập CÔNG TY CỔ PHẦN: trang "Người đại diện theo pháp luật".

Lỗi thật (ảnh chụp cổng dangkyquamang, hồ sơ CTCP Quản lý vận động viên trẻ quốc gia): trang này
trống trơn dù GCN ĐKDN in đủ họ tên / giới tính / ngày sinh / số định danh / chức danh / địa chỉ
của người đại diện. Nguyên nhân: pipeline CTCP KHÔNG hề khai bộ field NguoiDaiDien_* — schema
không có field, prompt không có luật, mapper không có nhánh trang. Extension dựng thứ tự trang từ
chính dữ liệu backend trả về (pageHasData) nên trang bị bỏ qua im lặng.

Thủ tục TNHH hai thành viên đã chạy đúng từ trước và dùng CHUNG trang
Information_of_Legal_representative.aspx của cổng, nên bài test chốt luôn: hai pipeline phải phát
ra field GIỐNG HỆT nhau.
"""
from app.pipelines.thanh_lap_ctcp.process import schema
from app.pipelines.thanh_lap_ctcp.process.mapper import enrich, enrich_all
from app.pipelines.thanh_lap_ctythnn_2_nguoi.process.mapper import enrich as enrich_tnhh2

_PAGE = "nguoi-dai-dien-phap-luat"

# Người đại diện trên GCN ĐKDN 0402298682.
_REP = [
    {"name": "NguoiDaiDien_HoTen", "value": "Nguyễn Hồng Anh"},
    {"name": "NguoiDaiDien_GioiTinh", "value": "Nam"},
    {"name": "NguoiDaiDien_NgaySinh", "value": "01/04/1966"},
    {"name": "NguoiDaiDien_SoDinhDanh", "value": "044066012106"},
    {"name": "NguoiDaiDien_DienThoai", "value": "0967772585"},
    {"name": "NguoiDaiDien_Email", "value": "nya@example.vn"},
    {"name": "NguoiDaiDien_QuyenHan", "value": "Giám đốc"},
    {
        "name": "NguoiDaiDien_DiaChi",
        "value": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Phường Hòa Cường", "diaChi": "Tổ 17"},
    },
]


def _by_name(fields):
    return {f["name"]: f["value"] for f in fields}


def test_trang_nguoi_dai_dien_nam_dung_thu_tu_menu_cong():
    """Xếp đúng vị trí như menu trái của cổng: sau "Thông tin về cổ phần", trước "Thông tin về thuế".

    Thứ tự ĐI qua từng trang khi điền do PAGE_SPEC của extension quyết định, không phải danh sách
    này; ở đây chỉ giữ cho PAGES đọc khớp với cổng để người sau không phải đoán.
    """
    keys = [p["key"] for p in schema.PAGES]
    assert _PAGE in keys
    assert keys.index("thong-tin-ve-co-phan") < keys.index(_PAGE) < keys.index("thong-tin-ve-thue")


def test_schema_khai_du_bo_field_va_dung_kieu_o():
    assert {n for n in schema.ALLOWED if n.startswith("NguoiDaiDien_")} == {
        "NguoiDaiDien_HoTen", "NguoiDaiDien_GioiTinh", "NguoiDaiDien_NgaySinh",
        "NguoiDaiDien_SoDinhDanh", "NguoiDaiDien_DiaChi", "NguoiDaiDien_DienThoai",
        "NguoiDaiDien_Fax", "NguoiDaiDien_Website", "NguoiDaiDien_Email", "NguoiDaiDien_QuyenHan",
    }
    # Địa chỉ phải là ô địa bàn (cascade tỉnh/xã), ngày sinh phải là ô ngày — sai kiểu thì
    # extension điền như text và cổng không nhận.
    assert schema.COMPACT_COMP_BY_NAME["NguoiDaiDien_DiaChi"] == "x-select-area"
    assert schema.COMPACT_COMP_BY_NAME["NguoiDaiDien_NgaySinh"] == "x-date"


def test_mapper_phat_du_o_cua_trang():
    out = _by_name(enrich(_REP, page=_PAGE))
    person = "ctl00$C$REPCtl$PERSCtl"
    assert out[f"{person}$FULL_NAMEFld"] == "NGUYỄN HỒNG ANH"   # cổng lưu chữ HOA
    assert out[f"{person}$GENDER_IDFld"] == "M"
    assert out[f"{person}$DATE_OF_BIRTHFld"] == "01/04/1966"
    assert out[f"{person}$PERS_DOC_NOFld"] == "044066012106"
    assert out[f"{person}$ADDRCCtl$CITY_IDFld"] == "Đà Nẵng"
    assert out[f"{person}$ADDRCCtl$STREET_NUMBERFld"] == "Tổ 17"
    assert out["ctl00$C$REPCtl$POWERSId"] == "Giám đốc"


def test_o_quyen_han_co_alias():
    """Bảng đặc tả ghi id là POWERSId; alias POWERSFld đỡ cho bản render khác của cổng."""
    field = next(f for f in enrich(_REP, page=_PAGE) if f["name"].endswith("$POWERSId"))
    assert field["aliases"] == ["ctl00$C$REPCtl$POWERSFld"]


def test_giong_het_luong_tnhh_hai_thanh_vien():
    """Cùng một trang của cổng ⇒ cùng một bộ field. Đây là chốt chặn chống lệch về sau."""
    def shape(fields):
        return sorted((f["name"], f["comp"], str(f["value"]), str(f.get("aliases"))) for f in fields)

    assert shape(enrich(_REP, page=_PAGE)) == shape(enrich_tnhh2(_REP, page=_PAGE))


def test_khong_co_nguoi_dai_dien_thi_trang_rong_chu_khong_no():
    """Hồ sơ không đọc được người đại diện → trang rỗng, extension tự báo và bỏ qua."""
    assert enrich([{"name": "DoanhNghiep_TenRieng", "value": "X"}], page=_PAGE) == []


def test_gui_kem_legalRep_cho_trang_nguoi_nop():
    """Extension đối chiếu người đại diện với tài khoản ĐKKD đang đăng nhập để chốt vai trò người nộp."""
    pages = enrich_all(_REP + [{"name": "NguoiNop_HoTen", "value": "BÙI THỊ PHƯƠNG HẠNH"}])
    legal_rep = _by_name(pages["nguoi-nop-ho-so"])["__legalRep"]
    assert legal_rep == {"fullName": "Nguyễn Hồng Anh", "docNo": "044066012106"}


def test_khong_co_nguoi_dai_dien_thi_khong_gui_legalRep():
    pages = enrich_all([{"name": "NguoiNop_HoTen", "value": "BÙI THỊ PHƯƠNG HẠNH"}])
    assert "__legalRep" not in _by_name(pages["nguoi-nop-ho-so"])
