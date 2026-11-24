"""Liên thông khai sinh: thanh tra địa chỉ — CCCD ghi nơi cư trú theo địa giới cũ, giấy chứng sinh / giấy kết hôn ghi nơi
cư trú của chính người đó theo địa giới mới ở xã khác → đề xuất địa chỉ mới."""
from app.pipelines.khai_sinh_lien_thong.thanh_tra import dia_chi, trang

_GKH = """GIẤY CHỨNG NHẬN KẾT HÔN
Họ, chữ đệm, tên vợ: NGUYỄN THỊ VỢ Họ, chữ đệm, tên chồng: TRẦN VĂN CHỒNG
Nơi cư trú: Thôn Mới, xã Thái Tân, thành phố Hải Phòng Nơi cư trú: Thôn Thượng, xã Phật Tích, tỉnh Bắc Ninh"""
_CCCD_ME = {"diaChi": "Thôn Cũ", "xa": "Nam Trung", "tinh": "Hải Dương"}


def _fix(values, *texts):
    docs = [{"name": f"g{i}.pdf", "text": text} for i, text in enumerate(texts)]
    return dia_chi.boundary_fix(values, trang.pages(docs))


def test_cot_vo_cua_giay_ket_hon_la_noi_cu_tru_moi_cua_me():
    found = _fix({"ThongTinMe_NoiCuTru": _CCCD_ME}, _GKH)
    assert [(name, area["xa"], area["tinh"], area["diaChi"]) for name, area, *_ in found] == [
        ("ThongTinMe_NoiCuTru", "Xã Thái Tân", "Hải Phòng", "Thôn Mới")]


def test_khong_de_xuat_khi_co_to_khai_hoac_giay_moi_con_cap_huyen():
    assert _fix({"ThongTinMe_NoiCuTru": _CCCD_ME, "Tk_NoiCuTruMe": {"xa": "Nam Trung", "tinh": "Hải Dương"}}, _GKH) == []
    old = _GKH.replace("xã Thái Tân, thành phố Hải Phòng", "xã Thái Tân, Nam Sách, thành phố Hải Phòng")
    assert _fix({"ThongTinMe_NoiCuTru": _CCCD_ME}, old) == []
