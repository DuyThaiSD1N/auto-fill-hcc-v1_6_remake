"""Mapper kết hôn: chỉ upload 2 CCCD vẫn điền tối đa — các ô suy diễn gắn default (viền vàng)."""
from app.pipelines.ket_hon.process.mapper import enrich


def _fields(**kv):
    return [{"name": k, "value": v} for k, v in kv.items()]


def _by_name(out):
    return {f["name"]: f for f in out}


def test_chi_co_cccd_suy_luan_lan_dau_dan_toc_kinh():
    out = _by_name(enrich(_fields(
        CccdNam_HoTen="Nguyễn Văn A", CccdNam_SoDinhDanh="012345678901",
        CccdNu_HoTen="Trần Thị B", CccdNu_SoDinhDanh="098765432109",
    )))
    for dst in ("BenNam", "BenNu"):
        assert out[f"DanToc{dst}"]["value"] == "Kinh" and out[f"DanToc{dst}"]["default"] is True
        assert out[f"SoLanKetHon_{dst}"]["value"] == "1" and out[f"SoLanKetHon_{dst}"]["default"] is True
        tt = out[f"LoaiTinhTrangHonNhan_{dst}"]
        assert tt["value"] == "Hiện tại chưa đăng ký kết hôn với ai" and tt["default"] is True
    # Không tác động radio "Loại đăng ký"; chỉ giữ mặc định không cấp bản sao.
    assert "loaiDangKy" not in out
    assert out["CapBanSao"]["value"] == "NO" and out["CapBanSao"]["default"] is True


def test_giay_to_ghi_ro_thi_khong_gan_default():
    out = _by_name(enrich(_fields(
        CccdNam_HoTen="Nguyễn Văn A", CccdNam_SoDinhDanh="012345678901",
        CccdNam_DanToc="Tày", CccdNam_SoLanKetHon="2",
    )))
    assert out["DanTocBenNam"]["value"] == "Tày" and "default" not in out["DanTocBenNam"]
    assert out["SoLanKetHon_BenNam"]["value"] == "2" and "default" not in out["SoLanKetHon_BenNam"]
    # Lần 2 → KHÔNG tự suy tình trạng "chưa đăng ký kết hôn với ai".
    assert "LoaiTinhTrangHonNhan_BenNam" not in out


def test_khong_co_nguoi_nao_thi_khong_de_radio_mo_coi():
    assert enrich([]) == []
