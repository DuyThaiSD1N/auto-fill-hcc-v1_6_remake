"""Thủ tục đăng ký lại khai sinh (lõi copy từ auto-fill khai_sinh_dang_ky_lai).

Kiểm registry đăng ký đúng 3 chỗ (entry + 2 map) và classify dồn CCCD/giấy khai sinh cũ vào
ô "Giấy tờ khác" (chỉ 2 ô: to_khai + khac), theo yêu cầu "cái gì ngoài tờ khai cho vào hết".
"""

from app.pipelines.khai_sinh_dang_ky_lai import attach as ks_attach
from app.pipelines.khai_sinh_dang_ky_lai import process as ks_process
from app.channels.handfree.procedure_registry import get_attach_pipeline, get_pipeline, get_procedure
from app.upload_session.classify import classify_text, route_to_slot


def test_registry_khai_sinh_dang_ky_lai_entry():
    proc = get_procedure("khai-sinh-dang-ky-lai")
    assert proc is not None
    assert get_pipeline("khai-sinh-dang-ky-lai") is ks_process.run          # process map
    assert get_attach_pipeline("khai-sinh-dang-ky-lai") is ks_attach.plan   # attach map
    assert not proc.get("hiddenFromList")          # hiện trên card như các hộ tịch khác
    assert proc["needsAgencySelect"] is True
    assert proc["detect"]["urlIncludes"] == ["maThuTuc=1.004884"]
    assert proc["keKhaiUrl"].endswith("019d2bfd-6eac-7598-b88b-15f8a61b366a")
    docs = {r["key"]: r for r in proc["requiredDocs"]}
    assert set(docs) == {"to_khai", "khac"}         # ĐÚNG 2 ô theo yêu cầu FE
    assert docs["khac"].get("repeatable")           # catch-all nhận nhiều file


def _route(proc, text):
    info = classify_text(text)
    key, _side, _note = route_to_slot(info, proc["requiredDocs"], [], None)
    return info["doc_type"], key


def test_classify_dong_moi_giay_to_ngoai_to_khai_vao_khac():
    """Tờ khai → ô to_khai; CCCD cha/mẹ + giấy khai sinh cũ + GCN + linh tinh → ô "khac"."""
    proc = get_procedure("khai-sinh-dang-ky-lai")
    assert _route(proc, "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH") == ("to_khai", "to_khai")
    # CCCD KHÔNG có ô riêng ở thủ tục này → phải rơi vào "khac" (guard nhánh cccd trong classify).
    assert _route(proc, "CĂN CƯỚC CÔNG DÂN Số/No.: 001099012345 Nam")[1] == "khac"
    # Giấy khai sinh cũ (doc_type ho_tich) không có ô ho_tich → "khac".
    assert _route(proc, "GIẤY KHAI SINH Họ và tên: Nguyễn Văn A")[1] == "khac"
    assert _route(proc, "GIẤY CHỨNG NHẬN KẾT HÔN Số: 40/2026")[1] == "khac"
    assert _route(proc, "hóa đơn tiền điện tháng 8")[1] == "khac"
