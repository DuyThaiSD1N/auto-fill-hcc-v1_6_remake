"""Unit test mapper "[Bắc Ninh] Xóa đăng ký biện pháp bảo đảm bằng QSDĐ" — trọng tâm XÓA THẾ CHẤP.

Dữ liệu dùng trong test là GIẢ (không phải PII thật) — chỉ để kiểm tra định tuyến FACT → UI field:
- Đồng bảo đảm, 1 người nộp thay → nhân thân (SoNYC) lấy đúng NGƯỜI THỰC NỘP (không lấy người đứng đầu).
- HĐ thế chấp: số + NGÀY KÝ đi thẳng ra ô eForm (phân biệt ngày ký ≠ ngày đăng ký do prompt/LLM lo).
- Tư cách 'Bên bảo đảm' → radio 'Bên thế chấp'.
- Hồ sơ 1 người (mẫu cũ) không vỡ.
"""

from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_bac_ninh.process import mapper


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _run(vals: dict) -> dict:
    return {f["name"]: f for f in mapper.enrich(_flds(vals))}


# Đồng bảo đảm: ông A đứng đầu phiếu, bà B là người trực tiếp nộp (LLM đã trả B ở NguoiYeuCau_*).
_DONG_BAO_DAM = {
    "NguoiYeuCau_HoTen": "NGUYỄN THỊ B",                       # người thực nộp (thứ 2 trên phiếu)
    "NguoiYeuCau_TenDayDu": "ÔNG NGUYỄN VĂN A VÀ BÀ NGUYỄN THỊ B",
    "NguoiYeuCau_SoDinhDanh": "000000000002",                 # CCCD của B, KHÔNG phải A
    "NguoiYeuCau_NgayCap": "05/03/2021",
    "NguoiYeuCau_NoiCap": "Cục Cảnh sát QLHC về TTXH",
    "NguoiYeuCau_DiaChi": "Thôn X, Phường Y, tỉnh Z",
    "NguoiYeuCau_DienThoai": "0900000000",
    "NguoiYeuCau_TuCach": "Bên bảo đảm",
    "Don_KinhGui": "Chi nhánh Văn phòng đăng ký đất đai liên phường, xã Bắc Giang",
    "Gcn_ThuaDatSo": "839",
    "Gcn_ToBanDoSo": "45",
    "Gcn_MucDichSuDung": "Đất ở tại nông thôn",
    "Gcn_ThoiHanSuDung": "Lâu dài",
    "Gcn_DiaChiThuaDat": "Điểm dân cư thôn Ba, Xã Tân Mỹ, thành phố Bắc Giang",
    "Gcn_DienTich": "99,0",
    "Gcn_DienTichBangChu": "chín mươi chín phẩy không mét vuông",
    "Gcn_SoPhatHanh": "CP 485797",
    "Gcn_SoVaoSo": "CH 05063",
    "Gcn_CoQuanCap": "UBND thành phố Bắc Giang",
    "Gcn_NgayCap": "29/11/2018",
    # HĐ thế chấp: số có nhiều dấu '/', ngày KÝ = 02/05 (KHÁC ngày đăng ký 04/05).
    "TheChap_SoHopDong": "19-046-09/2019/HĐBĐ/NHCT280",
    "TheChap_NgayKy": "02/05/2019",
}


def test_dong_bao_dam_nguoi_thuc_nop_va_the_chap():
    d = _run(_DONG_BAO_DAM)
    # Nhân thân điền theo người THỰC NỘP (bà B), không phải người đứng đầu (ông A).
    assert d["SoNYC"]["value"] == "000000000002"
    assert d["CoQuanCapNYC"]["value"] == "Cục Cảnh sát QLHC về TTXH"
    assert d["CapNgayNYC"]["value"] == "05/03/2021"
    # Ô '1.1. Tên đầy đủ' vẫn ghi CẢ HAI đúng nguyên văn phiếu.
    assert d["11TenDayDuCuaToChucCaNhan"]["value"] == "ÔNG NGUYỄN VĂN A VÀ BÀ NGUYỄN THỊ B"
    # Diện tích chỉ giữ chữ số.
    assert d["213DienTichDatTheChapm2"]["value"] == "990"
    # Hợp đồng thế chấp: số + ngày KÝ đi thẳng ra ô.
    assert d["3HopDongTheChapSoNeuCo"]["value"] == "19-046-09/2019/HĐBĐ/NHCT280"
    assert d["KyKetNgayHDTC"]["value"] == "02/05/2019"
    assert d["KyKetNgayHDTC"]["comp"] == "bn-date"
    # Tư cách 'Bên bảo đảm' (NĐ 99/2022) → nhãn radio eForm TT 07/2019.
    assert d["1NguoiYeuCauXoaDangKy"]["value"] == ["Bên thế chấp"]
    # Loại giấy tờ mặc định CCCD; phương thức + nơi nhận mặc định.
    assert d["14luachon"]["value"] == ["Chứng minh nhân dân/Căn cước công dân/Chứng minh QĐND"]
    assert d["7PhuongThucNhanKetQuaDangKy"]["value"] == ["Nhận trực tiếp"]
    assert d["noiNhanKetQua"]["value"] == ["Tại nơi nộp hồ sơ"]


def test_ben_nhan_bao_dam_ra_nhan_the_chap():
    d = _run({**_DONG_BAO_DAM, "NguoiYeuCau_TuCach": "Bên nhận bảo đảm"})
    assert d["1NguoiYeuCauXoaDangKy"]["value"] == ["Bên nhận thế chấp"]


def test_ho_so_mot_nguoi_khong_vo():
    """Mẫu cũ 1 người: TenDayDu fallback = HoTen, vẫn phát đủ field cốt lõi."""
    one = {
        "NguoiYeuCau_HoTen": "TRẦN VĂN C",
        "NguoiYeuCau_SoDinhDanh": "000000000009",
        "NguoiYeuCau_DiaChi": "Bản P, xã Q, tỉnh R",
        "Don_KinhGui": "Chi nhánh Văn phòng đăng ký đất đai Tam Đường",
        "Gcn_ThuaDatSo": "29",
        "TheChap_SoHopDong": "03412.TC.003",
        "TheChap_NgayKy": "05/11/2025",
    }
    d = _run(one)
    assert d["11TenDayDuCuaToChucCaNhan"]["value"] == "TRẦN VĂN C"
    assert d["SoNYC"]["value"] == "000000000009"
    assert d["3HopDongTheChapSoNeuCo"]["value"] == "03412.TC.003"
    assert d["KyKetNgayHDTC"]["value"] == "05/11/2025"
