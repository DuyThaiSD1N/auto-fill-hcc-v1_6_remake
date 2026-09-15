"""Unit test "[Bắc Ninh] Đăng ký biến động QSDĐ" (1.115468).

Theo spec (ánh xạ hồ sơ): đơn Mẫu 18 khớp CLASS eform-element-<Key>, GỘP 2 vợ chồng vào ô Tên/Giấy tờ.
Khối "được ủy quyền" (doiTuongKhac*) = NGƯỜI ỦY QUYỀN = CHỦ HỒ SƠ (KHÔNG phải người được ủy quyền).
Đính kèm 16 mã TP-H05 + File đính kèm khác. Phân loại LLM-first.
"""

from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.attach import catalog, planner
from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.process import mapper, schema
from app.procedures.registry import get_attach_pipeline, get_procedure

_KEY = "dang-ky-bien-dong-dat-dai-bac-ninh"

# Hồ sơ mẫu Nguyễn Văn Dũng + Nguyễn Thị Yến (vợ chồng nhận tặng cho), nộp qua ủy quyền Phan Mỹ Dung.
_SAMPLE = {
    "ChuHoSo_HoTen": "Nguyễn Văn Dũng",
    "ChuHoSo_GioiTinh": "Nam",
    "ChuHoSo_SoDinhDanh": "027087017758",
    "ChuHoSo_NgaySinh": "28/08/1987",
    "ChuHoSo_NgayCap": "26/09/2024",
    "ChuHoSo_NoiCap": "Bộ Công an",
    # Địa chỉ ưu tiên Đơn M18/tờ khai (Nam Sơn) — theo chốt của user, KHÔNG lấy CCCD (Văn Dương).
    "ChuHoSo_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Nam Sơn", "diaChi": ""},
    "ChuHoSo_DienThoai": "0983696787",
    "ChuHoSo_MaSoThue": "027087017758",
    "DongSuDung_HoTen": "Nguyễn Thị Yến",
    "DongSuDung_SoDinhDanh": "024189005605",
    "DongSuDung_NgaySinh": "04/03/1989",
    "Don_KinhGui": "Chi nhánh Văn phòng đăng ký đất đai liên phường Bắc Ninh",
    "Don_LoaiGiaoDich": "tặng cho",
    "Don_TenHopDong": "Hợp đồng tặng cho quyền sử dụng đất, số công chứng 2224/2026/CCGD",
    "Don_GiayToKem": "CCCD (bản sao chứng thực); Giấy chứng nhận kết hôn; Trích lục khai sinh; Giấy ủy quyền; Biên bản bàn giao đất",
    "Don_TranhChap": "Không có tranh chấp",
    "Don_RanhGioi": "Không thay đổi so với ranh giới được cấp Giấy chứng nhận",
}


def _fields(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _map(d: dict, options: dict | None = None) -> dict:
    mapped, _ = mapper.enrich(_fields(d), options)
    return {f["name"]: f["value"] for f in mapped}


def test_registration_don_gop_hai_vo_chong():
    got = _map(_SAMPLE)
    assert got[schema.K_KINHGUI] == "Chi nhánh Văn phòng đăng ký đất đai liên phường Bắc Ninh"
    # Tên(2) GỘP cả 2 người + sinh năm.
    assert got[schema.K_TEN] == "Nguyễn Văn Dũng, sinh năm 1987 và Nguyễn Thị Yến, sinh năm 1989"
    # Giấy tờ nhân thân GỘP 2 CCCD (kèm tên).
    assert got[schema.K_GIAYTO] == "027087017758 (Nguyễn Văn Dũng); 024189005605 (Nguyễn Thị Yến)"
    assert got[schema.K_DIACHI] == "Nam Sơn, Bắc Ninh"
    assert got[schema.K_MST] == "027087017758"
    assert got[schema.K_DIENTHOAI] == "0983696787"
    assert got[schema.K_NOIDUNG] == "Nhận tặng cho quyền sử dụng đất"
    # Mục IV(2) = hợp đồng; mục IV(3) = giấy tờ tùy thân/hộ tịch (KHÔNG gồm hợp đồng).
    assert "Hợp đồng tặng cho" in got[schema.K_GIAYTOKEM2]
    assert got[schema.K_GIAYTOKEM3].startswith("CCCD (bản sao")
    assert "Hợp đồng" not in got[schema.K_GIAYTOKEM3]
    assert got[schema.K_TRANHCHAP] == "Không có tranh chấp"
    assert got[schema.K_RANHGIOI].startswith("Không thay đổi")


def test_authorized_block_is_chu_ho_so_not_proxy():
    """doiTuongKhac* = CHỦ HỒ SƠ = người ủy quyền (Nguyễn Văn Dũng), KHÔNG phải người được ủy quyền."""
    got = _map(_SAMPLE, options={"purpose": "authorized_person"})
    assert got["doiTuongKhachoTen"] == "Nguyễn Văn Dũng"
    assert got["doiTuongKhacgioiTinhId"] == "Nam"
    assert got["doiTuongKhacsoDinhDanh"] == "027087017758"
    assert got["doiTuongKhacngayCap"] == "26/09/2024"
    assert got["doiTuongKhacnoiCap"] == "Bộ Công an"
    assert got["doiTuongKhacngaySinh"] == "28/08/1987"
    assert got["doiTuongKhacsoDienThoai"] == "0983696787"
    assert got["doiTuongKhactinhThanhId"] == "Bắc Ninh"
    assert got["doiTuongKhacphuongXaId"] == "Nam Sơn"
    assert got["doiTuongKhacdiaChiChiTiet"] == "Nam Sơn, Bắc Ninh"
    # KHÔNG lẫn field đơn.
    assert schema.K_TEN not in got


def test_optional_giayto_kem_khong_ep_mac_dinh():
    """"Có thì điền, không thì để trống": không có hợp đồng/giấy tờ kèm → ô (2)/(3) BỎ TRỐNG (không default)."""
    got = _map({"ChuHoSo_HoTen": "A", "ChuHoSo_SoDinhDanh": "1", "Don_LoaiGiaoDich": "tặng cho"})
    assert schema.K_GIAYTOKEM2 not in got  # không ép hd_default
    assert schema.K_GIAYTOKEM3 not in got
    assert schema.K_MIENGIAM not in got and schema.K_TRANHCHAP not in got
    # Ô bắt buộc "Nội dung biến động" vẫn suy ra được.
    assert got[schema.K_NOIDUNG] == "Nhận tặng cho quyền sử dụng đất"


def test_authorized_block_needs_chu_ho_so_identity():
    mapped, warnings = mapper.enrich(_fields({"Don_KinhGui": "X"}), {"purpose": "authorized_person"})
    assert mapped == [] and warnings and "chủ hồ sơ" in warnings[0].lower()


def test_registration_single_person_no_gop():
    got = _map({"ChuHoSo_HoTen": "Trần Thị B", "ChuHoSo_SoDinhDanh": "048301000999",
                "ChuHoSo_NgaySinh": "1990", "Don_LoaiGiaoDich": "chuyển nhượng"})
    assert got[schema.K_TEN] == "Trần Thị B, sinh năm 1990"
    assert got[schema.K_GIAYTO] == "048301000999 (Trần Thị B)"
    assert got[schema.K_NOIDUNG] == "Nhận chuyển nhượng quyền sử dụng đất"


def test_transaction_map_covers_new_types():
    for loai, noidung in [
        ("chuyển đổi", "Chuyển đổi quyền sử dụng đất nông nghiệp"),
        ("thừa kế", "Nhận thừa kế quyền sử dụng đất"),
        ("mua bán nhà ở có thời hạn", "Mua bán nhà ở có thời hạn"),
    ]:
        got = _map({"ChuHoSo_HoTen": "A", "Don_LoaiGiaoDich": loai})
        assert got[schema.K_NOIDUNG] == noidung, loai


def test_catalog_routes_tp_h05_and_supplementary():
    assert catalog.resolve("vb_tang_cho") == ("existing", "TP-H05.000080")
    assert catalog.resolve("hop_dong_chuyen_quyen") == ("existing", "TP-H05.000069")
    assert catalog.resolve("van_ban_dai_dien") == ("existing", "TP-H05.000079")
    assert catalog.resolve("gcn") == ("existing", "TP-H05.000040")
    assert catalog.resolve("don_bien_dong") == ("existing", "TP-H05.000026")
    for lbl in ("cccd", "ho_tich", "to_khai_thue", "bien_ban_ban_giao", "khac"):
        assert catalog.resolve(lbl) == ("supplementary", ""), lbl
    codes = [c for _, c, _ in catalog.CATALOG if c]
    assert len(codes) == 16 and len(set(codes)) == 16


def test_build_item_supplementary_and_existing():
    item = planner._build_item({"name": "ủy quyền.pdf"}, 0, "van_ban_dai_dien", "Giấy ủy quyền")
    assert item["target"] == "existing" and item["componentName"] == "TP-H05.000079"
    supp = planner._build_item({"name": "khai thue.pdf"}, 1, "to_khai_thue", "Tờ khai thuế")
    assert supp["target"] == "supplementary" and supp["componentName"] == ""


def test_schema_split_uyquyen_vs_don():
    """Ủy quyền chỉ nhân thân 1 người; Đơn thêm đồng sử dụng + nghiệp vụ; chung 6 trường _PERSON."""
    uq, don = schema.ALLOWED_UYQUYEN, schema.ALLOWED_DON
    # Ủy quyền có giới tính/ngày cấp/nơi cấp; Đơn KHÔNG cần (đơn không có ô riêng cho 3 cái này).
    assert {"ChuHoSo_GioiTinh", "ChuHoSo_NgayCap", "ChuHoSo_NoiCap"} <= uq
    assert not ({"ChuHoSo_GioiTinh", "ChuHoSo_NgayCap", "ChuHoSo_NoiCap"} & don)
    # Đơn có đồng sử dụng + MST + nghiệp vụ; ủy quyền KHÔNG.
    assert {"DongSuDung_HoTen", "ChuHoSo_MaSoThue", "Don_KinhGui", "Don_GiayToKem"} <= don
    assert not ({"DongSuDung_HoTen", "Don_KinhGui"} & uq)
    # Chung 6 trường nhân thân.
    assert {"ChuHoSo_HoTen", "ChuHoSo_SoDinhDanh", "ChuHoSo_NgaySinh", "ChuHoSo_ThuongTru",
            "ChuHoSo_DienThoai", "ChuHoSo_Email"} <= (uq & don)


def test_registry_entry():
    proc = get_procedure(_KEY)
    assert proc is not None and proc["mode"] == "agent" and proc["hasAttachmentStep"] is True
    assert "maThuTucHanhChinh=1.115468" in proc["detect"]["urlIncludes"]
    assert "dichvucong.bacninh.gov.vn" in proc["detect"]["urlScope"]
    assert get_attach_pipeline(_KEY) is not None
