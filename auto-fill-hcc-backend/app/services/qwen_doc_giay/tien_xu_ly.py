# -*- coding: utf-8 -*-
"""Tiền xử lý ảnh giấy tờ trước khi OCR.

Tầng trang (làm một lần trên ảnh trang, theo thứ tự):
  1. tự xoay theo chiều chữ 90°/180°/270° (detect_orientation), không cần model
  2. chỉnh nghiêng nhỏ (tối đa 8°)
  3. cân bằng sáng: xóa bóng đổ, vùng tối, màu giấy ngả (chỉ khi ảnh sáng không đều)
  4. tìm các dòng chữ (để chia dải phóng to theo vùng chữ)
  5. tùy chọn: tăng tương phản (CLAHE), lọc hoa văn nền và dấu đỏ
Tầng vùng (làm trên từng ảnh gửi đi, sau khi đã phóng/thu về cỡ gửi): khử nhiễu, làm nét hoặc chuyển đen trắng.

Hàm chính: chuan_bi_trang(img, prep) ở cuối tệp. Các hàm còn lại trích nguyên văn từ tien_xu_ly.py của web.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


# Không bao giờ cắt ảnh: tiền xử lý chỉ chỉnh nghiêng (mở rộng khung, giữ đủ trang), cân sáng và lọc, không bỏ phần nào
# của trang. Bản trước có "doc_crop" (tự tìm mép giấy rồi cắt) nhưng hay nhận nhầm khung kẻ trong giấy là mép giấy và
# cắt mất phần lớn trang, nên đã gỡ bỏ hẳn.
DEFAULT_PREP = {
    "auto_orient": True,    # tự xoay 90°/180°/270° cho chữ đứng thẳng (nhận diện một lần cho mỗi trang)
    "deskew": True,         # chỉnh nghiêng
    "illum": True,          # cân bằng sáng, xóa bóng (chỉ áp dụng khi ảnh sáng không đều)
    "clahe": False,         # tăng tương phản cục bộ
    "pattern": False,       # lọc hoa văn nền màu và dấu đỏ (chữ màu sẽ nhạt đi)
    "denoise": "off",       # khử nhiễu: off | zoom (chỉ vùng phải phóng to) | on (mọi vùng, chậm)
    "sharpen": "light",     # off | light | medium | strong
    "binarize": False,      # chuyển đen trắng
}


DENOISE_MODES = ("off", "zoom", "on")


SHARPEN_LEVELS = {"off": None, "light": (1.0, 0.6), "medium": (1.2, 1.0), "strong": (1.4, 1.6)}


TARGET_LINE_PX = 36          # chiều cao dòng chữ mong muốn trong ảnh gửi đi


def normalize_prep(p: dict | None) -> dict:
    out = dict(DEFAULT_PREP)
    for k, v in (p or {}).items():
        if k in out:
            out[k] = v if k in ("sharpen", "denoise") else bool(v)
    if out["sharpen"] not in SHARPEN_LEVELS:
        out["sharpen"] = "light"
    if out["denoise"] not in DENOISE_MODES:     # bản trước là bật/tắt
        out["denoise"] = "on" if out["denoise"] is True else "off"
    return out


def to_bgr(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def to_pil(a: np.ndarray) -> Image.Image:
    if a.ndim == 2:
        a = cv2.cvtColor(a, cv2.COLOR_GRAY2BGR)
    return Image.fromarray(cv2.cvtColor(a, cv2.COLOR_BGR2RGB))


def _resize_max(a: np.ndarray, max_side: int) -> tuple[np.ndarray, float]:
    h, w = a.shape[:2]
    s = min(1.0, max_side / max(h, w))
    if s < 1.0:
        a = cv2.resize(a, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    return a, s


# ------------------------------------------------------------------ chỉnh nghiêng
def _ink_mask(bgr: np.ndarray, block: int | None = None) -> np.ndarray:
    """Mặt nạ nét mực tối. Dùng kênh sáng nhất (max RGB) để hoa văn màu nhạt và dấu đỏ không bị tính là chữ."""
    g = bgr.max(axis=2) if bgr.ndim == 3 else bgr
    h, w = g.shape[:2]
    block = block or (max(15, (max(h, w) // 60) | 1))
    return cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block, 12)


def estimate_skew(bgr: np.ndarray, limit: float = 8.0) -> float:
    small, _ = _resize_max(bgr, 1400)
    m = _ink_mask(small)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    h, w = m.shape
    ctr = (w / 2, h / 2)

    def score(a: float) -> float:
        M = cv2.getRotationMatrix2D(ctr, a, 1.0)
        r = cv2.warpAffine(m, M, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
        rows = r.sum(1, dtype=np.float64)
        return float(np.sum(np.diff(rows) ** 2))

    base = score(0.0)
    best_a, best_s = 0.0, base
    for a in np.arange(-limit, limit + 0.01, 0.5):
        sc = score(float(a))
        if sc > best_s:
            best_a, best_s = float(a), sc
    for a in np.arange(best_a - 0.5, best_a + 0.51, 0.1):
        sc = score(float(a))
        if sc > best_s:
            best_a, best_s = float(a), sc
    if abs(best_a) < 0.3 or best_s < base * 1.05:
        return 0.0
    return round(best_a, 1)


def rotate_keep(bgr: np.ndarray, angle: float) -> np.ndarray:
    h, w = bgr.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    M[0, 2] += nw / 2 - w / 2
    M[1, 2] += nh / 2 - h / 2
    # tô góc trống bằng màu nền của trang (trung vị viền ngoài) thay vì kéo dãn mép ảnh
    e = max(2, min(h, w) // 50)
    border = np.concatenate([bgr[:e].reshape(-1, 3), bgr[-e:].reshape(-1, 3),
                             bgr[:, :e].reshape(-1, 3), bgr[:, -e:].reshape(-1, 3)])
    fill = tuple(int(v) for v in np.median(border, axis=0))
    return cv2.warpAffine(bgr, M, (nw, nh), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=fill)


# ------------------------------------------------------------------ chiều chữ: xoay 90°, 180°, 270°
# Không cần model: (1) chữ chạy ngang hay dọc nhận ra qua nhịp dòng chữ / khoảng trắng giữa các dòng;
# (2) xuôi hay ngược nhận ra qua đặc điểm chữ Việt: chân chữ thẳng hàng theo đường kẻ còn đỉnh chữ nhấp nhô,
# và dấu thanh (sắc, huyền, hỏi, ngã, mũ, móc) nằm trên nhiều hơn hẳn dấu nặng nằm dưới.
ORIENT_VERSION = 2           # tăng khi đổi cách nhận diện: các trang đã lưu sẽ được nhận diện lại


ORIENT_EDGE = 1400           # đủ để biết chữ chạy ngang hay dọc


ORIENT_FINE_EDGE = 2600      # xuôi/ngược cần thấy rõ dấu thanh tách khỏi chữ


ORIENT_W_BASE, ORIENT_W_DIAC = 1.0, 1.0


ORIENT_FLIP_MIN = 0.08       # điểm xuôi/ngược tối thiểu để lật 180°


ORIENT_MIN_EVIDENCE = 30     # số cặp chữ / dấu thanh tối thiểu làm bằng chứng


def _char_mask(bgr: np.ndarray, edge: int = ORIENT_EDGE) -> np.ndarray:
    """Mặt nạ các nét cỡ chữ (bỏ đường kẻ bảng, khung, mảng lớn), như nhau theo mọi chiều xoay."""
    small, _ = _resize_max(bgr, edge)
    sh, sw = small.shape[:2]
    mx = small.max(axis=2)
    otsu, _ = cv2.threshold(mx, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    core = mx[sh // 6: sh - sh // 6, sw // 6: sw - sw // 6]     # bỏ lề (ảnh chụp thường có lề trắng quanh vật)
    if (core < otsu).mean() > 0.5:                # nền tối, chữ sáng (bia, biển, ảnh âm bản): đảo màu
        small = 255 - small
        mx = small.max(axis=2)
        otsu, _ = cv2.threshold(mx, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = (mx < min(float(otsu), 165.0)).astype(np.uint8) * 255
    m = cv2.bitwise_and(_ink_mask(small), dark)
    L = max(25, max(sh, sw) // 20)
    hl = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (L, 1)))
    vl = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, L)))
    m = cv2.subtract(m, cv2.bitwise_or(hl, vl))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return np.zeros_like(m)
    ws, hs, areas = stats[1:, 2], stats[1:, 3], stats[1:, 4]
    big, small_side = np.maximum(ws, hs), np.minimum(ws, hs)
    ok = (areas >= 3) & (big <= max(sh, sw) * 0.05) & (big <= 8 * small_side + 2)
    keep = np.zeros(n, dtype=np.uint8)
    keep[1:][ok] = 255
    return keep[labels]


def _profile_cv(p: np.ndarray) -> float:
    """Độ nhấp nhô của một đường chiếu (độ lệch chuẩn / trung bình), chỉ trong phần có mực."""
    c = np.cumsum(p)
    if c[-1] <= 0:
        return 0.0
    lo, hi = np.searchsorted(c, c[-1] * 0.02), np.searchsorted(c, c[-1] * 0.98)
    q = p[lo:hi + 1].astype(np.float64)
    return float(q.std() / q.mean()) if q.size > 8 and q.mean() > 0 else 0.0


def _rotate_mask(m: np.ndarray, a: float) -> np.ndarray:
    if not a:
        return m
    h, w = m.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), a, 1.0)
    return cv2.warpAffine(m, M, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)


def _text_axis(m: np.ndarray) -> tuple[float, float, float]:
    """(độ nhấp nhô theo hàng, theo cột, góc nghiêng nhỏ tốt nhất). Thử vài góc lệch vì trang có thể hơi nghiêng."""
    best_r, best_c, best_a = 0.0, 0.0, 0.0
    for a in (-6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0):
        r = _rotate_mask(m, a)
        cr = _profile_cv(r.sum(axis=1, dtype=np.float64))
        cc = _profile_cv(r.sum(axis=0, dtype=np.float64))
        if cr > best_r:
            best_r, best_a = cr, a
        best_c = max(best_c, cc)
    return best_r, best_c, best_a


def _wmedian(v: np.ndarray, w: np.ndarray) -> float:
    o = np.argsort(v)
    c = np.cumsum(w[o].astype(np.float64))
    return float(v[o][np.searchsorted(c, c[-1] / 2)])


def _text_scales(hs: np.ndarray, ar: np.ndarray, cand: np.ndarray) -> list[float]:
    """Các cỡ chữ chính trên trang (trung vị chiều cao có trọng số theo lượng mực, để hàng nghìn dấu chấm của
    dòng kẻ chấm không kéo cỡ chữ xuống). Thêm cỡ nhỏ hơn / lớn hơn nếu chúng chiếm đáng kể lượng mực,
    ví dụ mặt sau thẻ: dải MRZ chữ to và các dòng nhãn chữ nhỏ."""
    ink = float(ar[cand].sum())
    s1 = _wmedian(hs[cand], ar[cand])
    scales = [s1]
    for sel in (cand & (hs < 0.6 * s1) & (hs >= 6), cand & (hs > 1.8 * s1)):
        if sel.sum() >= 30 and ar[sel].sum() >= 0.15 * ink:
            scales.append(_wmedian(hs[sel], ar[sel]))
    return scales


def _scale_cues(m: np.ndarray, labels, st, cent, sane, mh: float) -> tuple[int, int, int, int]:
    """Bằng chứng xuôi/ngược ở một cỡ chữ mh: (cặp chữ chân thẳng hàng, cặp đỉnh thẳng hàng, dấu trên, dấu dưới)."""
    H, W = m.shape
    n = len(st)
    hs, ws, ar = st[:, 3], st[:, 2], st[:, 4]
    main = sane & (hs >= 0.6 * mh) & (hs <= 1.8 * mh)
    # chỉ giữ nét nằm trong một dòng chữ (khối dài, mảnh khi nối ngang); vân tay, ảnh chân dung, con dấu tròn bị loại
    keep = np.zeros(n + 1, dtype=np.uint8)
    keep[np.nonzero(main)[0] + 1] = 255
    blobs = cv2.dilate(keep[labels], cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, int(1.5 * mh)), 1)))
    nb, blab, bst, _ = cv2.connectedComponentsWithStats(blobs, 8)
    textlike = np.zeros(nb, dtype=bool)
    textlike[1:] = (bst[1:, 3] <= 2.2 * mh) & (bst[1:, 2] >= 3 * bst[1:, 3])
    cx = np.clip(cent[:, 0].astype(np.int64), 0, W - 1)
    cy = np.clip(cent[:, 1].astype(np.int64), 0, H - 1)
    main &= textlike[blab[cy, cx]]
    idx = np.nonzero(main)[0]
    if len(idx) < 10:
        return 0, 0, 0, 0
    keepm = np.zeros(n + 1, dtype=bool)
    keepm[idx + 1] = True
    lab = np.where(keepm[labels], labels, 0)

    # (1) mỗi chữ so với chữ kề bên phải: chân thẳng hàng mà đỉnh lệch (chữ xuôi) hay ngược lại.
    # So từng cặp kề nhau nên không cần dòng chữ thẳng (ảnh chụp nghiêng, dòng cong vẫn đúng).
    colmap = np.where(lab > 0, np.arange(W, dtype=np.int32)[None, :], W).astype(np.int32)
    nxt = np.minimum.accumulate(colmap[:, ::-1], axis=1)[:, ::-1]
    x, y, w, h = (st[idx, k].astype(np.int64) for k in range(4))
    c0 = np.minimum(x + w, W - 1)
    best_d = np.full(len(idx), W, dtype=np.int64)
    best_j = np.zeros(len(idx), dtype=np.int64)
    for frac in (0.35, 0.5, 0.65):
        r = np.clip(y + (h * frac).astype(np.int64), 0, H - 1)
        nc = nxt[r, c0]
        ok = nc < W
        j = np.where(ok, lab[r, np.minimum(nc, W - 1)], 0)
        d = np.where(ok, nc - c0, W)
        better = (d < best_d) & (j > 0) & (j - 1 != idx)
        best_d, best_j = np.where(better, d, best_d), np.where(better, j, best_j)
    v = (best_j > 0) & (best_d <= max(2, int(0.8 * mh)))
    pos = neg = 0
    if v.any():
        j = best_j[v] - 1
        ti, hi = y[v], h[v]
        tj, hj = st[j, 1].astype(np.int64), st[j, 3].astype(np.int64)
        tol = np.maximum(1.5, 0.12 * np.minimum(hi, hj))
        db, dt = np.abs((ti + hi) - (tj + hj)), np.abs(ti - tj)
        pos = int(((db <= tol) & (dt > tol)).sum())
        neg = int(((dt <= tol) & (db > tol)).sum())

    # (2) dấu thanh: nét nhỏ nằm sát ngay trên một chữ (chữ xuôi) hay sát ngay dưới (chữ ngược).
    # Bỏ trước các dòng chấm "......" của mẫu đơn: chữ viết tay nằm trên dòng chấm nên chấm dễ bị tính là dấu dưới.
    tiny = sane & (hs < 0.5 * mh) & (ws < 1.3 * mh) & (ar >= 2)
    keept = np.zeros(n + 1, dtype=np.uint8)
    keept[np.nonzero(tiny)[0] + 1] = 255
    dl = cv2.dilate(keept[labels], cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, int(2.5 * mh)), 1)))
    nd, dlab, dst, _ = cv2.connectedComponentsWithStats(dl, 8)
    dotted = np.zeros(nd, dtype=bool)
    dotted[1:] = (dst[1:, 2] > 6 * mh) & (dst[1:, 3] < 0.9 * mh)
    ti_ = np.nonzero(tiny)[0]
    ti_ = ti_[~dotted[dlab[cy[ti_], cx[ti_]]]]
    up = down = 0
    if len(ti_):
        rows = np.arange(H, dtype=np.int32)[:, None]
        mm = lab > 0
        below = np.minimum.accumulate(np.where(mm, rows, H).astype(np.int32)[::-1], axis=0)[::-1]
        above = np.maximum.accumulate(np.where(mm, rows, -1).astype(np.int32), axis=0)
        x, y, w, h = (st[ti_, k].astype(np.int64) for k in range(4))
        yb, yt = np.minimum(y + h, H - 1), np.maximum(y - 1, 0)
        db = np.full(len(ti_), H, dtype=np.int64); jb = np.zeros(len(ti_), dtype=np.int64)
        da = np.full(len(ti_), H, dtype=np.int64); ja = np.zeros(len(ti_), dtype=np.int64)
        for c in (x, x + w // 2, x + w - 1):
            c = np.clip(c, 0, W - 1)
            rb = below[yb, c]
            d1 = np.where(rb < H, rb - yb, H)
            l1 = np.where(rb < H, lab[np.minimum(rb, H - 1), c], 0)
            better = d1 < db
            db, jb = np.where(better, d1, db), np.where(better, l1, jb)
            ra = above[yt, c]
            d2 = np.where(ra >= 0, yt - ra, H)
            l2 = np.where(ra >= 0, lab[np.maximum(ra, 0), c], 0)
            better = d2 < da
            da, ja = np.where(better, d2, da), np.where(better, l2, ja)
        # chỉ tính khi sát chữ (cách không quá 35% chiều cao chữ) và thấp hơn nửa chữ đó
        hb = np.where(jb > 0, st[np.maximum(jb - 1, 0), 3], 1)
        ha = np.where(ja > 0, st[np.maximum(ja - 1, 0), 3], 1)
        ok_b = (jb > 0) & (db <= 0.35 * hb) & (h <= 0.5 * hb)
        ok_a = (ja > 0) & (da <= 0.35 * ha) & (h <= 0.5 * ha)
        up = int((ok_b & (~ok_a | (db < da))).sum())        # cách đều hai dòng thì không tính
        down = int((ok_a & (~ok_b | (da < db))).sum())
    return pos, neg, up, down


def _updown_score(m: np.ndarray) -> tuple[float, int]:
    """Mặt nạ có chữ chạy ngang: > 0 nếu chữ xuôi, < 0 nếu chữ lộn ngược. Trả (điểm từ -1 tới 1, số bằng chứng)."""
    n, labels, st, cent = cv2.connectedComponentsWithStats(m, 8)
    st, cent = st[1:], cent[1:]
    hs, ws, ar = st[:, 3], st[:, 2], st[:, 4]
    big = np.maximum(ws, hs)
    sane = (ar >= 2) & (big <= max(m.shape) * 0.05) & (big <= 8 * np.minimum(ws, hs) + 2)
    cand = sane & (hs >= 4)
    if cand.sum() < 20:
        return 0.0, 0
    pos = neg = up = down = 0
    for mh in _text_scales(hs, ar, cand):
        a, b, c, d = _scale_cues(m, labels, st, cent, sane, mh)
        pos, neg, up, down = pos + a, neg + b, up + c, down + d
    parts, ev = [], 0
    if pos + neg >= 10:
        parts.append(((pos - neg) / (pos + neg), ORIENT_W_BASE))
        ev += pos + neg
    if up + down >= 6:
        parts.append(((up - down) / (up + down), ORIENT_W_DIAC))
        ev += up + down
    if not parts:
        return 0.0, 0
    return float(sum(v * w for v, w in parts) / sum(w for _, w in parts)), ev


def detect_orientation(img) -> dict:
    """Chiều cần xoay (theo chiều kim đồng hồ) để chữ đứng thẳng, đọc từ trái sang phải: 0, 90, 180 hoặc 270.
    Trả {"deg", "conf": "cao" | "vừa" | "thấp", "axis": > 0 chữ chạy ngang / < 0 chạy dọc, "updown": > 0 xuôi / < 0 ngược,
    "ev": số bằng chứng (cặp chữ kề nhau, dấu thanh), "v": phiên bản cách nhận diện}.
    Không thấy dòng chữ rõ (trang trắng, ảnh) thì giữ nguyên deg = 0.
    Đo trên 307 trang thật (căn cước, tờ khai viết tay, sổ hộ khẩu, giấy chứng nhận...), mỗi trang xoay 4 hướng:
    đúng 97,1%; khi tin cậy "cao" hoặc "vừa" (95% số lần) đúng 100%; trang đã đúng chiều bị xoay nhầm 1/307 (tin cậy thấp)."""
    bgr = img if isinstance(img, np.ndarray) else to_bgr(img)
    m = _char_mask(bgr)
    out = {"deg": 0, "conf": "thấp", "axis": 0.0, "updown": 0.0, "ev": 0, "v": ORIENT_VERSION}
    if cv2.countNonZero(m) < 200:
        return out
    cr, cc, a = _text_axis(m)
    ratio = (cr + 1e-6) / (cc + 1e-6)
    out["axis"] = round(float(np.log(ratio)), 3)           # > 0: chữ chạy ngang; < 0: chữ chạy dọc
    if abs(out["axis"]) < 0.12:
        return out                                          # không rõ chiều dòng chữ: không xoay
    fine = _char_mask(bgr, ORIENT_FINE_EDGE)
    if ratio >= 1:
        hm, base = _rotate_mask(fine, a), 0
    else:
        _, _, a2 = _text_axis(np.ascontiguousarray(np.rot90(m, k=-1)))
        hm = np.ascontiguousarray(np.rot90(fine, k=-1))     # xoay 90° theo chiều kim đồng hồ cho chữ nằm ngang
        hm, base = _rotate_mask(hm, a2), 90
    sc, ev = _updown_score(hm)
    out["updown"], out["ev"] = round(sc, 3), ev
    if base == 0:
        # chữ đã nằm ngang: chỉ lật 180° khi bằng chứng đủ mạnh. Trang lộn ngược thật hiếm, còn lật nhầm một trang
        # đang đúng thì hại hơn bỏ sót, nên giấy ít chữ thường (mặt sau thẻ, bảng toàn chữ in hoa) cứ để nguyên.
        if sc < -ORIENT_FLIP_MIN and ev >= ORIENT_MIN_EVIDENCE:
            out["deg"] = 180
        strong = abs(out["axis"]) >= 0.35 and abs(sc) >= 0.15 and ev >= 80
        out["conf"] = "cao" if strong else ("vừa" if ev >= ORIENT_MIN_EVIDENCE and abs(sc) >= ORIENT_FLIP_MIN else "thấp")
        return out
    # chữ chạy dọc: chắc chắn phải xoay, chọn 90° hay 270° theo dấu của điểm (yếu thì độ tin cậy thấp)
    out["deg"] = 90 if sc >= 0 else 270
    strong = abs(out["axis"]) >= 0.35 and abs(sc) >= 0.15 and ev >= 80
    out["conf"] = "cao" if strong else ("vừa" if abs(sc) >= ORIENT_FLIP_MIN and ev >= ORIENT_MIN_EVIDENCE else "thấp")
    return out


# ------------------------------------------------------------------ ánh sáng, tương phản, hoa văn
def normalize_illumination(bgr: np.ndarray) -> tuple[np.ndarray, bool]:
    h, w = bgr.shape[:2]
    small, s = _resize_max(bgr, 700)
    k = max(15, int(min(small.shape[:2]) * 0.05)) | 1
    bg = cv2.morphologyEx(small, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    bg = cv2.medianBlur(bg, min(k, 99) if min(k, 99) % 2 else min(k, 99) - 1)
    g = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
    lo, mid, hi = np.percentile(g, [5, 50, 95])
    sat = cv2.cvtColor(bg, cv2.COLOR_BGR2HSV)[..., 1].mean()
    if hi - lo < 22 and mid > 215 and sat < 25:
        return bgr, False                       # đã sáng đều, giấy trắng: không cần
    bg_full = cv2.resize(bg, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    out = cv2.divide(bgr.astype(np.float32), np.maximum(bg_full, 1.0), scale=255.0)
    return np.clip(out, 0, 255).astype(np.uint8), True


def apply_clahe(bgr: np.ndarray, clip: float = 1.8) -> np.ndarray:
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    lab[..., 0] = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8)).apply(lab[..., 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def suppress_pattern(bgr: np.ndarray) -> np.ndarray:
    """Lấy kênh sáng nhất: hoa văn màu nhạt và dấu đỏ gần như biến mất, chữ đen/xanh đậm giữ lại."""
    m = bgr.max(axis=2).astype(np.float32)
    lo, hi = np.percentile(m, [1, 99])
    m = np.clip((m - lo) * 255.0 / max(hi - lo, 1.0), 0, 255).astype(np.uint8)
    return cv2.cvtColor(m, cv2.COLOR_GRAY2BGR)


# ------------------------------------------------------------------ tầng vùng
def sharpen(bgr: np.ndarray, level: str) -> np.ndarray:
    cfg = SHARPEN_LEVELS.get(level)
    if not cfg:
        return bgr
    sigma, amount = cfg
    blur = cv2.GaussianBlur(bgr, (0, 0), sigma)
    return cv2.addWeighted(bgr, 1 + amount, blur, -amount, 0)


def denoise(bgr: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(bgr, None, 4, 4, 7, 21)


def sauvola(bgr: np.ndarray, k: float = 0.2) -> np.ndarray:
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = g.shape
    win = max(15, (min(h, w) // 30) | 1)
    mean = cv2.boxFilter(g, -1, (win, win), borderType=cv2.BORDER_REFLECT)
    sq = cv2.boxFilter(g * g, -1, (win, win), borderType=cv2.BORDER_REFLECT)
    std = np.sqrt(np.maximum(sq - mean * mean, 0))
    thr = mean * (1 + k * (std / 128.0 - 1))
    out = np.where(g > thr, 255, 0).astype(np.uint8)
    return cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)


def resize_to(bgr: np.ndarray, s: float) -> np.ndarray:
    if abs(s - 1) < 1e-3:
        return bgr
    h, w = bgr.shape[:2]
    size = (max(1, round(w * s)), max(1, round(h * s)))
    return cv2.resize(bgr, size, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)


def finish_tile(bgr: np.ndarray, prep: dict, scale: float) -> np.ndarray:
    """Phóng/thu vùng về cỡ gửi đi rồi áp các bộ lọc tầng vùng."""
    out = resize_to(bgr, scale)
    d = prep.get("denoise")
    # thu nhỏ (INTER_AREA) đã lấy trung bình nhiều điểm ảnh nên nhiễu tự mịn đi; chế độ "zoom" chỉ khử khi phải phóng to
    if d in (True, "on") or (d == "zoom" and scale > 1.05):
        out = denoise(out)
    if prep.get("binarize"):
        out = sauvola(out)
    else:
        out = sharpen(out, prep.get("sharpen", "light"))
    return out


# ------------------------------------------------------------------ tầng trang
def process_page(img: Image.Image, prep: dict) -> tuple[Image.Image, dict]:
    """Áp các bộ lọc tầng trang. Trả ảnh đã xử lý và mô tả những gì đã làm."""
    prep = normalize_prep(prep)
    bgr = to_bgr(img)
    info = {"steps": []}
    if prep["deskew"]:
        a = estimate_skew(bgr)
        if a:
            bgr = rotate_keep(bgr, a)
            info["steps"].append(f"chỉnh nghiêng {abs(a):.1f}°".replace(".", ","))
            info["skew"] = a
    if prep["illum"]:
        bgr, done = normalize_illumination(bgr)
        if done:
            info["steps"].append("cân bằng sáng")
    info["text"] = detect_text_lines(bgr)
    if prep["clahe"]:
        bgr = apply_clahe(bgr)
        info["steps"].append("tăng tương phản")
    if prep["pattern"]:
        bgr = suppress_pattern(bgr)
        info["steps"].append("lọc hoa văn nền")
    info["size"] = [int(bgr.shape[1]), int(bgr.shape[0])]
    return to_pil(bgr), info


# ------------------------------------------------------------------ tìm dòng chữ
def detect_text_lines(img) -> dict:
    """Tìm các dòng chữ (nhận ảnh PIL hoặc mảng BGR). Trả tọa độ theo pixel ảnh đưa vào."""
    bgr = img if isinstance(img, np.ndarray) else to_bgr(img)
    H, W = bgr.shape[:2]
    small, s = _resize_max(bgr, 2000)
    sh, sw = small.shape[:2]
    mx = small.max(axis=2)
    otsu, _ = cv2.threshold(mx, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = (mx < min(float(otsu), 165.0)).astype(np.uint8) * 255
    m = cv2.bitwise_and(_ink_mask(small), dark)
    # bỏ đường kẻ bảng, khung viền
    hl = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, sw // 20), 1)))
    vl = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, sh // 20))))
    m = cv2.subtract(m, cv2.bitwise_or(hl, vl))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return {"lines": [], "line_h": 0, "text_box": None}
    ws, hs, areas = stats[1:, 2], stats[1:, 3], stats[1:, 4]
    ok = (areas >= 6) & (hs >= 4) & (hs <= sh * 0.06) & (ws <= sw * 0.25) & (ws <= hs * 12)
    if ok.sum() < 8:
        return {"lines": [], "line_h": 0, "text_box": None}
    char_h = float(np.percentile(hs[ok], 70))
    keep = np.zeros(n, dtype=np.uint8)
    keep[1:][ok] = 255
    mask = keep[labels]
    # chỉ nối theo chiều ngang để các dòng sát nhau không dính thành một khối
    kw, kh = max(3, int(char_h * 2.2)), 1
    merged = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh)))
    cnts, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    lines = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if h < 0.6 * char_h or h > 4.0 * char_h or w < 2.5 * char_h:
            continue
        ink = cv2.countNonZero(mask[y:y + h, x:x + w])
        if ink < 0.06 * w * h or ink < 3 * char_h * char_h * 0.15:
            continue
        lines.append([x / s, y / s, (x + w) / s, (y + h) / s])
    if len(lines) < 2:
        return {"lines": [], "line_h": 0, "text_box": None}
    lines.sort(key=lambda b: (b[1], b[0]))
    heights = sorted(b[3] - b[1] for b in lines)
    line_h = heights[len(heights) // 2]
    tb = [min(b[0] for b in lines), min(b[1] for b in lines), max(b[2] for b in lines), max(b[3] for b in lines)]
    pad = line_h * 0.8
    tb = [max(0.0, tb[0] - pad), max(0.0, tb[1] - pad), min(float(W), tb[2] + pad), min(float(H), tb[3] + pad)]
    return {"lines": [[round(v, 1) for v in b] for b in lines], "line_h": round(line_h, 1),
            "text_box": [round(v, 1) for v in tb]}


def _rows(lines: list) -> list:
    """Gộp các khối chữ nằm cùng hàng (ví dụ nhãn bên trái, giá trị bên phải) thành một hàng."""
    rows = []
    for b in sorted(lines, key=lambda b: (b[1] + b[3]) / 2):
        cy = (b[1] + b[3]) / 2
        if rows and abs(cy - rows[-1]["cy"]) < 0.5 * (rows[-1]["y1"] - rows[-1]["y0"]):
            r = rows[-1]
            r["y0"], r["y1"] = min(r["y0"], b[1]), max(r["y1"], b[3])
            r["cy"] = (r["y0"] + r["y1"]) / 2
        else:
            rows.append({"y0": b[1], "y1": b[3], "cy": cy})
    return rows


def plan_text_tiles(W: int, H: int, text: dict, fit, max_tiles: int, max_up: float = 4.0) -> dict | None:
    """Chia vùng chữ thành các dải ngang và chọn hệ số phóng theo cỡ chữ NHỎ trên trang.

    Mục tiêu: dòng chữ nhỏ (bách phân vị 30 của chiều cao dòng) cao khoảng TARGET_LINE_PX điểm ảnh
    trong ảnh gửi đi. Ưu tiên dải trọn chiều ngang để không cắt đôi dòng chữ; chỉ chia cột khi giữ
    trọn chiều ngang thì chữ nhỏ vẫn quá bé.
    fit(w, h, max_up) -> hệ số lớn nhất để một ảnh w×h vừa giới hạn gửi đi.
    Trả {"tiles": [[x0,y0,x1,y1], ...], "scale", "cols", "rows"} hoặc None (khi đó dùng lưới cố định)."""
    if not text or not text.get("lines") or max_tiles < 1:
        return None
    heights = sorted(b[3] - b[1] for b in text["lines"])
    small_h = max(4.0, heights[int(len(heights) * 0.1)])
    lh = text["line_h"]
    tx0, ty0, tx1, ty1 = text["text_box"]
    tw = tx1 - tx0
    rows = _rows(text["lines"])
    s_need = min(max_up, max(0.5, 30.0 / small_h))            # tối thiểu để chữ nhỏ đọc được
    s_ideal = min(max_up, max(0.5, TARGET_LINE_PX / small_h))  # cỡ thoải mái
    s_one = fit(tw, lh * 3, max_up)
    one_col = s_one >= s_need
    s = min(s_one, s_ideal) if one_col else s_ideal
    floor = s_need * 0.7
    while s >= floor:
        cols = 1
        if not one_col:
            while fit(tw / cols * 1.1, lh * 3, max_up) < s and cols < 3:
                cols += 1
        col_w = tw / cols * (1.1 if cols > 1 else 1.0)
        lo, hi = lh, max(lh, ty1 - ty0)
        while hi - lo > 2:
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if fit(col_w, mid, max_up) >= s else (lo, mid)
        max_h = lo
        bands, cur = [], None
        for r in rows:
            if cur and (r["y1"] - cur[0]) + lh <= max_h:
                cur[1] = r["y1"]
            else:
                if cur:
                    bands.append(cur)
                cur = [r["y0"], r["y1"]]
        if cur:
            bands.append(cur)
        if len(bands) * cols <= max_tiles:
            break
        s *= 0.9
    else:
        return None
    edges = [ty0] + [(bands[i][1] + bands[i + 1][0]) / 2 for i in range(len(bands) - 1)] + [ty1]
    ov = lh * 0.5
    tiles = []
    cw = tw / cols
    for i in range(len(bands)):
        y0, y1 = max(0.0, edges[i] - ov), min(float(H), edges[i + 1] + ov)
        for c in range(cols):
            x0 = tx0 + c * cw - (cw * 0.05 if c else 0)
            x1 = tx0 + (c + 1) * cw + (cw * 0.05 if c < cols - 1 else 0)
            tiles.append([round(max(0.0, x0), 1), round(y0, 1), round(min(float(W), x1), 1), round(y1, 1)])
    return {"tiles": tiles, "scale": s, "cols": cols, "rows": len(bands), "small_h": round(small_h, 1)}


# ------------------------------------------------------------------ chuẩn bị một trang (như processed_page của web)
def chuan_bi_trang(img: Image.Image, prep: dict | None = None, xoay_tay: int = 0) -> tuple[Image.Image, dict]:
    """Ảnh trang (như lúc tải lên) -> (ảnh trang đã tiền xử lý tầng trang, thông tin).

    1. Nhận diện chiều chữ trên ảnh gốc và xoay cho chữ đứng thẳng (nếu prep["auto_orient"]); xoay_tay là số độ
       xoay thêm theo chiều kim đồng hồ do người dùng chỉnh, tính từ chỗ đã tự xoay.
    2. process_page: chỉnh nghiêng, cân bằng sáng, tìm dòng chữ, (tăng tương phản, lọc hoa văn).
    info: {"steps": [các bước đã làm], "text": {"lines", "line_h", "text_box"}, "orient": {...}, "size": [W, H]}."""
    from .doc_tep import apply_rotation
    prep = normalize_prep(prep)
    o = detect_orientation(img) if prep["auto_orient"] else {}
    ad = o.get("deg", 0)
    out, info = process_page(apply_rotation(img, (ad + xoay_tay) % 360), prep)
    if ad:
        info["steps"].insert(0, f"tự xoay {ad}° theo chiều chữ"
                                + (" (chưa chắc, nên xem lại)" if o.get("conf") == "thấp" else ""))
    info["orient"] = {**o, "applied": ad, "manual": xoay_tay % 360}
    return out, info


def tu_xoay(img: Image.Image, xoay_tay: int = 0) -> tuple[Image.Image, dict]:
    """Chỉ tự xoay theo chiều chữ, không làm các bước khác: (ảnh đã xoay cho chữ đứng thẳng, kết quả nhận diện).
    Kết quả: {"deg": góc đã xoay theo chiều kim đồng hồ (0/90/180/270), "conf": "cao" | "vừa" | "thấp", ...};
    "thấp" là chưa chắc, nên cho người xem lại. Trang không có dòng chữ rõ thì giữ nguyên (deg = 0)."""
    from .doc_tep import apply_rotation
    o = detect_orientation(img)
    return apply_rotation(img, (o["deg"] + xoay_tay) % 360), o
