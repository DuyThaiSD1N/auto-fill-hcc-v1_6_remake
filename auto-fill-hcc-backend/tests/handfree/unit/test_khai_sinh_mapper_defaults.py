"""Regression tests for the interlinked birth-registration controls."""

from app.pipelines.khai_sinh_lien_thong.process.mapper import enrich


def _fields(**values):
    return [{"name": name, "value": value} for name, value in values.items()]


def _by_name(fields):
    return {field["name"]: field for field in fields}


_CT01_KHOP_ME = dict(
    Gcs_HoTenCon="Nguyễn Văn Bé",
    ThongTinBo_HoTen="Nguyễn Văn Bố",
    ThongTinBo_SoDinhDanh="012345678901",
    ThongTinMe_HoTen="Trần Thị Mẹ",
    ThongTinMe_SoDinhDanh="098765432109",
    Ct01_ChuHoHoTen="Trần Thị Mẹ",
    Ct01_ChuHoSoDinhDanh="098765432109",
)


def test_khong_co_ct01_khong_mac_dinh_vneid_va_dang_ky_thuong_tru():
    out = _by_name(enrich(_fields(
        Gcs_HoTenCon="Nguyễn Văn Bé",
        ThongTinBo_HoTen="Nguyễn Văn Bố",
        ThongTinBo_SoDinhDanh="012345678901",
    )))

    # Không có CT01 thì không có căn cứ chọn cách xác nhận/thường trú (nhiều nơi dùng mẫu khác) → để trống.
    for name in (
        "LoaiXacNhanVNeID", "DkttIsTtBo", "DkttIsTtMe", "LoaiThanNhanXacNhan", "LoaiChuSoHuuChoO",
    ):
        assert name not in out


def test_ct01_khop_me_giu_nhan_dien_me_khong_fallback_sang_bo():
    out = _by_name(enrich(_fields(**_CT01_KHOP_ME)))

    assert out["LoaiXacNhanVNeID"]["value"] == "1"
    assert out["DkttIsTtMe"]["value"] is True
    assert "DkttIsTtBo" not in out


def test_ct01_khop_me_chon_than_nhan_va_chu_so_huu_la_me():
    out = _by_name(enrich(_fields(**_CT01_KHOP_ME)))

    assert out["LoaiThanNhanXacNhan"]["value"] == "2"
    assert out["LoaiChuSoHuuChoO"]["value"] == "2"


def test_ct01_khop_bo_chon_than_nhan_va_chu_so_huu_la_bo():
    out = _by_name(enrich(_fields(**{**_CT01_KHOP_ME, "Ct01_ChuHoHoTen": "Nguyễn Văn Bố",
                                     "Ct01_ChuHoSoDinhDanh": "012345678901"})))

    assert out["DkttIsTtBo"]["value"] is True
    assert out["LoaiThanNhanXacNhan"]["value"] == "1"
    assert out["LoaiChuSoHuuChoO"]["value"] == "1"


def test_ct01_chu_ho_nguoi_khac_khong_tu_dong_chon_bo():
    out = _by_name(enrich(_fields(
        Gcs_HoTenCon="Nguyễn Văn Bé",
        ThongTinBo_HoTen="Nguyễn Văn Bố",
        ThongTinBo_SoDinhDanh="012345678901",
        ThongTinMe_HoTen="Trần Thị Mẹ",
        ThongTinMe_SoDinhDanh="098765432109",
        Ct01_ChuHoHoTen="Lê Văn Chủ Hộ",
        Ct01_ChuHoSoDinhDanh="011111111111",
        Ct01_QuanHeVoiChuHo="Cháu nội",
    )))

    assert out["DkttChuHo"]["value"] == "LÊ VĂN CHỦ HỘ"
    assert out["DkttChuhoSoGiayTo"]["value"] == "011111111111"
    assert out["DkttMaQuanHe"]["value"] == "Cháu nội"
    assert "LoaiThanNhanXacNhan" not in out
    assert "LoaiChuSoHuuChoO" not in out


def test_ct01_chu_ho_la_bo_van_dien_ten_va_so_dinh_danh_truoc_o_tick():
    # Form không có ô tick "Bố là chủ hộ" vẫn cần đủ tên + số định danh; form có ô tick thì tích sau cùng.
    fields = enrich(_fields(**{**_CT01_KHOP_ME, "Ct01_ChuHoHoTen": "Nguyễn Văn Bố",
                               "Ct01_ChuHoSoDinhDanh": "012345678901"}))
    out = _by_name(fields)
    order = [f["name"] for f in fields]

    assert out["DkttChuHo"]["value"] == "NGUYỄN VĂN BỐ"
    assert out["DkttChuhoSoGiayTo"]["value"] == "012345678901"
    assert out["DkttMaQuanHe"]["value"] == "Con đẻ"
    assert order.index("DkttChuHo") < order.index("DkttIsTtBo")
    assert order.index("DkttChuhoSoGiayTo") < order.index("DkttIsTtBo")


def test_ct01_chu_ho_la_me_khop_ten_lay_so_dinh_danh_cua_me():
    out = _by_name(enrich(_fields(**{**_CT01_KHOP_ME, "Ct01_ChuHoSoDinhDanh": ""})))

    assert out["DkttIsTtMe"]["value"] is True
    assert out["DkttChuHo"]["value"] == "TRẦN THỊ MẸ"
    assert out["DkttChuhoSoGiayTo"]["value"] == "098765432109"
