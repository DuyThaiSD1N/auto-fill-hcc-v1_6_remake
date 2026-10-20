# -*- coding: utf-8 -*-
"""CHẾ ĐỘ KHÔNG CẮT: mỗi trang gửi một yêu cầu gồm ảnh toàn trang + các dải chữ phóng to.

Luồng cho mỗi trang (giống web khi tắt "Tự cắt 4 phần"):
  1. tien_xu_ly.chuan_bi_trang: tự xoay theo chiều chữ, chỉnh nghiêng, cân bằng sáng, tìm dòng chữ
  2. chuan_bi_anh.page_shots: ảnh toàn trang + tối đa (max_images - 1) dải phóng to theo dòng chữ (zoom "auto")
  3. chuan_bi_anh.build_content: [chú thích, ảnh]... + lời kết "Đây là trang i trong tổng số n trang..."
  4. gửi model (trần max_tokens), dừng sớm nếu model lặp vô hạn
  5. goi_qwen.clean_output + trim_loop: gỡ khối ```markdown, bỏ phần lặp
Các trang được đọc song song (tối đa cfg["song_song"] trang một lúc); kết quả nối theo đúng thứ tự trang bằng "---".

Nhanh hơn chế độ cắt với tệp nhiều trang; trên 54 tệp viết tay đã chấm, chính xác hơn trung bình 2,1 điểm.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

from . import chuan_bi_anh as cb
from . import goi_qwen as gq
from . import tien_xu_ly as tx
from .chung import NOI_TRANG, KetQua, MayChuQwen, TongHop, bao_su_kien
from .prompt import ghi_chu_nguoi_dung, loi_ket_trang


def doc_mot_trang(may: MayChuQwen, img: Image.Image, i: int, so_trang: int, ten_tep: str, cfg: dict,
                  ghi_chu: str = "", xoay_tay: int = 0, bao=None) -> tuple[str, dict, dict]:
    """Đọc cả một trang. Trả (Markdown của trang đã làm sạch, usage, thông tin trang)."""
    prep = cfg["prep"]
    label = f"Trang {i + 1}/{so_trang}"
    page, info = tx.chuan_bi_trang(img, prep, xoay_tay)
    if info.get("steps"):
        bao_su_kien(bao, {"type": "status", "trang": i, "text": f"{label}: đã {', '.join(info['steps'])}."})
    shots = cb.page_shots(page, label, cfg["zoom"], may.spec, prep, max_images=may.max_images, text=info.get("text"))
    req = cb.build_content(shots, loi_ket_trang(i, so_trang, ten_tep) + ghi_chu_nguoi_dung(ghi_chu), cfg["image_format"])
    bao_su_kien(bao, {"type": "status", "trang": i,
                      "text": f"{label}: gửi {req.image_count} ảnh (khoảng {req.visual_tokens} token hình) tới {may.label}"})
    text, usage = may.doc(req.content, bao=(lambda ev: bao_su_kien(bao, {**ev, "trang": i})) if bao else None)
    thong_tin = {"trang": i + 1, "cach_doc": "cả trang", "buoc": info.get("steps", []), "chieu_chu": info.get("orient"),
                 "so_anh": req.image_count, "token_hinh_uoc_tinh": req.visual_tokens}
    return gq.trim_loop(gq.clean_output(text)), usage, thong_tin


def doc_khong_tach(trang: list[Image.Image], cfg: dict, ten_tep: str = "tep", ghi_chu: str = "",
                   xoay_tay: list[int] | None = None, bao=None) -> KetQua:
    """Đọc mọi trang của một tệp ở chế độ không cắt.

    trang: các trang ảnh (doc_tep.load_document); cfg: cau_hinh.tao_cau_hinh(); ten_tep: tên hiện trong lời kết;
    ghi_chu: ngữ cảnh cho model (không bắt buộc); xoay_tay: số độ xoay thêm cho từng trang (không bắt buộc);
    bao(su_kien): nhận sự kiện {"type": "status" | "text" | "usage", "trang": i, ...} trong lúc đọc
    (được gọi từ nhiều luồng cùng lúc)."""
    started = time.time()
    n = len(trang)
    kq = KetQua(so_trang=n, che_do="khong_tach")
    tong = TongHop(kq)
    may = MayChuQwen(cfg)
    xoay_tay = xoay_tay or [0] * n
    workers = max(1, min(int(cfg.get("song_song", 4) or 1), n))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(doc_mot_trang, may, trang[i], i, n, ten_tep, cfg, ghi_chu, xoay_tay[i], bao) for i in range(n)]
        try:
            res = [f.result() for f in futs]            # lỗi ở một trang thì dừng cả lần đọc, như web
        except BaseException:
            for f in futs:
                f.cancel()
            raise
    parts = []
    for i, (text, usage, info) in enumerate(res):
        tong.them(usage, f"Trang {i + 1}" if n > 1 else "")
        parts.append(text)
        kq.trang.append(info)
    kq.markdown = NOI_TRANG.join(p for p in parts if p).strip()
    if not kq.markdown:
        raise RuntimeError("Model không trả về nội dung nào. Thử đọc lại, hoặc kiểm tra model trên máy chủ có đọc được ảnh không.")
    kq.markdown += "\n"
    kq.giay = round(time.time() - started, 1)
    return kq
