"""Unit test attach planner "Cấp đổi GCN" (Đà Nẵng).

Trọng tâm: (1) file KHÔNG khớp dòng nào (CCCD/QĐ giải thể/không xác định) → MẶC ĐỊNH đưa vào dòng "Đơn
đăng ký biến động" để không bỏ sót file; (2) documentName để RỖNG (giữ tên file gốc + dedup theo fileName)."""

from app.pipelines.cap_doi_gcn_da_nang.attach import planner as P


def _plan(files_texts_llm):
    files = [{"name": n} for n, _, _ in files_texts_llm]
    ocr = [{"name": n, "text": t} for n, t, _ in files_texts_llm]
    llm = {i: lt for i, (_, _, lt) in enumerate(files_texts_llm) if lt}
    return P.build_plan_items(files, ocr, llm)


def test_moi_file_deu_duoc_dinh_kem_khong_bo_sot():
    items, warnings, classified = _plan([
        ("Đơn 1.pdf", "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI", "don_m18"),
        ("GCN CT.pdf", "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT", "ban_goc_gcn"),
        ("cccd.pdf", "CĂN CƯỚC CÔNG DÂN", "cccd"),
        ("quyetdinh.pdf", "QUYẾT ĐỊNH giải thể công ty", "other"),
    ])
    # 4 file vào → 4 item (KHÔNG bỏ sót file nào)
    assert len(items) == 4
    assert not warnings
    # CCCD + QĐ (không khớp dòng) → dồn vào dòng Đơn đăng ký
    by_name = {it["fileName"]: it for it in items}
    assert by_name["cccd.pdf"]["componentName"] == "Đơn đăng ký biến động đất đai"
    assert by_name["cccd.pdf"]["detectedType"] == "don_m18"
    assert by_name["cccd.pdf"]["fallback"] is True
    assert by_name["quyetdinh.pdf"]["componentName"] == "Đơn đăng ký biến động đất đai"
    # file khớp dòng riêng thì giữ đúng dòng
    assert by_name["GCN CT.pdf"]["componentName"] == "Bản gốc Giấy chứng nhận đã cấp"
    assert by_name["GCN CT.pdf"]["fallback"] is False


def test_document_name_rong_giu_ten_goc():
    items, _, _ = _plan([("Đơn 1.pdf", "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI", "don_m18")])
    assert items[0]["documentName"] == ""  # FE giữ tên file gốc + dedup theo fileName
    assert items[0]["rowDocumentName"]  # tên thành phần vẫn giữ để tham chiếu


def test_nhieu_file_cung_dong_don():
    items, _, _ = _plan([
        ("Đơn 1.pdf", "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI", "don_m18"),
        ("Đơn 2.pdf", "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI", "don_m18"),
        ("cccd.pdf", "CĂN CƯỚC CÔNG DÂN", "cccd"),
    ])
    don_items = [it for it in items if it["componentName"] == "Đơn đăng ký biến động đất đai"]
    assert len(don_items) == 3  # 2 đơn + 1 cccd fallback, tất cả vào dòng đơn
    assert all(it["documentName"] == "" for it in don_items)  # dedup theo fileName (unique) → không bị coi trùng
