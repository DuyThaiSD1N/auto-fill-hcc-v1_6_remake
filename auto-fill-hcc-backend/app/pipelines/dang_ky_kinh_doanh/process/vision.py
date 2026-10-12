"""Lượt DỰ PHÒNG: Qwen đọc thẳng ẢNH Giấy đề nghị đăng ký hộ kinh doanh → JSON số định danh, điện thoại, vốn, bảng ngành.

Đo trên 20 hồ sơ thật: OCR Vintern đọc tổng thể đúng hơn (nhất là dấu tên và ngày sinh) nhưng khi hỏng thì hỏng kiểu DỄ
PHÁT HIỆN — số định danh 11/13 số, điện thoại 9 số, bảng ngành vỡ thành chuỗi lặp, mất vốn. Qwen đọc bảng/dãy số dài tốt
hơn nhưng khi sai là nhầm chữ số mà vẫn đúng độ dài (khó phát hiện). Vì vậy chỉ gọi lượt này khi kết quả OCR + LLM có
dấu hiệu hỏng, và chỉ thay ĐÚNG trường hỏng bằng giá trị qua được kiểm tra định dạng.
"""

import asyncio
import base64
import logging
import re
from contextlib import ExitStack
from typing import Any

import fitz  # PyMuPDF

from app.monitor import recorder as mon
from app.services import ocr_qwen
from app.services.llm.client import extract_json_block
from app.services.ocr_tiengnoi import _open_input

logger = logging.getLogger(__name__)

_MAX_SIDE_PX = 1600
_JPEG_QUALITY = 85
# Giấy đề nghị 4 trang nằm đầu hồ sơ; chặn trần để CCCD/giấy tờ kèm theo không làm chậm lượt đọc.
_MAX_PAGES = 6
_MAX_TOKENS = 1200
_TIMEOUT_S = 120

PROMPT = """Bạn đọc ẢNH các trang của "GIẤY ĐỀ NGHỊ ĐĂNG KÝ HỘ KINH DOANH" (thường viết tay). Bỏ qua mọi giấy tờ khác.
Chép đúng chữ/số NHÌN THẤY, so từng chữ số. Ô trống hoặc không đọc được → "". Không suy đoán, không tra cứu.

- "so_dinh_danh": số giấy tờ của người đề nghị (chủ hộ) ở đầu đơn — dòng "Số định danh cá nhân" (mẫu mới) hoặc
  "Số giấy tờ pháp lý của cá nhân" (mẫu cũ) — chỉ chữ số.
- "dien_thoai": dòng "Điện thoại" ở đầu đơn — chỉ chữ số.
- "von": mục "4. Vốn kinh doanh — Tổng số" — chỉ chữ số, đơn vị đồng (dòng chữ "bằng chữ" dùng để đối chiếu).
- "so_lao_dong": mục "5.3 Tổng số lao động" — chỉ chữ số.
- "phuong_phap_thue": ô được đánh dấu ở mục "5.4 Phương pháp tính thuế GTGT" — "Phương pháp kê khai" hoặc
  "Phương pháp khoán"; không ô nào được đánh dấu → "".
- "nganh_nghe": bảng "3. Ngành, nghề kinh doanh", mỗi dòng có ghi dữ liệu là 1 phần tử:
  "ten" = cột Tên ngành; "ma" = cột Mã ngành (CHỈ chữ số ghi trên giấy — ô mã để trống thì "", KHÔNG tự tra mã
  theo tên ngành); "chinh" = true nếu dòng đó được đánh dấu (✓, X) ở cột "Ngành, nghề kinh doanh chính".
  Xác định cột theo vị trí ngang so với đường kẻ dọc, chữ viết xuống nhiều dòng trong cùng ô → ghép lại.

Trả DUY NHẤT một JSON, không giải thích:
{"so_dinh_danh": "", "dien_thoai": "", "von": "", "so_lao_dong": "", "phuong_phap_thue": "",
 "nganh_nghe": [{"ten": "", "ma": "", "chinh": false}]}"""


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _rows(value: Any) -> list[dict]:
    if isinstance(value, str):
        import json

        try:
            value = json.loads(value)
        except ValueError:
            return []
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _codes(rows: list[dict]) -> list[str]:
    return [c for c in (_digits(r.get("ma")) for r in rows) if len(c) == 4]


# OCR văn bản gặp bảng viết tay khó đọc hay rơi vào vòng lặp sinh chữ ("Bản tê-tô-Bản tê-tô-…"): một đoạn có chữ cái
# lặp liền nhau ≥6 lần. Dòng chấm/gạch điền tay ("……", "___") không có chữ cái nên không tính.
_LOOP_RE = re.compile(r"(.{4,40}?)\1{5,}", re.DOTALL)


def _has_ocr_loop(text: str) -> bool:
    return any(re.search(r"[^\W\d_]", m.group(1)) for m in _LOOP_RE.finditer(text or ""))


def broken_fields(values: dict, ocr_text: str = "") -> set[str]:
    """Dấu hiệu OCR + LLM đọc hỏng (sai độ dài / mất dữ liệu / OCR lặp vòng) — không đoán đúng sai theo nội dung."""
    broken = set()
    if _has_ocr_loop(ocr_text):
        broken.add("NganhNghe_DanhSach")
    if len(_digits(values.get("ChuHo_SoDinhDanh"))) != 12:
        broken.add("ChuHo_SoDinhDanh")
    phone = _digits(values.get("ChuHo_DienThoai"))
    if phone and len(phone) != 10:
        broken.add("ChuHo_DienThoai")
    if not _codes(_rows(values.get("NganhNghe_DanhSach"))):
        broken.add("NganhNghe_DanhSach")
    if not _digits(values.get("Von_SoTien")):
        broken.add("Von_SoTien")
    return broken


def _page_images(files: list[dict]) -> list[bytes]:
    images: list[bytes] = []
    for f in files:
        name = str(f.get("name") or "").lower()
        if name.endswith(".docx") or "wordprocessingml" in str(f.get("type") or ""):
            continue
        with ExitStack() as stack:
            _, src, mime = _open_input(f, stack)
            raw = src if isinstance(src, bytes) else src.read()
        filetype = "pdf" if "pdf" in mime else (mime.split("/")[-1] or None)
        doc = fitz.open(stream=raw, filetype=filetype)
        for page in doc:
            if len(images) >= _MAX_PAGES:
                return images
            zoom = min(_MAX_SIDE_PX / max(page.rect.width, page.rect.height), 3.0)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            images.append(pix.tobytes("jpeg", jpg_quality=_JPEG_QUALITY))
    return images


async def read_application(files: list[dict]) -> dict | None:
    try:
        async with mon.span("llm.vision_hkd_du_phong") as span:
            images = await asyncio.to_thread(_page_images, files)
            if not images:
                return None
            content = [{"type": "text", "text": PROMPT}] + [
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(b).decode()}}
                for b in images
            ]
            res = await ocr_qwen.chat(
                [{"role": "user", "content": content}],
                max_tokens=_MAX_TOKENS,
                timeout_s=_TIMEOUT_S,
                ocr_server=True,
            )
            span.attrs["pages"] = len(images)
            span.attrs["usage"] = res.get("usage")
            if res.get("finish_reason") == "length":
                raise ValueError("JSON bị cắt (chạm max_tokens)")
            data = extract_json_block(res.get("content") or "")
            mon.output("vision_hkd_du_phong", data)
            if not isinstance(data, dict):
                raise ValueError("Không parse được JSON")
            return data
    except Exception as exc:  # noqa: BLE001 — lỗi lượt phụ không được làm hỏng luồng chính
        logger.warning("Qwen đọc dự phòng Giấy đề nghị HKD lỗi, giữ kết quả OCR + LLM: %s", exc)
        return None


def patch(fields: list[dict], broken: set[str], data: dict) -> list[str]:
    """Thay ĐÚNG các trường hỏng bằng giá trị đọc ảnh qua được kiểm tra định dạng. Trả tên trường đã thay."""
    values = {f.get("name"): f.get("value") for f in fields}
    updates: dict[str, Any] = {}
    if "ChuHo_SoDinhDanh" in broken and len(_digits(data.get("so_dinh_danh"))) == 12:
        new_id = _digits(data.get("so_dinh_danh"))
        updates["ChuHo_SoDinhDanh"] = new_id
        # Người nộp = chủ hộ đọc cùng dòng hỏng → sửa theo.
        if _digits(values.get("NguoiNop_SoDinhDanh")) == _digits(values.get("ChuHo_SoDinhDanh")):
            updates["NguoiNop_SoDinhDanh"] = new_id
    if "ChuHo_DienThoai" in broken and len(_digits(data.get("dien_thoai"))) == 10:
        new_phone = _digits(data.get("dien_thoai"))
        updates["ChuHo_DienThoai"] = new_phone
        if _digits(values.get("TruSo_DienThoai")) == _digits(values.get("ChuHo_DienThoai")):
            updates["TruSo_DienThoai"] = new_phone
    if "Von_SoTien" in broken and _digits(data.get("von")):
        updates["Von_SoTien"] = _digits(data.get("von"))
    if "NganhNghe_DanhSach" in broken:
        rows = [r for r in _rows(data.get("nganh_nghe")) if str(r.get("ten") or "").strip() or _digits(r.get("ma"))]
        # Chỉ thay khi đọc ảnh ra NHIỀU mã hợp lệ hơn: OCR lặp vòng có thể nằm ngoài bảng ngành, bảng cũ vẫn tốt.
        if len(_codes(rows)) > len(_codes(_rows(values.get("NganhNghe_DanhSach")))):
            clean = [{"ma": _digits(r.get("ma")), "ten": str(r.get("ten") or "").strip(), "chinh": r.get("chinh") is True}
                     for r in rows]
            updates["NganhNghe_DanhSach"] = clean
            main = next((r for r in clean if r["chinh"] and len(r["ma"]) == 4), None)
            if main:
                updates["NganhNghe_MaChinh"] = main["ma"]
                updates["NganhNghe_TenChinh"] = main["ten"]
            elif _digits(values.get("NganhNghe_MaChinh")) not in _codes(clean):
                # Ngành chính cũ đọc từ bảng vỡ, không còn trong bảng mới → bỏ, không giữ mã sai.
                updates["NganhNghe_MaChinh"] = ""
                updates["NganhNghe_TenChinh"] = ""
    # OCR lặp vòng ở bảng ngành nuốt luôn phần sau của trang (mục 5): đã đọc ảnh thì bù các ô LLM để trống.
    if not _digits(values.get("Thue_SoLaoDong")) and _digits(data.get("so_lao_dong")):
        updates["Thue_SoLaoDong"] = _digits(data.get("so_lao_dong"))
    method = str(data.get("phuong_phap_thue") or "").strip()
    if not values.get("Thue_PhuongPhapTinh") and method in ("Phương pháp kê khai", "Phương pháp khoán"):
        updates["Thue_PhuongPhapTinh"] = method
    for name, value in updates.items():
        field = next((f for f in fields if f.get("name") == name), None)
        if field:
            field["value"] = value
        else:
            fields.append({"name": name, "comp": "raw", "value": value})
    return sorted(updates)
