# -*- coding: utf-8 -*-
"""Chuẩn bị các ảnh gửi model cho một trang và đóng gói nội dung yêu cầu.

Mỗi trang (khi không cắt) được gửi kèm:
  1. một ảnh toàn trang để model nắm bố cục;
  2. các dải chữ phóng to (chế độ "auto": dải theo dòng chữ tìm được, phóng sao cho chữ nhỏ cao khoảng 36 px;
     "2x2"/"3x3": lưới cố định; "off": chỉ ảnh toàn trang), tối đa max_images ảnh mỗi lần gửi.
Mỗi ảnh có một dòng chú thích (trang mấy, vùng nào, phóng bao nhiêu) đặt ngay trước ảnh.
Ảnh mã hóa PNG (giữ nguyên điểm ảnh) hoặc JPEG chất lượng 92 (nhẹ hơn 2-3 lần, gửi qua mạng nhanh hơn).

Trích nguyên văn từ ocr_engine.py của web.
"""
from __future__ import annotations

import base64
import io
import math
from dataclasses import dataclass, field

from PIL import Image

from . import tien_xu_ly as tx


# ---------------------------------------------------------------- cấu hình model
PATCH = 28  # ô 28x28 px: dùng để tính giới hạn số điểm ảnh mỗi ảnh (image_mp) và ước tính token hình


REQUEST_IMAGE_BUDGET = 24 * 1024**2  # tổng base64 của ảnh trong 1 request (giới hạn 32 MB)


MAX_IMAGE_B64 = int(9.5 * 1024**2)   # mỗi ảnh tối đa 10 MB base64


def visual_tokens(w: int, h: int) -> int:
    return math.ceil(w / PATCH) * math.ceil(h / PATCH)


def fit_scale(w: int, h: int, spec: dict, max_up: float = 1.0) -> float:
    """Hệ số phóng/thu lớn nhất (<= max_up) để ảnh vừa giới hạn, API không phải thu nhỏ thêm."""
    def ok(s: float) -> bool:
        W, H = max(1, round(w * s)), max(1, round(h * s))
        return max(W, H) <= spec["long_edge"] and visual_tokens(W, H) <= spec["max_tokens"]

    if ok(max_up):
        return max_up
    lo, hi = 0.0, max_up
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return lo


def resize_by(img: Image.Image, s: float) -> Image.Image:
    if abs(s - 1.0) < 1e-3:
        return img
    W, H = max(1, round(img.width * s)), max(1, round(img.height * s))
    return img.resize((W, H), Image.LANCZOS)


def grid_for(img: Image.Image, zoom: str) -> tuple[int, int]:
    """Số hàng x cột của lưới phóng to."""
    if zoom in ("off", "0", "", None):
        return (0, 0)
    if zoom == "2x2":
        return (2, 2)
    if zoom == "3x3":
        return (3, 3)
    # tự động: ảnh lớn (trên ~14 MP) chia 3x3, còn lại 2x2
    mp = img.width * img.height / 1e6
    n = 3 if mp > 14 else 2
    ratio = img.width / img.height
    if ratio > 1.9:      # ảnh rất ngang: thêm cột
        return (max(1, n - 1), n + 1)
    if ratio < 1 / 1.9:  # ảnh rất dọc: thêm hàng
        return (n + 1, max(1, n - 1))
    return (n, n)


def tile_boxes(w: int, h: int, rows: int, cols: int, overlap: float = 0.12):
    tw, th = w / cols, h / rows
    ox, oy = tw * overlap, th * overlap
    boxes = []
    for r in range(rows):
        for c in range(cols):
            x0 = max(0, int(c * tw - ox))
            y0 = max(0, int(r * th - oy))
            x1 = min(w, int(math.ceil((c + 1) * tw + ox)))
            y1 = min(h, int(math.ceil((r + 1) * th + oy)))
            boxes.append((r, c, (x0, y0, x1, y1)))
    return boxes


def _position_name(r: int, c: int, rows: int, cols: int) -> str:
    vert = {1: ["giữa"], 2: ["trên", "dưới"], 3: ["trên", "giữa", "dưới"]}
    horz = {1: ["giữa"], 2: ["trái", "phải"], 3: ["trái", "giữa", "phải"]}
    v = vert.get(rows, [f"hàng {i+1}" for i in range(rows)])[r]
    h = horz.get(cols, [f"cột {i+1}" for i in range(cols)])[c]
    return f"phần {v} {h}".replace("giữa giữa", "chính giữa")


@dataclass
class Shot:
    caption: str
    img: Image.Image


@dataclass
class PreparedRequest:
    content: list = field(default_factory=list)
    image_count: int = 0
    visual_tokens: int = 0
    shots: list = field(default_factory=list)


def limit_grid(rows: int, cols: int, max_images: int) -> tuple[int, int]:
    """Thu nhỏ lưới vùng phóng to để 1 ảnh toàn trang + các vùng không vượt số ảnh máy chủ cho phép."""
    while rows * cols > 1 and rows * cols + 1 > max_images:
        if rows >= cols:
            rows -= 1
        else:
            cols -= 1
    if rows * cols <= 1:
        return (0, 0)
    return (rows, cols)


def _grid_boxes(W: int, H: int, zoom: str, img_for_grid: Image.Image, max_images: int | None):
    rows, cols = grid_for(img_for_grid, "auto" if zoom in ("auto", "smart") else zoom)
    if max_images:
        rows, cols = limit_grid(rows, cols, max_images)
    if rows * cols <= 1:
        return [], 0, 0
    return [(r, c, box) for r, c, box in tile_boxes(W, H, rows, cols)], rows, cols


def plan_page(img: Image.Image, zoom: str, spec: dict, max_images: int | None, text: dict | None) -> dict:
    """Quyết định sẽ gửi những vùng nào của trang (dùng chung cho việc đọc và cho lớp hiển thị vùng chữ)."""
    W, H = img.size
    so = fit_scale(W, H, spec, max_up=2.0)
    cap = min((max_images or 20) - 1, 9)
    plan = {"overview_scale": so, "mode": "off", "tiles": []}
    if zoom == "off" or cap < 1:
        return plan
    if zoom in ("auto", "smart") and text:
        fit = lambda w, h, up: fit_scale(w, h, spec, max_up=up)
        p = tx.plan_text_tiles(W, H, text, fit, max_tiles=cap)
        if p and p["tiles"]:
            n = len(p["tiles"])
            for k, b in enumerate(p["tiles"]):
                x0, y0, x1, y1 = b
                where = f"khoảng {round(100 * y0 / H)}–{round(100 * y1 / H)}% chiều dọc trang"
                if p["cols"] > 1:
                    c = k % p["cols"]
                    where += ", " + (["phần trái", "phần phải"] if p["cols"] == 2 else ["phần trái", "phần giữa", "phần phải"])[c]
                s = min(p["scale"], fit_scale(x1 - x0, y1 - y0, spec, max_up=4.0))
                plan["tiles"].append({"box": [x0, y0, x1, y1], "scale": s,
                                      "caption": f"dải chữ {k + 1}/{n} ({where}), phóng ×{s / max(so, 1e-6):.1f} so với ảnh toàn trang"})
            plan["mode"] = "text"
            return plan
    boxes, rows, cols = _grid_boxes(W, H, zoom, img, (cap + 1) if max_images else None)
    for r, c, box in boxes:
        x0, y0, x1, y1 = box
        s = fit_scale(x1 - x0, y1 - y0, spec, max_up=3.0)
        plan["tiles"].append({"box": list(box), "scale": s,
                              "caption": f"vùng phóng to {_position_name(r, c, rows, cols)} (hàng {r + 1}/{rows}, cột {c + 1}/{cols}), "
                                         f"phóng ×{s / max(so, 1e-6):.1f} so với ảnh toàn trang"})
    plan["mode"] = "grid" if boxes else "off"
    return plan


def page_shots(img: Image.Image, page_label: str, zoom: str, spec: dict, prep: dict | None = None,
               max_images: int | None = None, text: dict | None = None, plan: dict | None = None) -> list[Shot]:
    """img là trang đã qua tiền xử lý tầng trang. Tạo ảnh toàn trang + các vùng phóng to đã lọc tầng vùng."""
    prep = tx.normalize_prep(prep)
    plan = plan or plan_page(img, zoom, spec, max_images, text)
    bgr = tx.to_bgr(img)
    ov_prep = dict(prep, denoise=False, binarize=False)
    shots = [Shot(f"{page_label}: ảnh toàn trang (để nắm bố cục)", tx.to_pil(tx.finish_tile(bgr, ov_prep, plan["overview_scale"])))]
    for t in plan["tiles"]:
        x0, y0, x1, y1 = (int(round(v)) for v in t["box"])
        crop = bgr[max(0, y0):max(y0 + 1, y1), max(0, x0):max(x0 + 1, x1)]
        shots.append(Shot(f"{page_label}: {t['caption']}", tx.to_pil(tx.finish_tile(crop, prep, t["scale"]))))
    return shots


# ---------------------------------------------------------------- mã hóa ảnh gửi API
def _b64len(n: int) -> int:
    return 4 * math.ceil(n / 3)


def encode_image(img: Image.Image, budget: int, fmt: str = "png") -> tuple[str, str]:
    """PNG (không mất chi tiết) nếu vừa ngân sách, nếu không thì JPEG chất lượng cao.
    fmt="jpeg": luôn JPEG chất lượng 92, nhẹ hơn PNG 2-3 lần nên gửi qua mạng nhanh hơn."""
    # ảnh chụp/scan thường nén PNG còn ~20-60% dung lượng thô; chỉ thử PNG khi có khả năng vừa
    if fmt != "jpeg" and img.width * img.height * 3 * 0.25 <= budget * 3 // 4:
        buf = io.BytesIO()
        img.save(buf, format="PNG", compress_level=3)
        if _b64len(buf.tell()) <= budget:
            return "image/png", base64.b64encode(buf.getvalue()).decode()
    data = b""
    for q in (92, 88, 84, 78, 70, 60) if fmt == "jpeg" else (95, 92, 88, 84, 78, 70, 60):
        buf = io.BytesIO()
        try:
            img.save(buf, format="JPEG", quality=q, subsampling=0 if q >= 88 else 2, optimize=True)
        except OSError:
            # optimize với q < 95 Pillow chỉ cấp bộ đệm w×h byte; ảnh nhiều chi tiết, không lấy mẫu màu thì tràn
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=q, subsampling=0 if q >= 88 else 2)
        data = buf.getvalue()
        if _b64len(len(data)) <= budget:
            break
    return "image/jpeg", base64.b64encode(data).decode()


def build_content(shots: list[Shot], closing_text: str, fmt: str = "png") -> PreparedRequest:
    req = PreparedRequest(shots=shots)
    per_image = min(MAX_IMAGE_B64, REQUEST_IMAGE_BUDGET // max(1, len(shots)))
    for shot in shots:
        media, b64 = encode_image(shot.img, per_image, fmt)
        req.content.append({"type": "text", "text": shot.caption})
        req.content.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}})
        req.image_count += 1
        req.visual_tokens += visual_tokens(*shot.img.size)
    req.content.append({"type": "text", "text": closing_text})
    return req


def openai_spec(max_mp: float, long_edge: int, label: str) -> dict:
    """Giới hạn kích thước mỗi ảnh gửi lên máy chủ riêng (tính theo ô 28x28 như model Qwen)."""
    return {"label": label, "long_edge": int(long_edge), "max_tokens": max(64, int(float(max_mp) * 1e6 / (PATCH * PATCH)))}


def to_openai_content(content: list) -> list:
    out = []
    for b in content:
        if b["type"] == "text":
            out.append({"type": "text", "text": b["text"]})
        elif b["type"] == "image":
            src = b["source"]
            out.append({"type": "image_url", "image_url": {"url": f"data:{src['media_type']};base64,{src['data']}"}})
    return out
