"""Unit test "[Quảng Ninh] Tính hoặc tính lại tiền sử dụng đất (khoản 2 Điều 12 NĐ 50/2026/NĐ-CP)".

Form có 2 dòng thành phần SẴN: Đơn đề nghị → dòng 1, Giấy tờ kèm theo đơn → dòng 2. Bộ giấy tờ kèm theo
hay quét gộp một PDF → đính nguyên vào dòng 2, planner đề xuất ghi chú trích yếu.
"""

from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_quang_ninh.attach import planner
from app.procedures import ke_khai_links
from app.procedures.registry import get_attach_pipeline, get_procedure

_KEY = "tinh-tien-su-dung-dat-nd-50-2026-quang-ninh"

_DON_TEXT = (
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n"
    "ĐƠN ĐỀ NGHỊ TÍNH LẠI TIỀN SỬ DỤNG ĐẤT\nKính gửi: Chi nhánh Văn phòng đăng ký đất đai\n"
    "1. Người nộp thuế: LÊ VĂN AN\n2. Thửa đất số: 12; tờ bản đồ số: 7\n"
    "4. Giấy tờ nộp kèm: Quyết định số 101/QĐ-UBND; giấy nộp tiền vào ngân sách nhà nước"
)
_KEM_THEO_TEXT = (
    "ỦY BAN NHÂN DÂN\nQUYẾT ĐỊNH số 101/QĐ-UBND về việc cho phép chuyển mục đích sử dụng đất "
    "diện tích 150,0 m2 từ đất trồng cây hàng năm sang đất ở\n"
    "GIẤY NỘP TIỀN VÀO NGÂN SÁCH NHÀ NƯỚC\nTHÔNG BÁO NỘP TIỀN SỬ DỤNG ĐẤT\n"
    "PHIẾU CHUYỂN THÔNG TIN ĐỊA CHÍNH\nTRÍCH LỤC BẢN ĐỒ ĐỊA CHÍNH thửa đất số 12"
)


def test_rows_are_named_new_components_don_first():
    """Cổng không có dòng đặt tên sẵn: mọi tệp là dòng mới có tên, Đơn đính trước dù tải lên sau."""
    files = [
        {"name": "Ho_so_kem_theo.pdf", "type": "application/pdf"},
        {"name": "Don.pdf", "type": "application/pdf"},
    ]
    attachments, warnings, classified = planner.build_plan_items(
        files, [], {0: "giay_to_kem_theo", 1: "don_de_nghi"}
    )
    assert [a["fileName"] for a in attachments] == ["Don.pdf", "Ho_so_kem_theo.pdf"]
    assert attachments[0]["componentName"] == "Đơn đề nghị tính lại tiền sử dụng đất"
    assert attachments[1]["componentName"].startswith("Giấy tờ kèm theo đơn (QĐ chuyển mục đích")
    assert all(a["target"] == "new" and a["needsAddComponent"] is True for a in attachments)
    assert all("componentIndex" not in a for a in attachments)
    assert all(a["loaiBan"] == "Bản chính" for a in attachments)
    assert all(c["source"] == "llm" for c in classified)
    assert warnings == []


def test_rule_fallback_and_note_suggestion():
    files = [
        {"name": "a.pdf", "type": "application/pdf"},
        {"name": "b.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": "a.pdf", "text": _DON_TEXT}, {"name": "b.pdf", "text": _KEM_THEO_TEXT}]
    attachments, warnings, classified = planner.build_plan_items(files, ocr, {})

    assert [a["detectedType"] for a in attachments] == ["don_de_nghi", "giay_to_kem_theo"]
    assert all(c["source"] == "rule" for c in classified)
    note = next(w for w in warnings if w.startswith("Ghi chú"))
    assert "thửa đất số 12, tờ bản đồ số 7" in note
    assert "chuyển mục đích 150,0 m² theo Quyết định số 101/QĐ-UBND" in note
    assert "giấy nộp tiền vào ngân sách nhà nước" in note
    assert "trích lục bản đồ địa chính" in note


def test_bundle_mentioning_don_is_not_don():
    """Tờ trình trong bộ kèm theo nhắc "đơn đề nghị" ở thân văn bản vẫn vào dòng 2."""
    text = "TỜ TRÌNH số 5/TTr về việc chuyển mục đích. " + "x " * 900 + "đơn đề nghị tính lại tiền sử dụng đất"
    assert planner._rule_doc_type(text) == "giay_to_kem_theo"


def test_missing_rows_warn_and_other_becomes_new_component():
    files = [
        {"name": "GIẤY ỦY QUYỀN.pdf", "type": "application/pdf"},
        {"name": "TAI_LIEU_LA.pdf", "type": "application/pdf"},
    ]
    attachments, warnings, _ = planner.build_plan_items(files, [], {0: "van_ban_dai_dien", 1: "other"})
    by = {a["fileName"]: a for a in attachments}
    assert by["GIẤY ỦY QUYỀN.pdf"]["needsAddComponent"] is True
    assert by["TAI_LIEU_LA.pdf"]["componentName"] == "TAI LIEU LA"
    assert any("Đơn đề nghị" in w for w in warnings)
    assert any("Giấy tờ kèm theo đơn" in w for w in warnings)


def test_registry_and_ke_khai_link_wired():
    proc = get_procedure(_KEY)
    assert proc is not None
    assert proc["mode"] == "attach"
    assert callable(get_attach_pipeline(_KEY))
    link = next(item for item in ke_khai_links.KE_KHAI_LINKS if item.get("key") == _KEY)
    assert link["code"] == "1.115148"
    assert link["provincePortalFlow"]["agency"] == "Đặc khu Cô Tô"
