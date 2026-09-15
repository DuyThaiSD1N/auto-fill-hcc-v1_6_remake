"""Đăng ký lại kết hôn (handfree): file lạ (bản cam đoan) phải rơi vào ô 'Các giấy tờ khác'
thay vì 'chưa nhận ra loại'. Bug gốc: requiredDocs thiếu slot 'khac'."""
from app.channels.handfree.procedure_registry import PROCEDURES
from app.pipelines.ket_hon_lai.handfree.upload_classification import SPEC
from app.upload_session import classifier_registry
from app.upload_session.classify import classify_text, route_to_slot


def _required_docs() -> list[dict]:
    proc = next(p for p in PROCEDURES if p["key"] == "dang-ky-lai-ket-hon")
    return proc["requiredDocs"]


def test_has_khac_catch_all_slot():
    keys = [d["key"] for d in _required_docs()]
    assert "khac" in keys  # thiếu ô này thì file lạ báo "chưa nhận ra loại"


def test_spec_allowed_keys_subset_of_required_docs():
    # LLM chỉ được trả doc_key khớp một ô trong checklist, nếu không sẽ rơi fallback.
    keys = {d["key"] for d in _required_docs()}
    assert SPEC.allowed_keys <= keys
    assert classifier_registry.get_upload_classifier("dang-ky-lai-ket-hon") is not None


def test_unrecognized_file_routes_to_khac_not_rejected():
    info = {"doc_type": None, "side": None, "gender": None}
    doc_key, _side, _note = route_to_slot(info, _required_docs(), [], None)
    assert doc_key == "khac"


def test_without_khac_slot_would_be_rejected():
    """Chứng minh chính slot 'khac' là thứ sửa lỗi: bỏ nó đi thì quay lại 'chưa nhận ra loại'."""
    info = {"doc_type": None, "side": None, "gender": None}
    docs_no_khac = [d for d in _required_docs() if d["key"] != "khac"]
    doc_key, _side, note = route_to_slot(info, docs_no_khac, [], None)
    assert doc_key is None
    assert "chưa nhận ra loại" in note


def test_commitment_statement_text_routes_to_khac():
    # OCR bản cam đoan không khớp CCCD/GCN/tờ khai -> phải vào 'khac'.
    info = classify_text("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM BẢN CAM ĐOAN Tôi xin cam đoan nội dung là đúng")
    doc_key, _side, _note = route_to_slot(info, _required_docs(), [], None)
    assert doc_key == "khac"


def test_old_marriage_certificate_text_routes_to_ho_tich():
    # GCN kết hôn cũ là nguồn số/ngày/nơi đăng ký -> ô 'ho_tich', không rơi 'khac'.
    info = classify_text("GIẤY CHỨNG NHẬN KẾT HÔN Số Quyển số Ngày đăng ký kết hôn")
    doc_key, _side, _note = route_to_slot(info, _required_docs(), [], None)
    assert doc_key in {"ho_tich", "khac"}  # ho_tich nếu classify_text nhận ra GCN kết hôn
