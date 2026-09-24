"""[Lào Cai - Cấp Sở] Xóa đăng ký biện pháp bảo đảm (1.011443.H38) — eForm iGate + đính kèm fixed-slot.

Khoá các điểm dễ vỡ: Phiếu 03a có chữ ký bên nhận bảo đảm được đính CHUNG vào dòng "Văn bản đồng ý xóa
thế chấp", dòng GCN mang "Số bản" = số trang, đối tượng nộp hồ sơ phát theo VALUE (CN/DN) và lọc ô ẩn.
"""

from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_lao_cai.attach import planner
from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_lao_cai.process import mapper
from app.procedures.registry import public_list

_KEY = "xoa-dang-ky-bien-phap-bao-dam-lao-cai"
_ANCHOR = {"formContext": {"applicantFullname": "TRẦN THỊ MẪU", "applicantIdentityNumber": "010180001234"}}

_CA_NHAN = [
    {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ MẪU"},
    {"name": "ChuHoSo_LaToChuc", "value": False},
    {"name": "ChuHoSo_GioiTinh", "value": "Nữ"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "010180001234"},
    {"name": "ChuHoSo_NgayCap", "value": "10/05/2022"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục CSQLHC về TTXH"},
    {"name": "ChuHoSo_DienThoai", "value": "0912000111"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Phường Cam Đường", "diaChi": "Tổ dân phố số 2"}},
]


def _entry():
    return next(p for p in public_list() if p["key"] == _KEY)


def _names(fields):
    return {f["name"]: f["value"] for f in fields}


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _by_slot(attachments):
    return {(a["fileIndex"], a.get("slotIndex")): a for a in attachments}


def test_co_trong_registry_va_khoa_dung_cong_lao_cai():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlScope"] == ["dichvucong.laocai.gov.vn"]


def test_ca_nhan_phat_doi_tuong_CN_va_bo_o_to_chuc():
    fields, warnings = mapper.enrich(_CA_NHAN, _ANCHOR)
    by_name = _names(fields)

    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert by_name["ChuHoSo_tenChuHoSo"] == "TRẦN THỊ MẪU"
    assert by_name["ChuHoSo_soCMNDChuHoSo"] == "010180001234"
    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert by_name["ChuHoSo_diaChiChuHoSo"] == "Tổ dân phố số 2"
    # Người đăng nhập chính là người yêu cầu → khối người nộp lấy đủ nhân thân + điện thoại trên phiếu.
    assert by_name["CongDan_soCmnd"] == "010180001234"
    assert by_name["CongDan_diDong"] == "0912000111"
    assert by_name["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert "ChuHoSo_tenCoQuanToChucCHS" not in by_name
    assert not warnings


def test_to_chuc_phat_DN_va_khong_phat_o_ca_nhan_bi_an():
    fields, _ = mapper.enrich(
        [
            {"name": "ChuHoSo_HoTen", "value": "LÊ VĂN ĐẠI DIỆN"},
            {"name": "ChuHoSo_LaToChuc", "value": True},
            {"name": "ChuHoSo_TenToChuc", "value": "QUỸ TÍN DỤNG NHÂN DÂN MINH HỌA"},
            {"name": "ChuHoSo_MaSoThue", "value": "5200000001"},
            {"name": "ChuHoSo_SoDinhDanh", "value": "010090001111"},
            {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Phường Cam Đường", "diaChi": "Số 1"}},
        ],
        _ANCHOR,
    )
    by_name = _names(fields)

    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "DN"
    assert by_name["ChuHoSo_tenCoQuanToChucCHS"] == "QUỸ TÍN DỤNG NHÂN DÂN MINH HỌA"
    assert by_name["ChuHoSo_maSoThueChuHoSo"] == "5200000001"
    for hidden in ("ChuHoSo_tenChuHoSo", "ChuHoSo_soCMNDChuHoSo", "ChuHoSo_gioiTinhChuHoSo"):
        assert hidden not in by_name


def test_nguoi_dai_dien_tren_phieu_ma_khong_co_uy_quyen_thi_canh_bao():
    _, warnings = mapper.enrich(
        _CA_NHAN + [{"name": "Don_NguoiDaiDien", "value": "Ông Phạm Văn Đại"}],
        _ANCHOR,
    )
    assert any("Phạm Văn Đại" in w and "ủy quyền" in w for w in warnings)


def test_phieu_co_chu_ky_ben_nhan_bao_dam_dinh_chung_vao_dong_dong_y():
    files = _files(["scan_phieu.pdf", "scan_gcn.pdf"])
    attachments, warnings, _ = planner.build_plan_items(files, {
        0: {"docType": "phieu_yc_03a", "securedPartySigned": True},
        1: {"docType": "gcn", "gcnPages": 4},
    })
    slots = _by_slot(attachments)

    assert slots[(1, 0)]["soBan"] == 4
    assert slots[(1, 0)]["tickRow"] is True
    assert slots[(0, 1)]["target"] == "fixed-slot"
    # Cùng tệp phiếu, khác dòng và khác slotKey để FE đính hai lượt riêng.
    assert slots[(0, 2)]["slotKey"] != slots[(0, 1)]["slotKey"]
    assert (0, 3) not in slots
    assert any("đính chung" in w for w in warnings)


def test_phieu_chua_co_chu_ky_ben_nhan_bao_dam_thi_khong_dinh_dong_dong_y():
    attachments, warnings, _ = planner.build_plan_items(
        _files(["phieu.pdf", "gcn.pdf"]),
        {0: {"docType": "phieu_yc_03a", "securedPartySigned": False}, 1: {"docType": "gcn"}},
    )
    assert all(a.get("slotIndex") != 2 for a in attachments)
    # Không đếm được trang thì không đụng tới ô Số bản.
    assert all("soBan" not in a for a in attachments)
    assert any("văn bản đồng ý" in w for w in warnings)


def test_van_ban_dong_y_rieng_uu_tien_hon_phieu():
    attachments, _, _ = planner.build_plan_items(
        _files(["phieu.pdf", "cong_van.pdf"]),
        {0: {"docType": "phieu_yc_03a", "securedPartySigned": True}, 1: {"docType": "van_ban_dong_y_xoa"}},
    )
    assert [a["fileIndex"] for a in attachments if a.get("slotIndex") == 2] == [1]


def test_cccd_vao_giay_to_khac_co_ten_va_khong_bo_sot_tep():
    files = _files(["phieu.pdf", "cccd.pdf", "la.pdf"])
    attachments, _, _ = planner.build_plan_items(files, {
        0: {"docType": "phieu_yc_03a"},
        1: {"docType": "cccd", "documentName": "Căn cước công dân Trần Thị Mẫu"},
    })
    news = [a for a in attachments if a["target"] == "new"]

    assert {a["fileIndex"] for a in attachments} == {0, 1, 2}
    assert [a["documentName"] for a in news] == ["Căn cước công dân Trần Thị Mẫu", "Tài liệu khác"]
    assert all(a["needsAddComponent"] and a["noChooserClick"] for a in news)


def test_tep_gop_phieu_va_gcn_phu_ca_hai_dong():
    attachments, _, _ = planner.build_plan_items(
        _files(["gop.pdf"]),
        {0: {"docType": "phieu_yc_03a", "alsoTypes": ["gcn", "cccd"]}},
    )
    assert sorted(a["slotIndex"] for a in attachments) == [0, 1]


def test_gcn_pages_phi_ly_bi_bo():
    attachments, _, _ = planner.build_plan_items(_files(["gcn.pdf"]), {0: {"docType": "gcn", "gcnPages": 40}})
    assert "soBan" not in attachments[0]
