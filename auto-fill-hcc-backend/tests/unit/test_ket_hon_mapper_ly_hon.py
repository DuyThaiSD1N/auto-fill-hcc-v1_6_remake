"""Mapper kết hôn: hồ sơ hai bên đều đã ly hôn (mỗi bên một quyết định riêng).

Ca thật ngoài quầy: cùng một file PDF chứa QĐ ly hôn của bên nữ (An Lão, Hải Phòng) và
QĐ ly hôn của bên nam (thành phố Sơn La); LLM từng gán QĐ của bên nam cho CẢ HAI bên,
đồng thời bỏ trống "Kết hôn lần thứ mấy" và dân tộc.
"""
from app.pipelines.ket_hon.process.mapper import enrich


def _fields(**kv):
    return [{"name": k, "value": v} for k, v in kv.items()]


def _by_name(out):
    return {f["name"]: f for f in out}


_HAI_BEN_DA_LY_HON = dict(
    CccdNam_HoTen="MÈ MINH TUẤN", CccdNam_SoDinhDanh="014090014602",
    CccdNam_TinhTrangHonNhan="3",
    CccdNam_BanAnLyHon_So="52/2023/QĐST-HNGĐ",
    CccdNam_BanAnLyHon_Ngay="17/02/2023",
    CccdNam_BanAnLyHon_CoQuan="Tòa án nhân dân thành phố Sơn La",
    CccdNam_BanAnLyHon_DuongSu="Lường Thị Ly; Mè Minh Tuấn",
    CccdNu_HoTen="NGUYỄN HOÀNG HẢI THANH", CccdNu_SoDinhDanh="068190007436",
    CccdNu_TinhTrangHonNhan="3",
)


def test_moi_ben_giu_dung_quyet_dinh_ly_hon_cua_minh():
    out = _by_name(enrich(_fields(
        **_HAI_BEN_DA_LY_HON,
        CccdNu_BanAnLyHon_So="70/2018/QĐST-HNGĐ",
        CccdNu_BanAnLyHon_Ngay="09/05/2018",
        CccdNu_BanAnLyHon_CoQuan="Tòa án nhân dân huyện An Lão, thành phố Hải Phòng",
        CccdNu_BanAnLyHon_DuongSu="Nguyễn Hoàng Hải Thanh; Lưu Hùng Nguyên",
    )))
    assert out["TTHN_LyHonBenNam"]["value"]["soBanAnQuyetDinhLyHon"] == "52/2023/QĐST-HNGĐ"
    assert out["TTHN_LyHonBenNu"]["value"] == {
        "soBanAnQuyetDinhLyHon": "70/2018/QĐST-HNGĐ",
        "ngayCapBanAnQuyetDinhLyHon": "09/05/2018",
        "coQuanCapBanAnQuyetDinhLyHon": "Tòa án nhân dân huyện An Lão, thành phố Hải Phòng",
    }


def test_bo_quyet_dinh_ly_hon_gan_nham_sang_ben_kia():
    # LLM copy nguyên QĐ của bên nam sang bên nữ: đương sự không có tên bên nữ → phải bỏ hẳn,
    # thà để trống cho cán bộ nhập tay còn hơn điền số/ngày/tòa án sai.
    out = _by_name(enrich(_fields(
        **_HAI_BEN_DA_LY_HON,
        CccdNu_BanAnLyHon_So="52/2023/QĐST-HNGĐ",
        CccdNu_BanAnLyHon_Ngay="17/02/2023",
        CccdNu_BanAnLyHon_CoQuan="Tòa án nhân dân thành phố Sơn La",
        CccdNu_BanAnLyHon_DuongSu="Lường Thị Ly; Mè Minh Tuấn",
    )))
    assert "TTHN_LyHonBenNu" not in out
    assert out["TTHN_LyHonBenNam"]["value"]["soBanAnQuyetDinhLyHon"] == "52/2023/QĐST-HNGĐ"
    # Tình trạng hôn nhân của bên nữ vẫn giữ (có thể suy từ nguồn khác), chỉ phần văn bản bị bỏ.
    assert out["LoaiTinhTrangHonNhan_BenNu"]["value"].startswith("Đã đăng ký kết hôn")


def test_llm_khong_tra_duong_su_thi_giu_nguyen_hanh_vi_cu():
    out = _by_name(enrich(_fields(
        CccdNu_HoTen="Nguyễn Hoàng Hải Thanh", CccdNu_SoDinhDanh="068190007436",
        CccdNu_TinhTrangHonNhan="3", CccdNu_BanAnLyHon_So="70/2018/QĐST-HNGĐ",
    )))
    assert out["TTHN_LyHonBenNu"]["value"] == {"soBanAnQuyetDinhLyHon": "70/2018/QĐST-HNGĐ"}


def test_da_ly_hon_thi_suy_ra_ket_hon_lan_2():
    out = _by_name(enrich(_fields(**_HAI_BEN_DA_LY_HON)))
    for dst in ("BenNam", "BenNu"):
        so_lan = out[f"SoLanKetHon_{dst}"]
        assert so_lan["value"] == "2" and so_lan["default"] is True


def test_so_lan_tren_giay_luon_thang_suy_dien():
    out = _by_name(enrich(_fields(
        CccdNam_HoTen="Mè Minh Tuấn", CccdNam_SoDinhDanh="014090014602",
        CccdNam_TinhTrangHonNhan="3", CccdNam_SoLanKetHon="3",
    )))
    assert out["SoLanKetHon_BenNam"]["value"] == "3"
    assert "default" not in out["SoLanKetHon_BenNam"]


def test_giay_to_khong_ghi_dan_toc_thi_de_trong_cho_fe_to_do():
    # Không nguồn nào ghi dân tộc → không điền, không đoán: ô "-- Chọn --" còn trống sẽ được
    # markAllEmptyFieldsRed() bên extension tô đỏ để cán bộ tự chọn.
    out = _by_name(enrich(_fields(**_HAI_BEN_DA_LY_HON)))
    assert "DanTocBenNam" not in out and "DanTocBenNu" not in out


def test_dan_toc_doc_duoc_tren_giay_thi_khong_to_vang():
    out = _by_name(enrich(_fields(
        CccdNam_HoTen="Mè Minh Tuấn", CccdNam_SoDinhDanh="014090014602",
        CccdNam_DanToc="Thái",
        CccdNu_HoTen="Lường Thị Ly", CccdNu_SoDinhDanh="068190007436",
        CccdNu_DanToc="H'Mông",
    )))
    assert out["DanTocBenNam"]["value"] == "Thái" and "default" not in out["DanTocBenNam"]
    assert out["DanTocBenNu"]["value"] == "Mông (Hmông)"
