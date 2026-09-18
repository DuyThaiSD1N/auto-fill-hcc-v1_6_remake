"""Quầy Lai Châu: đọc TRỌN câu rồi mới sang câu sau.

Mặc định mỗi lượt mới cắt ngang câu đang đọc — đúng cho quầy nói tiếng phổ thông, vì bot
không được đọc hướng dẫn đã hết hiệu lực. Nhưng ở Lai Châu công dân nghe qua lời dịch tiếng
Mông: mất nửa câu là mất hẳn ý, nghe lại cũng không có.

Chính sách đặt Ở BACKEND chứ không ở extension: thêm tỉnh chỉ cần deploy BE, không phải phát
hành lại bản extension cho mọi máy quầy.
"""
import pytest

from app.channels.handfree.voice import router


@pytest.mark.parametrize("tinh", [
    "Lai Châu",
    "Tỉnh Lai Châu",
    "lai chau",
    "TỈNH LAI CHÂU",      # danh mục tỉnh/xã có bản in hoa
])
def test_tai_khoan_lai_chau_thi_doc_het_cau(tinh):
    assert router._finish_sentence_before_next({"tinh": tinh}) is True


@pytest.mark.parametrize("tinh", ["Bắc Ninh", "Đà Nẵng", "Lào Cai", "", None])
def test_tinh_khac_van_cat_ngang_nhu_cu(tinh):
    """Không được bật đại trà: cắt ngang là hành vi ĐÚNG ở quầy nói tiếng phổ thông."""
    assert router._finish_sentence_before_next({"tinh": tinh}) is False


def test_thieu_han_truong_tinh_thi_khong_bat():
    """Tài khoản cũ chưa có trường tinh → mặc định an toàn, giữ nguyên hành vi cũ."""
    assert router._finish_sentence_before_next({}) is False


def test_lao_cai_khong_bi_khop_nham():
    """Bẫy khớp lỏng: 'lai chau' không được dính vào tên tỉnh khác. Chốt lại vì danh sách
    tỉnh sẽ dài thêm và cách khớp hiện tại là kiểm tra chuỗi con."""
    for tinh in ["Lào Cai", "Châu Đốc", "Lai Vung", "Chợ Lách"]:
        assert router._finish_sentence_before_next({"tinh": tinh}) is False, tinh
