"""Classify giấy báo tử (khai tử): nhận theo cụm đầy đủ/nhãn tử vong, KHÔNG dính "thông báo từ chối"."""
from app.upload_session.classify import classify_text, route_to_slot

_KHAI_TU_DOCS = [
    {"key": "cccd", "sides": 2},
    {"key": "bao_tu", "sides": 1},
    {"key": "to_khai", "sides": 1, "optional": True},
]


def test_nhan_giay_bao_tu_va_chung_tu():
    assert classify_text("GIẤY BÁO TỬ Số 12/GBT UBND xã")["doc_type"] == "bao_tu"
    assert classify_text("GIẤY CHỨNG TỬ của ông Nguyễn Văn A")["doc_type"] == "bao_tu"
    assert classify_text("Đã chết vào lúc 06 giờ 38 phút ngày 05/06/2026")["doc_type"] == "bao_tu"


def test_khong_dinh_thong_bao_tu_choi():
    # "thông báo từ chối" fold dấu chứa chuỗi "bao tu" — không được nhận nhầm.
    assert classify_text("Thông báo từ chối tiếp nhận hồ sơ")["doc_type"] is None


def test_to_khai_khai_tu_thang_giay_bao_tu():
    # Tờ khai khai tử có nhắc "kèm giấy báo tử" → vẫn là tờ khai (xét trước).
    assert classify_text("TỜ KHAI ĐĂNG KÝ KHAI TỬ kèm theo giấy báo tử")["doc_type"] == "to_khai"


def test_route_bao_tu_vao_slot():
    info = classify_text("GIẤY BÁO TỬ Số 12/GBT")
    key, _side, _note = route_to_slot(info, _KHAI_TU_DOCS, [], None)
    assert key == "bao_tu"
    # Slot đã đầy → không nhận thêm (thủ tục khai tử không có slot "khác").
    key2, _s, note2 = route_to_slot(info, _KHAI_TU_DOCS, [{"doc_key": "bao_tu"}], None)
    assert key2 is None and note2
