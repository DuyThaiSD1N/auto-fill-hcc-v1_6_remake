"""Mapper trích lục: quan hệ từ tờ khai → radio NYC_QuanHe (khớp NHÃN option), quyển số đi trọn đường."""
from app.pipelines.trich_luc.process.mapper import enrich


def _by_name(out):
    return {f["name"]: f for f in out}


def _fields(**kv):
    return [{"name": k, "value": v} for k, v in kv.items()]


def test_quanhe_tu_to_khai_khop_nhan_option():
    base = dict(HoTich_LoaiSuKien="birth", HoTich_HoTenNguoiDuocDangKy="Nguyễn Văn B",
                HoTich_So="45/2019", HoTich_QuyenSo="02/2019")
    for raw, expect in [
        ("Mẹ đẻ", "Mẹ đẻ"),
        ("mẹ ruột", "Mẹ đẻ"),       # biến thể nói thường
        ("Bố đẻ", "Bố Đẻ"),          # nhãn form viết hoa Đ — khớp qua fold
        ("Bản thân", "Bản thân"),
        ("tự khai", "Bản thân"),     # "tự khai" = tự làm cho mình
        ("Tư khai", "Bản thân"),     # OCR rớt dấu vẫn khớp qua fold
        ("ông ngoại", "Ông"),
    ]:
        out = _by_name(enrich(_fields(**base, CopyRequest_QuanHe=raw)))
        assert out["NYC_QuanHe"]["value"] == expect, raw
        assert out["NYC_QuanHe"]["comp"] == "x-radio"

    # "Ba" trần nhập nhằng (bố Nam bộ vs Bà) → KHÔNG tick bừa.
    out = _by_name(enrich(_fields(**base, CopyRequest_QuanHe="Ba")))
    assert "NYC_QuanHe" not in out
    # Không có dòng quan hệ → bỏ trống.
    out = _by_name(enrich(_fields(**base)))
    assert "NYC_QuanHe" not in out


def test_giay_to_tuy_than_chu_the_tu_thẻ_can_cuoc():
    """Thẻ căn cước RIÊNG của người được đăng ký (ChuThe_*) khớp số định danh chủ thể → điền
    mục (9) giấy tờ tùy thân; số thẻ lệch chủ thể (bắt nhầm thẻ mẹ) → guard chặn, không điền."""
    base = dict(
        HoTich_LoaiSuKien="birth", HoTich_HoTenNguoiDuocDangKy="Nguyễn Văn B",
        HoTich_SoDinhDanh="045678901234",
        ChuThe_HoTen="Nguyễn Văn B", ChuThe_SoDinhDanh="045678901234",
        ChuThe_LoaiGiayTo="Thẻ căn cước",
        ChuThe_NgayCap="03/04/2024", ChuThe_NoiCap="Bộ Công an",
    )
    out = _by_name(enrich(_fields(**base)))
    assert out["NDK_SoGiayToTuyThan"]["value"] == "045678901234"
    assert out["NDK_NgayCap"]["value"] == "03/04/2024"
    assert out["NDK_NoiCap"]["value"] == "Bộ Công an"
    assert out["NDK_LoaiGiayToTuyThan"]["value"] == "Thẻ Căn cước"  # Bộ Công an → thẻ mới

    # Số thẻ KHÔNG trùng số định danh chủ thể (LLM bắt nhầm thẻ mẹ) → bỏ toàn bộ.
    wrong = dict(base, ChuThe_SoDinhDanh="036192014000")
    out = _by_name(enrich(_fields(**wrong)))
    assert "NDK_NgayCap" not in out and "NDK_LoaiGiayToTuyThan" not in out


def test_quyen_so_di_tron_duong_ra_hoso():
    out = _by_name(enrich(_fields(
        HoTich_LoaiSuKien="birth", HoTich_HoTenNguoiDuocDangKy="Nguyễn Văn B",
        HoTich_So="45/2019", HoTich_QuyenSo="02/2019", HoTich_NgayDangKy="05/06/2019",
    )))
    assert out["HoSo_So"]["value"] == "45/2019"
    assert out["HoSo_QuyenSo"]["value"] == "02/2019"
    assert out["HoSo_NgayCapSo"]["value"] == "05/06/2019"


def test_nguoi_yeu_cau_trung_chu_the_tu_lam_dien_noi_cu_tru():
    """Ca TỰ LÀM (người yêu cầu = người được đăng ký, trùng số định danh) → mục II lấy nơi
    cư trú từ CCCD người yêu cầu (fallback Nyc_*). Không mỏ neo formContext."""
    out = _by_name(enrich(_fields(
        HoTich_LoaiSuKien="birth",
        HoTich_HoTenNguoiDuocDangKy="Nguyễn Thị Song Hồng",
        HoTich_SoDinhDanh="068184005205",
        Nyc_HoTen="Nguyễn Thị Song Hồng",
        Nyc_SoDinhDanh="068184005205",
        Nyc_NgayCap="21/10/2024", Nyc_NoiCap="Bộ Công an",
        Nyc_NoiCuTru={"quocGia": "Việt Nam", "tinh": "Lâm Đồng",
                      "xa": "Phường Xuân Hương", "diaChi": "25 Phan Đình Phùng"},
    )))
    assert out["NDK_NoiCuTru"]["value"] == "1"          # radio "Trong nước" mục II được tích
    area = out["NDK_NoiCuTru_TrongNuoc"]["value"]
    assert area["tinh"] == "Lâm Đồng" and area["xa"] == "Phường Xuân Hương"


def test_nyc_nguoi_khac_van_khong_lay_dia_chi_cho_chu_the():
    """Ca LÀM HỘ: CCCD của mẹ (số khác chủ thể) → mục II vẫn tích "Trong nước" + Việt Nam
    (mặc định vàng), nhưng TUYỆT ĐỐI không nhét địa chỉ CHI TIẾT của mẹ vào ô của con."""
    out = _by_name(enrich(_fields(
        HoTich_LoaiSuKien="birth",
        HoTich_HoTenNguoiDuocDangKy="Nguyễn Văn Con",
        HoTich_SoDinhDanh="068184005205",
        Nyc_HoTen="Trần Thị Mẹ",
        Nyc_SoDinhDanh="040203015844",                 # số KHÁC hẳn chủ thể
        Nyc_NoiCuTru={"quocGia": "Việt Nam", "tinh": "Nghệ An",
                      "xa": "Xã Tam Hợp", "diaChi": "Xóm Long Thành"},
    )))
    area = out["NDK_NoiCuTru_TrongNuoc"]["value"]
    assert out["NDK_NoiCuTru_TrongNuoc"].get("default") is True   # chỉ là mặc định vàng
    assert area == {"quocGia": "Việt Nam"}                        # KHÔNG có tỉnh/xã của mẹ
    assert not area.get("tinh") and not area.get("xa")


def test_hai_noi_cu_tru_doc_lap_khong_muon_cheo():
    """HoTich_NoiCuTru (người được đăng ký) và Nyc_NoiCuTru (người yêu cầu) là 2 ô ĐỘC LẬP.
    Khi 2 người ở KHÁC địa chỉ, mỗi ô phải đúng của mỗi người — tuyệt đối không chắp chéo."""
    out = _by_name(enrich(_fields(
        HoTich_LoaiSuKien="birth",
        HoTich_HoTenNguoiDuocDangKy="Nguyễn Thị Song Hồng",
        HoTich_SoDinhDanh="068184005205",
        HoTich_NoiCuTru={"quocGia": "Việt Nam", "tinh": "Lâm Đồng",
                         "xa": "Phường Xuân Hương", "diaChi": "25 Phan Đình Phùng"},
        # Người yêu cầu là người KHÁC (làm hộ), ở tỉnh khác hẳn.
        Nyc_HoTen="Trần Văn Bố", Nyc_SoDinhDanh="040203015844",
        Nyc_NoiCuTru={"quocGia": "Việt Nam", "tinh": "Nghệ An",
                      "xa": "Xã Tam Hợp", "diaChi": "Xóm Long Thành"},
    ), {"formContext": {"applicantFullname": "Trần Văn Bố",
                        "applicantIdentityNumber": "040203015844"}}))
    # Mục II (người được đăng ký) — địa chỉ Lâm Đồng từ HoTich_NoiCuTru.
    assert out["NDK_NoiCuTru"]["value"] == "1"
    assert out["NDK_NoiCuTru_TrongNuoc"]["value"]["tinh"] == "Lâm Đồng"
    assert out["NDK_NoiCuTru_TrongNuoc"]["value"]["xa"] == "Phường Xuân Hương"
    # Mục I (người yêu cầu) — địa chỉ Nghệ An từ Nyc_NoiCuTru, KHÔNG lẫn sang Lâm Đồng.
    # remap_area chuẩn hóa về tên đơn vị hiện hành ĐẦY ĐỦ tiền tố ("Xã Tam Hợp") để khớp option form.
    assert out["NYC_NoiCuTru_TrongNuoc"]["value"]["tinh"] == "Nghệ An"
    assert out["NYC_NoiCuTru_TrongNuoc"]["value"]["xa"] == "Xã Tam Hợp"
