# -*- coding: utf-8 -*-
"""Đọc giấy tờ tiếng Việt (OCR) bằng model Qwen trên máy chủ chuẩn OpenAI, tách từ web Bàn đọc giấy tờ.

Dùng nhanh:
    from app.services.qwen_doc_giay import doc_giay_to, tao_cau_hinh
    cfg = tao_cau_hinh(base_url="http://<may-chu>:<cong>/v1", model="qwen3.6-35b")
    kq = doc_giay_to("giay_khai_sinh.pdf", tach=False, cfg=cfg)   # tach=True: tự cắt 4 phần
    print(kq.markdown, kq.giay, kq.input_tokens, kq.output_tokens)

Chỉ tự xoay ảnh theo chiều chữ (dùng riêng, không gọi model):
    from app.services.qwen_doc_giay import tu_xoay
    anh_thang, ket_qua = tu_xoay(anh)          # ket_qua["deg"]: 0/90/180/270, ket_qua["conf"]: cao/vừa/thấp

Các tệp:
    doc_tep.py          đọc PDF / ảnh / ZIP thành các trang ảnh
    tien_xu_ly.py       tiền xử lý: tự xoay theo chiều chữ, chỉnh nghiêng, cân bằng sáng, tìm dòng chữ, làm nét...
    chuan_bi_anh.py     ảnh toàn trang + dải phóng to, mã hóa ảnh, đóng gói nội dung yêu cầu
    prompt.py           prompt hệ thống (prompt_he_thong.md) và các lời kết từng trang / từng phần
    goi_qwen.py         gọi /v1/chat/completions (stream), chặn lặp vô hạn, làm sạch kết quả
    doc_khong_tach.py   CHẾ ĐỘ KHÔNG CẮT
    doc_tach_4_phan.py  CHẾ ĐỘ TỰ CẮT 4 PHẦN
    chung.py            phần dùng chung: gọi máy chủ, kết quả, cộng token
    cau_hinh.py         cấu hình mặc định (đúng cấu hình web 1 đang chạy)
"""
from __future__ import annotations

from pathlib import Path

from .cau_hinh import CAU_HINH_MAC_DINH, tao_cau_hinh
from .chung import KetQua, MayChuQwen
from .doc_khong_tach import doc_khong_tach
from .doc_tach_4_phan import doc_tach_4_phan
from .doc_tep import load_document
from .tien_xu_ly import chuan_bi_trang, detect_orientation, tu_xoay

__all__ = ["doc_giay_to", "doc_trang", "doc_khong_tach", "doc_tach_4_phan", "tao_cau_hinh", "CAU_HINH_MAC_DINH",
           "KetQua", "MayChuQwen", "load_document", "chuan_bi_trang", "detect_orientation", "tu_xoay"]


def doc_trang(nguon, ten_tep: str | None = None) -> tuple[list, str]:
    """Đường dẫn tệp hoặc bytes -> (danh sách trang ảnh, tên tệp)."""
    if isinstance(nguon, (bytes, bytearray)):
        return load_document(bytes(nguon), ten_tep or "tep"), ten_tep or "tep"
    p = Path(nguon)
    return load_document(p.read_bytes(), p.name), ten_tep or p.name


def doc_giay_to(nguon, tach: bool = True, cfg: dict | None = None, ten_tep: str | None = None, ghi_chu: str = "",
                xoay_tay: list[int] | None = None, bao=None) -> KetQua:
    """Đọc một tệp giấy tờ (đường dẫn hoặc bytes) thành Markdown.

    tach=True: tự cắt 4 phần (doc_tach_4_phan); tach=False: không cắt (doc_khong_tach).
    Web 1 hiện để mặc định bật tự cắt 4 phần."""
    cfg = cfg or tao_cau_hinh()
    trang, ten = doc_trang(nguon, ten_tep)
    if not trang:
        raise ValueError("Không tìm thấy trang nào trong tệp.")
    doc = doc_tach_4_phan if tach else doc_khong_tach
    return doc(trang, cfg, ten_tep=ten, ghi_chu=ghi_chu, xoay_tay=xoay_tay, bao=bao)
