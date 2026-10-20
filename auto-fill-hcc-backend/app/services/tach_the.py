"""Tách thẻ: một trang scan đặt NHIỀU thẻ (vd 2 CCCD một trên một dưới, giữa là khoảng trắng) → cắt riêng từng thẻ
rồi mới gửi OCR. Vintern chỉ đọc một vùng giấy tờ trên mỗi ảnh nên thẻ thứ hai bị bỏ qua, thẻ nhỏ trên trang lớn mất dấu.

Chỉ dùng OpenCV: tìm các khối không trắng có tỉ lệ cạnh như thẻ (85,6 × 54 mm ≈ 1,585). Trang có dưới 2 thẻ → giữ nguyên
tệp gốc, không đụng tới. Tìm thẻ MỘT lần (``cat``) rồi dùng chung cho nhánh Vintern (``tach``) và nhánh Qwen.
"""
from __future__ import annotations

import base64
import io
import threading
import time

import cv2
import numpy as np
from PIL import Image

from app.services.qwen_doc_giay import load_document as _load_document

_CANH_DAI_TIM = 900          # thu nhỏ trang để tìm khối cho nhanh
_TI_LE_THE = (1.3, 1.95)     # cạnh dài / cạnh ngắn của khối được coi là thẻ
_DIEN_TICH = (0.02, 0.6)     # diện tích khối / diện tích trang
_LE = 0.03                   # chừa lề quanh thẻ khi cắt (theo cạnh dài của thẻ)
# Thẻ (kể cả bản photo đen trắng) phủ kín mực/nền màu: đo 0,3–0,85; khối chữ của tờ khai, bản án chỉ 0,09–0,22.
_DO_PHU_THE = 0.3

# pypdfium2 không an toàn đa luồng: hai luồng cùng mở PDF làm crash cả tiến trình (không có traceback).
_KHOA_PDF = threading.Lock()


def load_document(data: bytes, name: str) -> list[Image.Image]:
    """Đọc tệp thành các trang ảnh qua khoá chung — mọi nhánh chạy song song phải đọc qua hàm này."""
    with _KHOA_PDF:
        return _load_document(data, name)


def file_bytes(f: dict) -> bytes:
    """Nội dung tệp từ ``bytes`` hoặc ``dataUrl`` (data:...;base64,...)."""
    if f.get("bytes"):
        return f["bytes"]
    url = str(f.get("dataUrl") or "")
    return base64.b64decode(url.split(",", 1)[1]) if "," in url else b""


def tim_the(img: Image.Image) -> list[tuple[int, int, int, int]]:
    """Các khung thẻ (x0, y0, x1, y1) trên ảnh gốc, xếp trên xuống dưới, trái sang phải."""
    W, H = img.size
    s = min(1.0, _CANH_DAI_TIM / max(W, H))
    g = cv2.cvtColor(np.asarray(img.convert("RGB").resize((max(1, int(W * s)), max(1, int(H * s))))),
                     cv2.COLOR_RGB2GRAY)
    ink = g < 225
    mask = ink.astype(np.uint8) * 255
    k = max(3, int(min(g.shape) * 0.02))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area = g.shape[0] * g.shape[1]
    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        ratio = max(w, h) / max(1, min(w, h))
        if not (_DIEN_TICH[0] <= (w * h) / area <= _DIEN_TICH[1] and _TI_LE_THE[0] <= ratio <= _TI_LE_THE[1]):
            continue
        if ink[y:y + h, x:x + w].mean() >= _DO_PHU_THE:
            le = _LE * max(w, h)
            boxes.append((max(0, int((x - le) / s)), max(0, int((y - le) / s)),
                          min(W, int((x + w + le) / s)), min(H, int((y + h + le) / s))))
    return sorted(boxes, key=lambda b: (b[1] // max(1, H // 10), b[0]))


def _data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def cat(files: list[dict]) -> tuple[list[list[tuple]], int]:
    """Đọc trang + tìm thẻ MỘT lần cho cả hồ sơ.
    → ([tệp][trang] = (ảnh trang, các khung thẻ — rỗng nếu trang có < 2 thẻ), ms)."""
    t0 = time.monotonic()
    out = []
    for f in files:
        try:
            trang = load_document(file_bytes(f), f.get("name") or "")
        except Exception:  # noqa: BLE001 — không đọc được trang thì để OCR tự xử lý tệp gốc
            trang = []
        out.append([(p, b if len(b) >= 2 else []) for p, b in ((p, tim_the(p)) for p in trang)])
    return out, int((time.monotonic() - t0) * 1000)


def tach(files: list[dict], da_cat: list[list[tuple]]) -> tuple[list[dict], list[list[int]], int]:
    """→ (danh sách ảnh/tệp gửi OCR, nhóm chỉ số của từng tệp gốc, số thẻ đã cắt).

    Tệp có ít nhất một trang chứa ≥ 2 thẻ: tách thành từng ảnh (thẻ đã cắt; trang ít thẻ giữ cả trang).
    Tệp khác giữ nguyên dict gốc để OCR như cũ (kể cả cache)."""
    out, groups, so_the = [], [], 0
    for f, tep in zip(files, da_cat):
        if not any(len(b) >= 2 for _, b in tep):
            groups.append([len(out)])
            out.append(f)
            continue
        idx = []
        for i, (p, boxes) in enumerate(tep, 1):
            parts = [p.crop(b) for b in boxes] if len(boxes) >= 2 else [p]
            so_the += len(boxes) if len(boxes) >= 2 else 0
            for k, part in enumerate(parts, 1):
                idx.append(len(out))
                out.append({"name": f"{f.get('name')}#trang{i}-phan{k}.jpg", "type": "image/jpeg",
                            "dataUrl": _data_url(part)})
        groups.append(idx)
    return out, groups, so_the


def gop_ket_qua(files: list[dict], results: list[dict], groups: list[list[int]]) -> list[dict]:
    """Nối chữ OCR các phần đã tách về đúng tệp gốc (để trích xuất như một tệp)."""
    merged = []
    for f, idx in zip(files, groups):
        if len(idx) == 1 and results[idx[0]].get("name") == f.get("name"):
            merged.append(results[idx[0]])
            continue
        texts = [results[i].get("text") or "" for i in idx]
        errors = [results[i].get("error") for i in idx if results[i].get("error")]
        provider = next((results[i].get("provider") for i in idx if results[i].get("provider")), None)
        item = {"name": f.get("name"), "type": f.get("type"), "provider": provider,
                "text": "\n\n".join(f"───── Phần {n}/{len(idx)} ─────\n{t}" if len(idx) > 1 else t
                                    for n, t in enumerate(texts, 1)).strip()}
        if errors and not item["text"]:
            item["error"] = "; ".join(errors)
        merged.append(item)
    return merged
