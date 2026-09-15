"""Đính kèm [BN] Tách/hợp thửa đất (1.011507): khớp thành phần theo MÃ TP-H05 (in trong dòng
tiêu đề mỗi hàng trên cổng), KHÔNG dùng mã KQ (mã kết quả — không hiện ở bảng đính kèm)."""

from app.pipelines.tach_hop_thua_dat_bac_ninh.attach import catalog
from app.pipelines.tach_hop_thua_dat_bac_ninh.attach.planner import _build_item

_FILE = {"name": "x.pdf"}


def _item(label: str) -> dict:
    return _build_item(_FILE, 0, label, "Tài liệu")


def test_component_names_are_tp_h05_codes_not_kq():
    """FE fill-bacninh khớp componentName = substring text hàng (chứa mã TP-H05), KHÔNG có mã KQ."""
    codes = [code for _, code, _ in catalog.CATALOG if code]
    assert codes, "catalog phải có mã thành phần"
    assert all(code.startswith("TP-H05.") for code in codes), codes
    assert not any(code.startswith("KQ") for code in codes), "KQ là mã kết quả, không khớp bảng đính kèm"


def test_four_slots_map_to_correct_tp_h05_rows():
    assert catalog.resolve("don_tach_thua") == ("existing", "TP-H05.000032")   # Mẫu 22 - Đơn
    assert catalog.resolve("ban_ve_tach_thua") == ("existing", "TP-H05.000033")  # Mẫu 22a - Bản vẽ
    assert catalog.resolve("gcn") == ("existing", "TP-H05.000040")             # Giấy chứng nhận đã cấp
    assert catalog.resolve("van_ban_co_quan") == ("existing", "TP-H05.000047") # Văn bản cơ quan


def test_don_gcn_banve_route_to_existing_slots():
    for label, code in (
        ("don_tach_thua", "TP-H05.000032"),
        ("ban_ve_tach_thua", "TP-H05.000033"),
        ("gcn", "TP-H05.000040"),
    ):
        item = _item(label)
        assert item["target"] == "existing", label
        assert item["componentName"] == code, label
        assert item["slotKey"] == "banChinh", label


def test_cccd_and_other_go_supplementary():
    """CCCD/giấy tờ khác không có ô riêng → ô 'File đính kèm khác' (supplementary)."""
    for label in ("cccd", "khac"):
        item = _item(label)
        assert item["target"] == "supplementary", label
        assert item["componentName"] == "", label
