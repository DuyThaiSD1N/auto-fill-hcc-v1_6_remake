"""Mapper kết hôn: chỉ upload 2 CCCD — ô suy luận được gắn default (viền vàng), ô không có nguồn để trống."""
from app.pipelines.ket_hon.process.mapper import enrich


def _fields(**kv):
    return [{"name": k, "value": v} for k, v in kv.items()]


def _by_name(out):
    return {f["name"]: f for f in out}


def test_chi_co_cccd_suy_luan_lan_dau_khong_bia_dan_toc():
    out = _by_name(enrich(_fields(
        BenNam_HoTen="Nguyễn Văn A", BenNam_SoDinhDanh="012345678901",
        BenNu_HoTen="Trần Thị B", BenNu_SoDinhDanh="098765432109",
    )))
    for dst in ("BenNam", "BenNu"):
        # CCCD không ghi dân tộc → để trống, không mặc định "Kinh".
        assert f"DanToc{dst}" not in out
        assert out[f"SoLanKetHon_{dst}"]["value"] == "1" and out[f"SoLanKetHon_{dst}"]["default"] is True
        tt = out[f"LoaiTinhTrangHonNhan_{dst}"]
        assert tt["value"] == "Hiện tại chưa đăng ký kết hôn với ai" and tt["default"] is True
    # Không tác động radio "Loại đăng ký" và "Cấp bản sao" — giấy tờ không nói thì cán bộ tự chọn.
    assert "loaiDangKy" not in out
    assert "CapBanSao" not in out


def test_giay_to_ghi_ro_thi_khong_gan_default():
    out = _by_name(enrich(_fields(
        BenNam_HoTen="Nguyễn Văn A", BenNam_SoDinhDanh="012345678901",
        BenNam_DanToc="Tày", BenNam_SoLanKetHon="2",
    )))
    assert out["DanTocBenNam"]["value"] == "Tày" and "default" not in out["DanTocBenNam"]
    assert out["SoLanKetHon_BenNam"]["value"] == "2" and "default" not in out["SoLanKetHon_BenNam"]
    # Lần 2 → KHÔNG tự suy tình trạng "chưa đăng ký kết hôn với ai".
    assert "LoaiTinhTrangHonNhan_BenNam" not in out


def test_khong_co_nguoi_nao_thi_khong_de_radio_mo_coi():
    assert enrich([]) == []
