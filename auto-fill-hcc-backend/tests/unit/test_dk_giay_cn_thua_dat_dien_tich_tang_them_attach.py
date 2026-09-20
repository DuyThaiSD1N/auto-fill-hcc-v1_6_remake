"""[Lào Cai] 1.115694 — đính kèm bảng "Thành phần hồ sơ" bước 3 (bảng phẳng 5 dòng).

Khoá những điều dễ vỡ:
  * slotIndex phải đúng thứ tự DOM 5 dòng — bảng không có tiêu đề nhánh nên FE chỉ còn thứ tự để khớp;
  * hợp đồng + chứng từ thanh toán CÙNG dòng 3 phải dùng CHUNG slotKey (engine gom rồi bơm một lượt);
  * MỘT TỆP chỉ vào MỘT dòng — số lượt đính không được vượt số tệp;
  * giấy tờ không có dòng riêng phải xuống "Giấy tờ khác", không im lặng bỏ tệp.
"""

from app.pipelines.dk_giay_cn_thua_dat_dien_tich_tang_them.attach import planner
from app.procedures.registry import get_attach_pipeline, public_list

_KEY = "dang-ky-cap-gcn-dien-tich-tang-them-nhan-chuyen-quyen-mot-phan-thua"

# Đúng 5 tệp của hồ sơ mẫu trong ảnh ánh xạ.
_HO_SO_MAU = [
    ("Don_to_khai_1788492452.pdf", "don_bien_dong"),
    ("GCN_1788492481.pdf", "gcn"),
    ("Hop_dong_1788492512.pdf", "giay_to_chuyen_quyen"),
    ("Hoa_don_1788492519.pdf", "chung_tu_thanh_toan"),
    ("uy_quyen_1788492529.pdf", "van_ban_dai_dien"),
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


def test_ho_so_mau_vao_dung_bon_dong():
    attachments, warnings, _ = _plan(_HO_SO_MAU)
    by_file = _by_file(attachments)

    assert by_file["Don_to_khai_1788492452.pdf"]["slotIndex"] == 0
    assert by_file["GCN_1788492481.pdf"]["slotIndex"] == 1
    assert by_file["Hop_dong_1788492512.pdf"]["slotIndex"] == 2
    assert by_file["Hoa_don_1788492519.pdf"]["slotIndex"] == 2
    assert by_file["uy_quyen_1788492529.pdf"]["slotIndex"] == 4

    # Mọi tệp đều là fixed-slot và đều phải tích checkbox dòng.
    for item in attachments:
        assert item["target"] == "fixed-slot"
        assert item["tickRow"] is True
        assert item["needsAddComponent"] is False

    # Dòng 4 "Mảnh trích đo" không có tệp → phải nhắc, không im lặng.
    assert any("Mảnh trích đo" in w for w in warnings)


def test_hai_tep_cung_dong_dung_chung_slot_key():
    """Engine gom item theo slotKey rồi bơm cả loạt vào một ô. Khác slotKey thì tệp thứ hai sẽ thấy ô
    đã bị dùng và báo lỗi."""
    attachments, _, _ = _plan(_HO_SO_MAU)
    by_file = _by_file(attachments)
    assert (
        by_file["Hop_dong_1788492512.pdf"]["slotKey"]
        == by_file["Hoa_don_1788492519.pdf"]["slotKey"]
        == "lc_115694_row_2"
    )
    # Hai dòng khác nhau thì slotKey phải khác.
    assert by_file["Don_to_khai_1788492452.pdf"]["slotKey"] != by_file["GCN_1788492481.pdf"]["slotKey"]


def test_moi_tep_chi_vao_dung_mot_dong():
    attachments, _, _ = _plan(_HO_SO_MAU)
    assert len(attachments) == len(_HO_SO_MAU)
    assert len({item["fileIndex"] for item in attachments}) == len(_HO_SO_MAU)


def test_giay_to_khong_co_dong_rieng_xuong_giay_to_khac():
    attachments, _, _ = _plan([
        ("TK_LPTB.pdf", "to_khai_thue"),
        ("CCCD_hai_vo_chong.pdf", "giay_to_nhan_than"),
    ])
    by_file = _by_file(attachments)

    for name in ("TK_LPTB.pdf", "CCCD_hai_vo_chong.pdf"):
        assert by_file[name]["target"] == "new"
        assert by_file[name]["needsAddComponent"] is True
        # Cổng iGate: bấm "Chọn tệp tin" mở hộp thoại file của OS → FE chỉ được gán thẳng.
        assert by_file[name]["noChooserClick"] is True
        assert "slotIndex" not in by_file[name]
    assert by_file["TK_LPTB.pdf"]["documentName"] == "Tờ khai thuế, lệ phí trước bạ"


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
        ("TK_LPTB.pdf", "to_khai_thue"),
        ("TK_SDDPNN.pdf", "to_khai_thue"),
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


def test_canh_bao_giay_to_quet_gop_vao_file_chinh():
    """Hồ sơ mẫu: tờ khai thuế nằm chung file với Đơn, CCCD nằm chung file với Giấy ủy quyền."""
    _, warnings, _ = _plan(_HO_SO_MAU)
    assert any("tờ khai lệ phí trước bạ" in w for w in warnings)
    assert any("CCCD của người sử dụng đất" in w for w in warnings)


def test_khong_canh_bao_quet_gop_khi_da_co_tep_rieng():
    _, warnings, _ = _plan(_HO_SO_MAU + [
        ("TK_LPTB.pdf", "to_khai_thue"),
        ("CCCD.pdf", "giay_to_nhan_than"),
    ])
    assert not any("thường quét gộp" in w for w in warnings)


def test_khong_co_tep_nao_thi_bao_ro():
    attachments, warnings, _ = planner.build_plan_items([], {})
    assert attachments == []
    assert any("Không có tài liệu nào" in w for w in warnings)


def test_slot_index_phu_kin_bang_nam_dong():
    """Mọi dòng khai trong _ROWS phải có ít nhất một docType trỏ tới, và không trỏ ra ngoài bảng."""
    routed = {slot for slot, _ in planner._ROUTES.values()}
    assert routed == set(planner._ROWS)
    assert max(routed) == 4
