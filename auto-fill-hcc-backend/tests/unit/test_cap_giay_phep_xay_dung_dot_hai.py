"""Cấp giấy phép xây dựng mới: làm sạch khung mẫu đơn ở mapper + thanh tra / điền đợt 2 (số, tên giả)."""

import asyncio

from app.pipelines._shared.thanh_tra.ho_so import Case
from app.pipelines.cap_giay_phep_xay_dung import thanh_tra
from app.pipelines.cap_giay_phep_xay_dung.process import mapper
from app.pipelines.cap_giay_phep_xay_dung.thanh_tra import chung, dia_diem, thiet_ke, thong_so
from app.procedures.registry import get_procedure


def test_registry_bat_dot_hai_formio():
    assert get_procedure("cap-giay-phep-xay-dung-moi-nha-o-rieng-le")["secondPass"] == "formio"
    assert [i.key for i in thanh_tra.INSPECTORS] == ["thong_so", "dia_diem", "dinh_danh", "thiet_ke"]


def test_chi_tiet_trong_do_bo_khung_mau_cham_dien_va_tang_ham_0():
    assert mapper._clean_detail("Tầng hầm 0m²; Tầng 1: 63,6m² ; Tầng lửng: 30,7m²") == "Tầng 1: 63,6m² ; Tầng lửng: 30,7m²"
    assert mapper._clean_detail("Tầng 1: 140 m², tầng 2: 41,2 m², tầng 3: ....m², tầng 4: .... m²") == (
        "Tầng 1: 140 m²; tầng 2: 41,2 m²")
    assert mapper._clean_detail("4 tầng (trong đó ghi rõ số tầng hầm, tầng trên mặt đất, tầng kỹ thuật)") == "4 tầng"
    assert mapper._clean_detail("01 tầng (trong đó: Trong đó: 0 tầng hầm, 01 tầng trên mặt đất + 01 tầng lửng)") == (
        "01 tầng (trong đó: 01 tầng trên mặt đất + 01 tầng lửng)")
    # Không có khung mẫu thì giữ nguyên chữ của đơn.
    assert mapper._clean_detail("tầng 1: 3.9m; tầng lửng:3.6; tầng tum:3m") == "tầng 1: 3.9m; tầng lửng:3.6; tầng tum:3m"
    assert mapper._clean_detail("Tầng hầm ....m²; Tầng 1 ....m²") is None


def test_duong_pho_bo_so_lo_khung_mau_va_tach_so_nha():
    assert mapper._clean_street("Số nhà .... đường Mẫu A, tổ ....", None) == (None, "đường Mẫu A")
    assert mapper._clean_street("Lô đất số: 325 Phố Mẫu B, tổ 19", None) == (None, "Phố Mẫu B, tổ 19")
    # Số nhà ghi liền tên đường giữ nguyên (cán bộ nhiều nơi để vậy); trùng ô Số nhà thì bỏ khỏi ô đường.
    assert mapper._clean_street("Số 58 Đường Mẫu C", None) == (None, "Số 58 Đường Mẫu C")
    assert mapper._clean_street("03B/19 đường Mẫu D", "03B/19") == ("03B/19", "đường Mẫu D")
    # Chữ "Thôn" cuối tên riêng không phải nhãn mẫu trống.
    assert mapper._clean_street("thôn Mẫu Thôn", None) == (None, "thôn Mẫu Thôn")


def test_cap_cong_trinh_va_thoi_gian_hoan_thanh():
    assert [mapper._cap(v) for v in ("3", "cấp 4", "Cấp III", "Hàng rào", "A")] == ["III", "IV", "III", None, None]
    assert [mapper._months(v) for v in ("06 tháng", "1 năm", "2026", "0.3")] == ["6", "12", None, None]


def test_tin_hieu_tong_dien_tich_san_khong_bang_tong_cac_tang():
    unit = thong_so._DIEN_TICH
    bad = thong_so.signals(unit, {"CongTrinh_TongDienTichSan": "185", "CongTrinh_ChiTietDienTichSan":
                                  "Tầng 1: 90 m², tầng 2: 85 m²"}, None)
    good = thong_so.signals(unit, {"CongTrinh_TongDienTichSan": "175", "CongTrinh_ChiTietDienTichSan":
                                   "Tầng 1: 90 m², tầng 2: 85 m²"}, None)
    assert bad == [(False, bad[0][1])] and good == [(True, good[0][1])]
    assert thong_so.signals(thong_so._CAP, {"CongTrinh_Cap": "Hàng rào"}, None)[0][0] is False


def test_duong_pho_chi_nhan_dong_trong_muc_dia_diem_xay_dung():
    don = ("1. Họ tên chủ hộ: Nguyễn Văn A\nSố nhà: 188 đường: Mẫu X tổ (thôn): 35\n2. Địa điểm xây dựng:\n"
           "- Lô đất có số thửa: 89 tờ bản đồ số: 88\n- Tại số nhà: ....đường Mẫu Y...tổ....phường:")
    case = Case([{"text": don}], "", {}, {})
    assert not dia_diem._site_line("Số nhà: 188 đường: Mẫu X tổ (thôn): 35", case)
    assert dia_diem._site_line("- Tại số nhà: ....đường Mẫu Y...tổ....phường:", case)
    assert dia_diem.check(dia_diem._DUONG, {"Dat_DuongPho": "tổ 45, phường Mẫu"}, case)


def test_ten_to_chuc_thiet_ke_phai_la_phap_nhan():
    assert thiet_ke.check(thiet_ke._TO_CHUC, {"ThietKe_ToChuc_Ten": "Gia đình tự lập"}, None)
    assert not thiet_ke.check(thiet_ke._TO_CHUC, {"ThietKe_ToChuc_Ten": "Công ty TNHH Mẫu"}, None)


def test_thanh_tra_chi_doc_trang_lien_quan_giu_so_thu_tu_tai_lieu():
    text = "───── Trang 1/2 ─────\nĐƠN ĐỀ NGHỊ\nTổng diện tích sàn: 90 m²\n───── Trang 2/2 ─────\nMẶT BẰNG MÓNG"
    case = chung.narrowed(Case([{"text": "CĂN CƯỚC"}, {"text": text}], "", {}, {}), ("tong dien tich san",))
    assert case.documents[0]["text"] == "" and "Tổng diện tích sàn" in case.documents[1]["text"]
    assert "MẶT BẰNG MÓNG" not in case.documents[1]["text"]


def test_review_so_duong_pho_voi_gia_tri_form_dang_co(monkeypatch):
    seen = {}

    async def fake_run(case, inspectors, *, title):
        seen.update(case.values)
        from app.pipelines._shared.thanh_tra.ho_so import Result
        return Result(case.values, [], {})

    monkeypatch.setattr(thanh_tra.engine, "run", fake_run)
    asyncio.run(thanh_tra.review([], {"Dat_DiaDiemXayDung": {"tinh": "A", "xa": "B", "diaChi": "tổ 4"}}))
    assert seen["Dat_DuongPho"] == "tổ 4"


def test_dinh_danh_chi_sua_cung_nguoi_khong_doi_nguoi():
    from app.pipelines.cap_giay_phep_xay_dung.thanh_tra import dinh_danh

    case = Case([], "", {"ChuHo_HoTen": "Nguyễn Hữu Mẫu", "ChuHo_SoDinhDanh": "123456789"}, {})
    unit = dinh_danh._CHU_HO
    assert not dinh_danh.check(unit, {"ChuHo_HoTen": "NGUYỄN HỮU MẪN"}, case)  # lệch chính tả cùng người
    assert dinh_danh.check(unit, {"ChuHo_HoTen": "Trần Thị Khác"}, case)  # người khác
    assert dinh_danh.check(unit, {"ChuHo_SoDinhDanh": "001085000001"}, case)  # đơn ghi CMND 9 số → giữ


def test_thoi_gian_chi_nhan_dong_ghi_theo_thang(monkeypatch):
    from app.pipelines._shared.thanh_tra.ho_so import Finding

    async def fake(inspector, case, title):
        return [Finding(inspector, thong_so._THOI_GIAN, {"CongTrinh_ThoiGianDuKienHoanThanh": "4"}, "Quý IV năm 2026", 1),
                Finding(inspector, thong_so._THOI_GIAN, {"CongTrinh_ThoiGianDuKienHoanThanh": "6"}, "06 tháng", 1)]

    monkeypatch.setattr(thong_so.engine, "llm_findings", fake)
    found = asyncio.run(thong_so.find(thong_so.INSPECTOR, Case([{"text": ""}], "", {}, {}), "thử"))
    assert [f.quote for f in found] == ["06 tháng"]


def test_chu_nhiem_chi_nhan_dong_ghi_vai_tro_chu_nhiem(monkeypatch):
    from app.pipelines._shared.thanh_tra.ho_so import Finding

    async def fake(inspector, case, title):
        return [Finding(inspector, thiet_ke._CHU_NHIEM, {"ThietKe_ChuNhiem_HoTen": "Lê Văn A"}, "KTS. Lê Văn A - Chủ trì: Kiến trúc", 1),
                Finding(inspector, thiet_ke._CHU_NHIEM, {"ThietKe_ChuNhiem_HoTen": "Lê Văn B"}, "KS. Lê Văn B - Chủ nhiệm/Chủ trì: Kết cấu", 1)]

    monkeypatch.setattr(thiet_ke.engine, "llm_findings", fake)
    found = asyncio.run(thiet_ke.find(thiet_ke.INSPECTOR, Case([{"text": ""}], "", {}, {}), "thử"))
    assert [f.values["ThietKe_ChuNhiem_HoTen"] for f in found] == ["Lê Văn B"]
