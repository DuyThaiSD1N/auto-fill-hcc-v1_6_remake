"""XNTTHN có giấy ủy quyền: tờ khai viết tay đọc lệch 1 chữ số CCCD của người được cấp.

Hồ sơ thật (Phạm Minh Kha ủy quyền cho mẹ Phó Thị Khoa): OCR tờ khai ra "068194003466" và tên
"Phạm Nhung Khae", trong khi giấy ủy quyền ghi đúng "068194003446". Bản cũ coi là hai người nên
mục II bỏ giới tính/dân tộc và lấy "chỗ ở hiện tại" trên giấy ủy quyền (Số 2 Bát Nàn, TP HCM)
thay cho nơi cư trú khai trên tờ khai → tỉnh/xã không khớp option nào.
"""
from app.pipelines.xac_nhan_tthn.process.mapper import enrich


def _run(**kv):
    return {f["name"]: f["value"] for f in enrich([{"name": k, "value": v} for k, v in kv.items()])}


_TO_KHAI_NOI_CU_TRU = {
    "quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường Xuân Hương", "diaChi": "64 Nguyễn Thế Oan Khai",
}

_HO_SO = dict(
    Cccd_HoTen="PHÓ THỊ KHOA",
    Cccd_SoDinhDanh="020173001080",
    Cccd_NgaySinh="21/03/1973",
    ToKhaiYeuCau_HoTen="Phó Thị Khoa",
    ToKhaiYeuCau_NgaySinh="21/03/1973",
    ToKhaiYeuCau_SoDinhDanh="020173001080",
    ToKhaiYeuCau_NoiCuTru=_TO_KHAI_NOI_CU_TRU,
    ToKhaiYeuCau_QuanHe="Mẹ đẻ",
    ToKhai_HoTen="Phạm Nhung Khae",
    ToKhai_NgaySinh="21/05/1994",
    ToKhai_GioiTinh="Nữ",
    ToKhai_DanToc="Kinh",
    ToKhai_SoDinhDanh="068194003466",
    ToKhai_NoiCuTru=_TO_KHAI_NOI_CU_TRU,
    PoA_SubjectName="Phạm Minh Kha",
    PoA_SubjectDoB="02/05/1994",
    PoA_SubjectIdNumber="068194003446",
    PoA_SubjectIdDate="06/08/2022",
    PoA_SubjectAddress={"tinh": "TP Hồ Chí Minh", "xa": "Thạnh Mỹ Lợi", "diaChi": "Số 2 Bát Nàn"},
)


def test_lech_mot_chu_so_cung_nam_sinh_thi_lay_gioi_tinh_dan_toc_noi_cu_tru_tu_to_khai():
    out = _run(**_HO_SO)
    assert out["HoVaTenC1"] == "PHẠM MINH KHA"
    assert out["SoDinhDanhC1"] == "068194003446"
    assert out["GioiTinhC1"] == "Nữ"
    assert out["DanTocC1"] == "Kinh"
    residence = out["nxnNoiCuTru_TrongNuoc"]
    assert residence["tinh"].endswith("Lâm Đồng")
    assert "Xuân Hương" in residence["xa"]
    assert "Bát Nàn" not in residence["diaChi"]


def test_ten_duong_viet_tay_sua_theo_the_can_cuoc_cua_nguoi_uy_quyen():
    out = _run(**_HO_SO, PoA_SubjectCccdNoiCuTru={
        "quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường 1", "diaChi": "64, Nguyễn Thị Minh Khai",
    })
    residence = out["nxnNoiCuTru_TrongNuoc"]
    assert residence["diaChi"] == "64 Nguyễn Thị Minh Khai"
    assert "Xuân Hương" in residence["xa"]   # xã giữ theo tờ khai, không lấy "Phường 1" cũ trên thẻ


def test_khac_so_nha_thi_khong_sua_ten_duong():
    out = _run(**_HO_SO, PoA_SubjectCccdNoiCuTru={
        "tinh": "Lâm Đồng", "diaChi": "22B Nguyễn Thị Minh Khai",
    })
    assert out["nxnNoiCuTru_TrongNuoc"]["diaChi"] == "64 Nguyễn Thế Oan Khai"


def _run_fields(**kv):
    return {f["name"]: f for f in enrich([{"name": k, "value": v} for k, v in kv.items()])}


def test_khong_xac_nhan_duoc_cung_nguoi_thi_van_lay_to_khai_nhung_vien_vang():
    """Lệch số + khác năm sinh + khác họ: không kết luận cùng người, nhưng tờ khai mục II vốn là
    người cần giấy → vẫn điền giới tính/dân tộc/nơi cư trú từ tờ khai, đánh dấu default để soát."""
    ho_so = {**_HO_SO, "ToKhai_HoTen": "Trần Văn Nam", "ToKhai_NgaySinh": "01/01/1990"}
    out = _run_fields(**ho_so)
    # Nhân thân giấy tờ vẫn theo giấy ủy quyền, không viền vàng.
    assert out["HoVaTenC1"]["value"] == "PHẠM MINH KHA"
    assert out["NgaySinhC1"]["value"] == "02/05/1994"
    assert not out["NgaySinhC1"].get("default")
    # Giấy ủy quyền không ghi → lấy tờ khai, viền vàng.
    assert out["GioiTinhC1"]["value"] == "Nữ" and out["GioiTinhC1"]["default"] is True
    assert out["DanTocC1"]["value"] == "Kinh" and out["DanTocC1"]["default"] is True
    residence = out["nxnNoiCuTru_TrongNuoc"]
    assert "Bát Nàn" not in residence["value"]["diaChi"]
    assert residence["default"] is True


def test_cung_nguoi_thi_khong_vien_vang():
    out = _run_fields(**_HO_SO)
    assert not out["DanTocC1"].get("default")
    assert not out["nxnNoiCuTru_TrongNuoc"].get("default")


def test_the_can_cuoc_nguoi_uy_quyen_thang_giay_uy_quyen_va_to_khai():
    out = _run(
        **_HO_SO,
        PoA_SubjectGender="Nam",                 # giấy ủy quyền ghi sai
        PoA_SubjectCccdHoTen="PHẠM MINH KHA",
        PoA_SubjectCccdSoDinhDanh="068194003446",
        PoA_SubjectCccdNgaySinh="02/05/1994",
        PoA_SubjectCccdGioiTinh="Nữ",
        PoA_SubjectCccdNgayCap="07/08/2022",
        PoA_SubjectCccdNoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    )
    assert out["HoVaTenC1"] == "PHẠM MINH KHA"
    assert out["GioiTinhC1"] == "Nữ"
    assert out["NgaySinhC1"] == "02/05/1994"      # thẻ thắng ngày sinh OCR tờ khai 21/05/1994
    assert out["NgayCapDDC1"] == "07/08/2022"
    assert out["SoDinhDanhC1"] == "068194003446"


def test_the_khac_han_so_giay_uy_quyen_thi_bo_the():
    out = _run(
        **_HO_SO,
        PoA_SubjectCccdHoTen="NGUYỄN VĂN A",
        PoA_SubjectCccdSoDinhDanh="001099000111",
        PoA_SubjectCccdGioiTinh="Nam",
    )
    assert out["HoVaTenC1"] == "PHẠM MINH KHA"
    assert out["GioiTinhC1"] == "Nữ"
    assert out["SoDinhDanhC1"] == "068194003446"


def test_khong_uy_quyen_trung_so_thi_gioi_tinh_theo_the():
    out = _run(
        ToKhai_HoTen="NGUYEN THI HOA",
        ToKhai_SoDinhDanh="036301012326",
        ToKhai_GioiTinh="Nam",                   # OCR tờ khai sai
        Cccd_HoTen="NGUYỄN THỊ HOÀ",
        Cccd_SoDinhDanh="036301012326",
        Cccd_GioiTinh="Nữ",
    )
    assert out["GioiTinhC1"] == "Nữ"


def test_trung_so_thi_ngay_sinh_theo_the_ca_muc_i_va_muc_ii():
    out = _run(
        ToKhaiYeuCau_HoTen="NGUYEN THI HOA",
        ToKhaiYeuCau_SoDinhDanh="036301012326",
        ToKhaiYeuCau_NgaySinh="12/03/2001",      # OCR tờ khai sai
        ToKhaiYeuCau_QuanHe="Bản thân",
        ToKhai_HoTen="NGUYEN THI HOA",
        ToKhai_SoDinhDanh="036301012326",
        ToKhai_NgaySinh="12/03/2001",
        Cccd_HoTen="NGUYỄN THỊ HOÀ",
        Cccd_SoDinhDanh="036301012326",
        Cccd_NgaySinh="21/03/2001",
    )
    assert out["NgaySinhC"] == "21/03/2001"
    assert out["NgaySinhC1"] == "21/03/2001"


def test_khac_so_thi_ngay_sinh_giu_to_khai():
    out = _run(
        ToKhai_HoTen="TRẦN VĂN NAM",
        ToKhai_SoDinhDanh="001099000111",
        ToKhai_NgaySinh="01/01/1999",
        Cccd_HoTen="NGUYỄN THỊ HOÀ",
        Cccd_SoDinhDanh="036301012326",
        Cccd_NgaySinh="21/03/2001",
    )
    assert out["NgaySinhC1"] == "01/01/1999"


def test_khong_uy_quyen_khac_so_thi_gioi_tinh_giu_to_khai():
    out = _run(
        ToKhai_HoTen="TRẦN VĂN NAM",
        ToKhai_SoDinhDanh="001099000111",
        ToKhai_GioiTinh="Nam",
        Cccd_HoTen="NGUYỄN THỊ HOÀ",
        Cccd_SoDinhDanh="036301012326",
        Cccd_GioiTinh="Nữ",
    )
    assert out["GioiTinhC1"] == "Nam"
