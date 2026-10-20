# -*- coding: utf-8 -*-
"""CHẾ ĐỘ TỰ CẮT 4 PHẦN: mỗi trang dọc khổ A4/A5 được cắt ngang thành 4 dải, đọc riêng từng dải rồi ghép lại.

Luồng cho mỗi trang (giống web khi bật "Tự cắt 4 phần"); các trang đọc lần lượt, 4 phần của một trang đọc song song:
  1. tien_xu_ly.chuan_bi_trang: tự xoay theo chiều chữ, chỉnh nghiêng, cân bằng sáng, tìm dòng chữ
  2. split_bands: đặt 3 đường cắt giữa các dải hàng trắng thật sự (không có nét mực đen nào) gần mốc 1/4, 1/2, 3/4
     trang, ưu tiên khoảng trắng rộng giữa hai mục, nên không dòng chữ nào bị cắt đôi; bảng có đường kẻ dọc nên không
     bị cắt giữa bảng nếu còn chỗ khác. Trang không phải dọc (cao < 1,25 lần rộng: thẻ, giấy ngang) thì không cắt.
  3. plan_split + split_shots: phóng mỗi dải sao cho chữ nhỏ cao khoảng 1,2 x 36 px, không vượt giới hạn ảnh của model
  4. gửi song song từng dải (một ảnh mỗi yêu cầu) với lời kết loi_ket_phan, trần max_tokens_moi_phan (1.536) mỗi phần
  5. stitch_parts: làm sạch từng phần, bỏ tiêu đề TRANG lặp lại ở các phần sau, nối bảng bị cắt ngang thành một
     bảng, gom các đoạn "Ghi chú đọc tài liệu" về cuối trang
  Trang không cắt được: đọc cả trang như chế độ không cắt (ảnh toàn trang + dải phóng to).

Nhanh hơn chế độ không cắt với giấy 1 trang (3,0 so với 5,0 giây), chậm hơn với tệp nhiều trang và tốn thêm
khoảng 70% token đầu vào. Mỗi phần được đọc mà không thấy phần còn lại, nên nên xem lại chỗ nối giữa các phần.

Các hàm cắt và ghép trích nguyên văn từ tien_xu_ly.py và ocr_engine.py của web; doc_tach_4_phan ở cuối tệp là luồng
đọc của web (app.py: ocr_file, read_split) viết lại không cần Flask.
"""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from PIL import Image

from . import chuan_bi_anh as cb
from . import goi_qwen as gq
from . import tien_xu_ly as tx
from .chuan_bi_anh import Shot, fit_scale
from .chung import NOI_TRANG, KetQua, MayChuQwen, TongHop, bao_su_kien
from .goi_qwen import clean_output, trim_loop
from .prompt import ghi_chu_nguoi_dung, loi_ket_phan, loi_ket_trang
from .tien_xu_ly import _ink_mask, _resize_max, to_bgr


# ================================================================ cắt trang thành các dải ngang
# ------------------------------------------------------------------ chia trang A4 thành các dải ngang
SPLIT_MIN_RATIO = 1.25       # cao/rộng tối thiểu để coi là trang dọc kiểu A4, A5 (thẻ, ảnh ngang thì không chia)


def _ink_rows(img: Image.Image) -> tuple[np.ndarray, float, int]:
    """Số điểm mực tối trên từng hàng của ảnh thu nhỏ. Dùng kênh sáng nhất nên hoa văn màu và dấu đỏ không tính,
    còn chữ đen, đường kẻ bảng (kể cả đường dọc) đều tính."""
    small, s = _resize_max(to_bgr(img), 1400)
    mx = small.max(axis=2)
    m = cv2.bitwise_and(_ink_mask(small), (mx < 165).astype(np.uint8) * 255)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))    # bỏ chấm nhiễu lẻ
    prof = (m > 0).sum(axis=1).astype(np.float64)
    prof = np.convolve(prof, np.ones(3) / 3, mode="same")
    return prof, s, small.shape[1]


def split_bands(img: Image.Image, n: int = 4, window: float = 0.09) -> list | None:
    """Chia trang dọc thành n dải ngang từ trên xuống. Mỗi đường cắt đặt giữa một dải hàng trống thật sự (không có
    nét mực đen nào) gần mốc chia đều, ưu tiên dải trống rộng (thường là chỗ chuyển mục), nên không dòng chữ nào bị cắt
    đôi; bên trong bảng luôn có đường kẻ dọc nên không bị cắt giữa bảng nếu còn chỗ khác.
    Trả [(y0, y1), ...] theo pixel, hoặc None nếu không phải trang dọc."""
    W, H = img.size
    if H < W * SPLIT_MIN_RATIO or n < 2:
        return None
    prof, s, w_small = _ink_rows(img)
    blank = prof <= max(2.0, 0.004 * w_small)
    cuts, lo = [], 0.0
    for k in range(1, n):
        target = H * k / n
        a = int(max(lo + 0.08 * H, target - window * H) * s)
        b = int(min(H - 1, target + window * H) * s)
        best = None
        i = a
        while i <= b:                       # duyệt các dải hàng trống trong cửa sổ quanh mốc
            if not blank[i]:
                i += 1
                continue
            j = i
            while j + 1 <= b and blank[j + 1]:
                j += 1
            c = (i + j) / 2 / s
            score = (j - i + 1) / s - 0.15 * abs(c - target)
            if best is None or score > best[0]:
                best = (score, c)
            i = j + 1
        if best:
            cut = best[1]
        elif b > a:                         # không có hàng trống nào: lấy hàng ít mực nhất
            cut = (a + int(np.argmin(prof[a:b + 1]))) / s
        else:
            cut = target
        cuts.append(int(round(cut)))
        lo = cut
    ys = [0] + cuts + [H]
    return [(ys[i], ys[i + 1]) for i in range(n)]


# ---------------------------------------------------------------- chia trang thành các phần, đọc riêng rồi ghép
def plan_split(img: Image.Image, spec: dict, text: dict | None, n: int = 4) -> dict | None:
    """Các dải ngang của trang và hệ số phóng của từng dải. None nếu trang không phải trang dọc kiểu A4."""
    bands = split_bands(img, n)
    if not bands:
        return None
    W, H = img.size
    lines = (text or {}).get("lines") or []
    page_h = sorted(b[3] - b[1] for b in lines)
    so = fit_scale(W, H, spec, max_up=2.0)
    tiles = []
    for y0, y1 in bands:
        hs = sorted(b[3] - b[1] for b in lines if y0 <= (b[1] + b[3]) / 2 < y1) or page_h
        small_h = max(4.0, hs[len(hs) // 10]) if hs else 30.0
        # phóng để chữ nhỏ trong dải cao khoảng 1,2 lần cỡ dễ đọc, nhưng không vượt giới hạn ảnh của model
        s = fit_scale(W, y1 - y0, spec, max_up=min(4.0, max(1.0, tx.TARGET_LINE_PX * 1.2 / small_h)))
        tiles.append({"box": [0, y0, W, y1], "scale": s})
    return {"overview_scale": so, "tiles": tiles}


def split_shots(img: Image.Image, plan: dict, page_label: str, prep: dict | None = None) -> list[Shot]:
    prep = tx.normalize_prep(prep)
    bgr = tx.to_bgr(img)
    H = img.height
    n = len(plan["tiles"])
    shots = []
    for k, t in enumerate(plan["tiles"]):
        _, y0, _, y1 = (int(v) for v in t["box"])
        z = t["scale"] / max(plan["overview_scale"], 1e-6)
        shots.append(Shot(f"{page_label}, phần {k + 1}/{n} (cắt ngang từ trên xuống, khoảng {round(100 * y0 / H)}–"
                          f"{round(100 * y1 / H)}% chiều dọc trang), phóng ×{z:.1f} so với ảnh toàn trang",
                          tx.to_pil(tx.finish_tile(bgr[y0:y1], prep, t["scale"]))))
    return shots


# ================================================================ ghép kết quả các phần
_PAGE_HEAD = re.compile(r"^\s*#{1,3}\s.*\bTRANG\s+\d+", re.I)


_NOTE_HEAD = re.compile(r"^(\s*\**\s*Ghi chú đọc tài liệu\s*:?\s*\**\s*:?)", re.I)


_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")


def _norm(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip().lower()


def _is_row(line: str) -> bool:
    return line.strip().startswith("|")


def _cols(line: str) -> int:
    return len(line.strip().strip("|").split("|"))


def _table_header(lines: list[str]) -> str | None:
    """Hàng tiêu đề của bảng nằm ở cuối danh sách dòng (nếu bảng đó có hàng kẻ |---| ngay sau tiêu đề)."""
    s = len(lines)
    while s > 0 and _is_row(lines[s - 1]):
        s -= 1
    return lines[s] if s + 1 < len(lines) and _TABLE_SEP.match(lines[s + 1]) else None


def _join_parts(a: list[str], b: list[str]) -> list[str]:
    tail = {_norm(x) for x in a[-3:] if x.strip()}
    while b and (not b[0].strip() or (len(_norm(b[0])) >= 8 and _norm(b[0]) in tail)):
        b = b[1:]                               # dòng ở mép bị chép ở cả hai phần: chỉ giữ một lần
    if not b:
        return a
    if _is_row(a[-1]) and _is_row(b[0]) and _cols(a[-1]) == _cols(b[0]):
        # bảng bị cắt ngang: phần sau thường có thêm hàng kẻ |---| (và có khi lặp lại tiêu đề cột) → nối thành một bảng
        if len(b) > 1 and _TABLE_SEP.match(b[1]):
            head = _table_header(a)
            b = b[2:] if head is not None and _norm(head) == _norm(b[0]) else [b[0]] + b[2:]
        return a + b
    if _is_row(a[-1]) or _is_row(b[0]):
        return a + [""] + b                     # Markdown cần dòng trống giữa bảng và chữ thường
    return a + b


def stitch_parts(parts: list[str]) -> str:
    """Ghép kết quả các phần của một trang theo thứ tự: bỏ tiêu đề trang lặp lại ở các phần sau, nối bảng bị cắt,
    gom các đoạn ghi chú khó đọc về cuối trang."""
    bodies, notes = [], []
    for k, raw in enumerate(parts):
        lines = trim_loop(clean_output(raw)).split("\n")
        for j, line in enumerate(lines):
            if _NOTE_HEAD.match(line):
                notes.append("\n".join(lines[j:]).strip())
                lines = lines[:j]
                break
        while lines and (not lines[0].strip() or lines[0].strip() == "---" or (k > 0 and _PAGE_HEAD.match(lines[0]))):
            lines = lines[1:]
        while lines and lines[-1].strip() in ("", "---"):
            lines = lines[:-1]
        if lines:
            bodies.append(lines)
    out = bodies[0] if bodies else []
    for b in bodies[1:]:
        out = _join_parts(out, b)
    text = "\n".join(out)
    if notes:
        prefix = _NOTE_HEAD.match(notes[0]).group(1).strip()
        found = [n[_NOTE_HEAD.match(n).end():].strip() for n in notes]
        found = [f for f in found if f and not re.fullmatch(r"không có chỗ khó đọc\.?", f, flags=re.I)]
        text += f"\n\n{prefix} " + (" ".join(found) if found else "Không có chỗ khó đọc.")
    return text



# ================================================================ luồng đọc
def doc_tach_4_phan(trang: list[Image.Image], cfg: dict, ten_tep: str = "tep", ghi_chu: str = "",
                    xoay_tay: list[int] | None = None, bao=None) -> KetQua:
    """Đọc mọi trang của một tệp ở chế độ tự cắt 4 phần.

    trang: các trang ảnh (doc_tep.load_document); cfg: cau_hinh.tao_cau_hinh(); ten_tep: tên hiện trong lời kết;
    ghi_chu: ngữ cảnh cho model (không bắt buộc); xoay_tay: số độ xoay thêm cho từng trang (không bắt buộc);
    bao(su_kien): nhận sự kiện {"type": "status" | "text" | "usage", "trang": i, "phan": k, ...} trong lúc đọc
    (được gọi từ nhiều luồng cùng lúc)."""
    started = time.time()
    n_pages = len(trang)
    kq = KetQua(so_trang=n_pages, che_do="tach_4_phan")
    tong = TongHop(kq)
    may = MayChuQwen(cfg)
    prep = cfg["prep"]
    hint = ghi_chu_nguoi_dung(ghi_chu)
    xoay_tay = xoay_tay or [0] * n_pages
    parts = []
    for i in range(n_pages):                       # các trang lần lượt
        label = f"Trang {i + 1}/{n_pages}"
        page, info = tx.chuan_bi_trang(trang[i], prep, xoay_tay[i])
        if info.get("steps"):
            bao_su_kien(bao, {"type": "status", "trang": i, "text": f"{label}: đã {', '.join(info['steps'])}."})
        thong_tin = {"trang": i + 1, "buoc": info.get("steps", []), "chieu_chu": info.get("orient")}
        plan = plan_split(page, may.spec, info.get("text"), int(cfg.get("so_phan", 4)))
        if plan:
            kq.so_trang_da_cat += 1
            shots = split_shots(page, plan, label, prep)
            n = len(shots)
            bao_su_kien(bao, {"type": "status", "trang": i, "text": f"{label}: đã chia thành {n} phần, đang đọc song song"})

            def work(k, i=i, n=n, shots=shots):
                req = cb.build_content([shots[k]], loi_ket_phan(i, k, n, n_pages, ten_tep) + hint, cfg["image_format"])
                cb_ev = (lambda ev: bao_su_kien(bao, {**ev, "trang": i, "phan": k})) if bao else None
                return may.doc(req.content, max_tokens=int(cfg.get("max_tokens_moi_phan", 1536)), bao=cb_ev)

            with ThreadPoolExecutor(max_workers=max(1, min(int(cfg.get("song_song", 4) or 1), n))) as pool:
                futs = [pool.submit(work, k) for k in range(n)]
                try:
                    res = [f.result() for f in futs]   # lỗi ở một phần thì dừng cả lần đọc, như web
                except BaseException:
                    for f in futs:
                        f.cancel()
                    raise
            for k, (_, usage) in enumerate(res):
                tong.them(usage, f"{label}, phần {k + 1}")
            parts.append(stitch_parts([t for t, _ in res]))
            thong_tin.update({"cach_doc": f"cắt {n} phần", "duong_cat": [t["box"][1] for t in plan["tiles"][1:]],
                              "so_anh": n})
        else:                                      # thẻ, ảnh ngang: chia ngang không hợp, đọc cả trang
            shots = cb.page_shots(page, label, cfg["zoom"], may.spec, prep, max_images=may.max_images,
                                  text=info.get("text"))
            req = cb.build_content(shots, loi_ket_trang(i, n_pages, ten_tep) + hint, cfg["image_format"])
            bao_su_kien(bao, {"type": "status", "trang": i,
                              "text": f"{label}: giấy không phải khổ A4 dọc, đọc cả trang không tách"})
            text, usage = may.doc(req.content, bao=(lambda ev: bao_su_kien(bao, {**ev, "trang": i})) if bao else None)
            tong.them(usage, label if n_pages > 1 else "")
            parts.append(gq.trim_loop(gq.clean_output(text)))
            thong_tin.update({"cach_doc": "cả trang (không phải A4 dọc)", "so_anh": req.image_count})
        kq.trang.append(thong_tin)
    kq.markdown = NOI_TRANG.join(p for p in parts if p).strip()
    if not kq.markdown:
        raise RuntimeError("Model không trả về nội dung nào. Thử đọc lại, hoặc kiểm tra model trên máy chủ có đọc được ảnh không.")
    kq.markdown += "\n"
    kq.giay = round(time.time() - started, 1)
    return kq
