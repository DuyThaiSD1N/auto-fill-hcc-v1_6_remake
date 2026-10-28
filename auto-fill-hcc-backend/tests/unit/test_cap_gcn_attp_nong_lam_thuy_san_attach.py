"""Unit test planner đính kèm "Cấp GCN ATTP nông, lâm, thủy sản" (engine attp-row).

3 hành vi theo yêu cầu tester (2026-09-04):
- Giấy tờ ngoài 2 loại đã định nghĩa (other) → ĐÍNH CHUNG vào hàng Tờ khai (Đơn Phụ lục I), không bỏ qua.
- GIỮ NGUYÊN tên file gốc (documentName = fileName) cho mọi item.
- 2 mặt CCCD (≥2 file) → gộp 1 PDF qua sourceFileIndexes.
"""

from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.attach import planner

_DON_ROW = planner._ROWS["don_de_nghi"]["componentName"]
_TM_ROW = planner._ROWS["thuyet_minh"]["componentName"]


def _by_file(files, ocr):
    attachments, warnings, classified = planner.build_plan_items(files, ocr)
    return attachments, warnings, {c["fileName"]: c for c in classified}, {a["fileName"]: a for a in attachments}


def test_don_va_thuyet_minh_dat_ten_theo_loai():
    files = [
        {"name": "scan-don.pdf", "type": "application/pdf"},
        {"name": "scan-thuyet-minh.pdf", "type": "application/pdf"},
    ]
    ocr = [
        {"name": "scan-don.pdf",
         "text": "ĐƠN ĐỀ NGHỊ CẤP GIẤY CHỨNG NHẬN CƠ SỞ ĐỦ ĐIỀU KIỆN AN TOÀN THỰC PHẨM Tên cơ sở sản xuất mặt hàng sản xuất"},
        {"name": "scan-thuyet-minh.pdf",
         "text": "BẢN THUYẾT MINH điều kiện bảo đảm an toàn thực phẩm THÔNG TIN CHUNG MÔ TẢ VỀ SẢN PHẨM"},
    ]
    attachments, warnings, _, by_name = _by_file(files, ocr)
    assert warnings == []
    # Giữ NGUYÊN tên file gốc, KHÔNG đổi thành nhãn "Đơn... (Phụ lục I)".
    assert by_name["scan-don.pdf"]["documentName"] == planner._ROWS["don_de_nghi"]["documentName"]
    assert by_name["scan-don.pdf"]["componentName"] == _DON_ROW
    assert by_name["scan-thuyet-minh.pdf"]["documentName"] == planner._ROWS["thuyet_minh"]["documentName"]
    assert by_name["scan-thuyet-minh.pdf"]["componentName"] == _TM_ROW


def test_other_dinh_chung_vao_hang_to_khai():
    files = [
        {"name": "scan-don.pdf", "type": "application/pdf"},
        {"name": "so-yeu-ly-lich.pdf", "type": "application/pdf"},
    ]
    ocr = [
        {"name": "scan-don.pdf",
         "text": "ĐƠN ĐỀ NGHỊ CẤP GIẤY CHỨNG NHẬN CƠ SỞ ĐỦ ĐIỀU KIỆN AN TOÀN THỰC PHẨM tên cơ sở mặt hàng sản xuất"},
        {"name": "so-yeu-ly-lich.pdf", "text": "SƠ YẾU LÝ LỊCH TỰ THUẬT thông tin bản thân quan hệ gia đình"},
    ]
    attachments, warnings, classified, by_name = _by_file(files, ocr)
    assert warnings == []
    # CV không thuộc 2 loại → vẫn ĐÍNH vào hàng Đơn (không bị bỏ như trước).
    cv = by_name["so-yeu-ly-lich.pdf"]
    assert cv["componentName"] == _DON_ROW
    assert cv["target"] == "attp-row"
    assert cv["documentName"] == "so-yeu-ly-lich.pdf"    # giữ tên gốc
    assert cv["detectedType"] == "other"
    assert classified["so-yeu-ly-lich.pdf"]["routedTo"] == "don_de_nghi"


def test_hai_mat_cccd_gop_thanh_mot():
    files = [
        {"name": "cccd-truoc.jpg", "type": "image/jpeg"},
        {"name": "cccd-sau.jpg", "type": "image/jpeg"},
    ]
    ocr = [
        {"name": "cccd-truoc.jpg", "text": "CĂN CƯỚC CÔNG DÂN Số 048079005662 Họ và tên PHẠM VĂN TUẤN"},
        {"name": "cccd-sau.jpg", "text": "CĂN CƯỚC CÔNG DÂN Cục Cảnh sát QLHC về TTXH nơi thường trú"},
    ]
    attachments, warnings, _, _ = _by_file(files, ocr)
    assert warnings == []
    cccd = [a for a in attachments if a["detectedType"] == "cccd"]
    # 2 mặt → GỘP 1 item duy nhất với sourceFileIndexes.
    assert len(cccd) == 1
    assert cccd[0]["sourceFileIndexes"] == [0, 1]
    assert cccd[0]["target"] == "add-document-dialog"
    assert cccd[0]["documentName"] == "Căn cước công dân"   # tệp gộp 2 mặt mang tên theo loại


def test_mot_cccd_khong_gop():
    files = [{"name": "cccd.pdf", "type": "application/pdf"}]
    ocr = [{"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN Số 048079005662 nơi thường trú"}]
    attachments, warnings, _, _ = _by_file(files, ocr)
    cccd = [a for a in attachments if a["detectedType"] == "cccd"]
    assert len(cccd) == 1
    assert "sourceFileIndexes" not in cccd[0]
    assert cccd[0]["documentName"] == "Căn cước công dân"


_GCN_ATTP_CU = (
    "GIẤY CHỨNG NHẬN CƠ SỞ ĐỦ ĐIỀU KIỆN AN TOÀN THỰC PHẨM Tên cơ sở ... Giấy chứng nhận đăng ký hộ kinh doanh số ..."
    " GIẤY KHÁM SỨC KHỎE Họ và tên NGUYỄN VĂN A"
)


def test_llm_quyet_loai_keyword_khong_de():
    # Keyword khớp "giấy chứng nhận đăng ký hộ kinh doanh" nhưng LLM đọc ra giấy khác → theo LLM, vẫn đính.
    files = [{"name": "gcn-va-ksk.pdf", "type": "application/pdf"}]
    ocr = [{"name": "gcn-va-ksk.pdf", "text": _GCN_ATTP_CU}]
    attachments, warnings, classified = planner.build_plan_items(files, ocr, {0: "other"})
    assert [a["componentName"] for a in attachments] == [_DON_ROW]
    assert classified[0]["source"] == "llm" and not classified[0].get("skipped")
    assert warnings == []


def test_gcn_dkkd_khong_bi_bo_ma_dinh_chung_dong_don():
    # Tệp scan gộp GCN ĐKKD + giấy khám sức khỏe: bỏ cả tệp là mất giấy → đính dòng Đơn, giữ tên gốc.
    files = [{"name": "gcn-va-ksk.pdf", "type": "application/pdf"}]
    ocr = [{"name": "gcn-va-ksk.pdf", "text": "GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH Mã số ... GIẤY KHÁM SỨC KHỎE"}]
    for llm in ({0: "gcn_dkkd"}, {}):  # LLM trả gcn_dkkd, hoặc LLM lỗi → keyword dự phòng
        attachments, warnings, classified = planner.build_plan_items(files, ocr, llm)
        assert [a["componentName"] for a in attachments] == [_DON_ROW]
        assert attachments[0]["documentName"] == "gcn-va-ksk.pdf" and attachments[0]["detectedType"] == "gcn_dkkd"
        assert classified[0]["routedTo"] == "don_de_nghi" and warnings == []


def test_prompt_gcn_dkkd_chi_khi_chinh_la_giay_dkkd():
    from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.attach.prompt import SYSTEM_PROMPT

    assert "CHÍNH LÀ tờ Giấy chứng nhận đăng ký" in SYSTEM_PROMPT
    assert "chỉ NHẮC số đăng ký kinh doanh" in SYSTEM_PROMPT
    assert "xếp\n   loại theo giấy ở TRANG ĐẦU" in SYSTEM_PROMPT
