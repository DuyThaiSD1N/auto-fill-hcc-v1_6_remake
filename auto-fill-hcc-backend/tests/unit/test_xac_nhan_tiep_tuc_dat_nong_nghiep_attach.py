"""[Lào Cai] 1.115677 — đính kèm bảng "Thành phần hồ sơ" bước 3 (bảng phẳng 2 dòng).

Khoá những điều dễ vỡ:
  * slotIndex phải đúng thứ tự DOM 2 dòng — bảng không có tiêu đề nhánh nên FE chỉ còn thứ tự để khớp;
  * MỘT TỆP chỉ vào MỘT dòng — số lượt đính không được vượt số tệp;
  * giấy tờ không có dòng riêng (mảnh trích đo rời, giấy uỷ quyền, CCCD) phải xuống "Giấy tờ khác",
    không im lặng bỏ tệp;
  * hồ sơ mẫu quét mảnh trích đo chung file Giấy chứng nhận → phải nhắc cán bộ.
"""

from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.attach import planner
from app.procedures.registry import get_attach_pipeline, public_list

_KEY = "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep"

# Đúng 2 tệp của hồ sơ mẫu trong ảnh ánh xạ (4 trang: Đơn 1 trang + GCN 3 trang).
_HO_SO_MAU = [
    ("don_1787621423.pdf", "don_mau_39"),
    ("gcn_1787621415.pdf", "gcn"),
]


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _plan(pairs):
    files = _files([n for n, _ in pairs])
    llm_types = {i: t for i, (_, t) in enumerate(pairs)}
    return planner.build_plan_items(files, llm_types)


def _by_file(attachments):
    return {item["fileName"]: item for item in attachments}


def test_registry_da_bat_buoc_dinh_kem():
    entry = next(p for p in public_list() if p["key"] == _KEY)
    assert entry["hasAttachmentStep"] is True
    assert get_attach_pipeline(_KEY) is not None


def test_ho_so_mau_vao_dung_hai_dong():
    attachments, warnings, _ = _plan(_HO_SO_MAU)
    by_file = _by_file(attachments)

    assert by_file["don_1787621423.pdf"]["slotIndex"] == 0
    assert by_file["gcn_1787621415.pdf"]["slotIndex"] == 1

    # Cả hai tệp đều là fixed-slot và đều phải tích checkbox dòng, nếu không cổng không nhận tệp.
    for item in attachments:
        assert item["target"] == "fixed-slot"
        assert item["tickRow"] is True
        assert item["needsAddComponent"] is False

    # Hồ sơ mẫu đủ cả hai thành phần bắt buộc → không được nhắc thiếu dòng.
    assert not any("Chưa có tệp nào cho dòng" in w for w in warnings)


def test_hai_dong_dung_slot_key_khac_nhau():
    attachments, _, _ = _plan(_HO_SO_MAU)
    by_file = _by_file(attachments)
    assert by_file["don_1787621423.pdf"]["slotKey"] == "lc_115677_row_0"
    assert by_file["gcn_1787621415.pdf"]["slotKey"] == "lc_115677_row_1"


def test_nhieu_tep_cung_dong_dung_chung_slot_key():
    """Engine gom item theo slotKey rồi bơm cả loạt vào một ô — hai tệp GCN (sổ + trang bổ sung) phải
    dùng chung slotKey, nếu không tệp thứ hai sẽ thấy ô đã bị dùng và báo lỗi."""
    attachments, _, _ = _plan([("gcn_q1.pdf", "gcn"), ("gcn_q2.pdf", "gcn")])
    assert len({item["slotKey"] for item in attachments}) == 1


def test_moi_tep_chi_vao_dung_mot_dong():
    attachments, _, _ = _plan(_HO_SO_MAU)
    assert len(attachments) == len(_HO_SO_MAU)
    assert len({item["fileIndex"] for item in attachments}) == len(_HO_SO_MAU)


def test_thieu_thanh_phan_bat_buoc_thi_nhac():
    _, warnings, _ = _plan([("don_1787621423.pdf", "don_mau_39")])
    assert any("Giấy chứng nhận đã cấp" in w for w in warnings)

    _, warnings, _ = _plan([("gcn_1787621415.pdf", "gcn")])
    assert any("Mẫu số 39" in w for w in warnings)


def test_giay_to_khong_co_dong_rieng_xuong_giay_to_khac():
    attachments, _, _ = _plan([
        ("MTD_rieng.pdf", "manh_trich_do"),
        ("uy_quyen.pdf", "van_ban_dai_dien"),
        ("CCCD_hai_vo_chong.pdf", "giay_to_nhan_than"),
    ])
    by_file = _by_file(attachments)

    for name in ("MTD_rieng.pdf", "uy_quyen.pdf", "CCCD_hai_vo_chong.pdf"):
        assert by_file[name]["target"] == "new"
        assert by_file[name]["needsAddComponent"] is True
        # Cổng iGate: bấm "Chọn tệp tin" mở hộp thoại file của OS → FE chỉ được gán thẳng.
        assert by_file[name]["noChooserClick"] is True
        assert "slotIndex" not in by_file[name]
    assert by_file["MTD_rieng.pdf"]["documentName"] == "Mảnh trích đo bản đồ địa chính thửa đất"


def test_canh_bao_cccd_khong_thuoc_thanh_phan_ho_so():
    _, warnings, _ = _plan(_HO_SO_MAU + [("CCCD.pdf", "giay_to_nhan_than")])
    assert any("KHÔNG thuộc thành phần hồ sơ" in w for w in warnings)


def test_canh_bao_manh_trich_do_quet_gop_trong_file_gcn():
    """Hồ sơ mẫu: mảnh trích đo địa chính nằm ở trang 3 của file Giấy chứng nhận."""
    _, warnings, _ = _plan(_HO_SO_MAU)
    assert any("mảnh trích đo" in w for w in warnings)


def test_khong_canh_bao_quet_gop_khi_da_co_tep_rieng():
    _, warnings, _ = _plan(_HO_SO_MAU + [("MTD_rieng.pdf", "manh_trich_do")])
    assert not any("thường quét gộp" in w for w in warnings)


def test_tep_chua_ro_loai_van_duoc_dinh_kem_va_canh_bao():
    attachments, warnings, _ = _plan([("Tai_lieu_la.pdf", "khac")])
    assert len(attachments) == 1
    assert attachments[0]["target"] == "new"
    # Giữ tên thật của tệp để cán bộ biết là giấy gì.
    assert "Tai lieu la" in attachments[0]["documentName"]
    assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_ten_dong_giay_to_khac_khong_trung_nhau():
    """documentName thành TÊN DÒNG ở "Giấy tờ khác" — trùng tên là hai dòng đè nhau."""
    attachments, _, _ = _plan([
        ("CCCD_ong_Minh.pdf", "giay_to_nhan_than"),
        ("CCCD_ba_Vu.pdf", "giay_to_nhan_than"),
    ])
    names = [item["documentName"] for item in attachments]
    assert len(set(names)) == 2


def test_llm_tra_loai_la_hoac_hong_thi_khong_mat_tep():
    attachments, _, classified = planner.build_plan_items(
        _files(["a.pdf", "b.pdf"]), {0: "loai_khong_ton_tai"}
    )
    assert len(attachments) == 2
    assert all(item["target"] == "new" for item in attachments)
    assert classified[1]["source"] == "default"


def test_khong_co_tep_nao_thi_bao_ro():
    attachments, warnings, _ = planner.build_plan_items([], {})
    assert attachments == []
    assert any("Không có tài liệu nào" in w for w in warnings)


def test_slot_index_phu_kin_bang_hai_dong():
    """Mọi dòng khai trong _ROWS phải có ít nhất một docType trỏ tới, và không trỏ ra ngoài bảng."""
    routed = {slot for slot, _ in planner._ROUTES.values()}
    assert routed == set(planner._ROWS)
    assert max(routed) == 1
