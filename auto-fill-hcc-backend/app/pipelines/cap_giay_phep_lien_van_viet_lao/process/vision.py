"""Qwen đọc thẳng ẢNH hồ sơ → bảng phương tiện + phường/xã, điện thoại trên Giấy đề nghị và số khung/số máy IN trên giấy xe.

OCR văn bản hay gộp ô viết tay nhiều dòng (số khung/số máy) làm cả hàng lệch cột, đọc sai dòng địa chỉ viết tay, và
đọc sai cả chữ in trên nền hoa văn của giấy kiểm định. Model đa phương thức thấy đường kẻ cột và nét chữ nên đọc riêng
các phần này. Runner gọi song song với OCR + LLM; trả ``None`` khi lỗi/không parse được để giữ kết quả cũ.
"""

import asyncio
import base64
import json
import logging
import re
from contextlib import ExitStack

import fitz  # PyMuPDF

from app.monitor import recorder as mon
from app.services import ocr_qwen
from app.services.llm.client import extract_json_block
from app.services.ocr_tiengnoi import _open_input

logger = logging.getLogger(__name__)

_MAX_SIDE_PX = 1600
_JPEG_QUALITY = 85
# Giấy đề nghị + giấy xe nằm đầu hồ sơ; chặn trần để hồ sơ dài không làm chậm lượt đọc.
_MAX_PAGES = 6
_MAX_TOKENS = 1500
_TIMEOUT_S = 120

# Địa chỉ chi tiết viết tay: thử trên hồ sơ thật model đọc ra chữ không có trên giấy → không lấy từ lượt này.
ROW_KEYS = ("bienSo", "trongTai", "namSanXuat", "nhanHieu", "soKhung", "soMay", "mauSon", "hinhThucHoatDong",
            "cuaKhau", "tuNgay", "denNgay")
CERT_KEYS = ("bienSo", "soKhung", "soMay")
AREA_KEYS = ("tinh", "xa")

PROMPT = """Bạn đọc ẢNH các trang hồ sơ xin "cấp, cấp lại giấy phép liên vận giữa Việt Nam và Lào". Chép đúng chữ nhìn
thấy, giữ dấu tiếng Việt. Ô trống hoặc không đọc được → "". Không suy đoán, không tính toán.

A. GIẤY ĐỀ NGHỊ (mẫu có tiêu đề "GIẤY ĐỀ NGHỊ cấp, cấp lại giấy phép liên vận…"):
1. "dia_chi" — CHỈ dòng "2. Địa chỉ" viết tay trên Giấy đề nghị (KHÔNG lấy địa chỉ trên giấy xe): {"tinh":
   tỉnh/thành phố, "xa": phường/xã/thị trấn viết ĐẦY ĐỦ "Phường …"/"Xã …" (không viết tắt "P."/"X.")}. Không ghi → "".
2. "dien_thoai" — dòng "3. Số điện thoại": chỉ chữ số.
3. "phuong_tien" — BẢNG mục 4, cột trái → phải: Số TT | Biển số xe | Trọng tải (ghế) | Năm sản xuất | Nhãn hiệu |
   Số khung | Số máy | Màu sơn | Thời gian đề nghị cấp phép | Hình thức hoạt động | Cửa khẩu Xuất - nhập. Dòng đánh
   số cột (A, B, 1, 2, …) dưới tiêu đề không phải dữ liệu.
   - Xác định cột theo vị trí ngang của chữ so với đường kẻ dọc, KHÔNG theo thứ tự xuất hiện.
   - Chữ viết xuống nhiều dòng trong CÙNG một ô → ghép lại; số khung/số máy bỏ khoảng trắng giữa các đoạn.
   - "tuNgay"/"denNgay": chỉ khi ô thời gian ghi NGÀY cụ thể — ngày viết trước/dòng trên là "tuNgay", ngày viết
     sau/dòng dưới là "denNgay" (dd/mm/yyyy). Ô chỉ ghi số tháng → để "".
   - Chỉ trả hàng có dữ liệu; hàng chỉ có số thứ tự → bỏ.
B. "giay_xe" — mỗi GIẤY CHỨNG NHẬN ĐĂNG KÝ XE (cà vẹt) và mỗi CHỨNG NHẬN KIỂM ĐỊNH (đăng kiểm) là 1 phần tử:
   biển số, "Số khung (Chassis N°)", "Số máy / Số động cơ (Engine N°)" — chữ IN trên giấy, chép đủ từng ký tự,
   bỏ khoảng trắng.

Trả DUY NHẤT một JSON, không giải thích:
{"dia_chi": {"tinh": "", "xa": ""}, "dien_thoai": "",
 "phuong_tien": [{"bienSo": "", "trongTai": "", "namSanXuat": "", "nhanHieu": "", "soKhung": "", "soMay": "",
   "mauSon": "", "hinhThucHoatDong": "", "cuaKhau": "", "tuNgay": "", "denNgay": ""}],
 "giay_xe": [{"bienSo": "", "soKhung": "", "soMay": ""}]}
Không thấy Giấy đề nghị → "dia_chi" rỗng, "dien_thoai": "", "phuong_tien": []. Không thấy giấy xe → "giay_xe": []."""


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


def _clean_rows(rows, keys: tuple[str, ...]) -> list[dict]:
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        clean = {k: str(row.get(k) or "").strip() for k in keys}
        for k in ("soKhung", "soMay"):
            clean[k] = re.sub(r"\s+", "", clean.get(k, ""))
        if any(clean.values()):
            out.append({k: v for k, v in clean.items() if v})
    return out


def parse(data: dict) -> dict | None:
    """JSON model → {rows, certs, area, phone}. Thiếu khung → None (coi như không đọc được)."""
    if not isinstance(data, dict) or not isinstance(data.get("phuong_tien"), list):
        return None
    area = data.get("dia_chi") if isinstance(data.get("dia_chi"), dict) else {}
    area = {k: str(area.get(k) or "").strip() for k in AREA_KEYS}
    return {
        "rows": _clean_rows(data.get("phuong_tien"), ROW_KEYS),
        "certs": _clean_rows(data.get("giay_xe"), CERT_KEYS),
        "area": {k: v for k, v in area.items() if v},
        "phone": re.sub(r"\D", "", str(data.get("dien_thoai") or "")),
    }


async def read_application(files: list[dict]) -> dict | None:
    try:
        async with mon.span("llm.vision_lien_van") as span:
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
            mon.output("vision_lien_van", data)
            parsed = parse(data or {})
            if parsed is None:
                raise ValueError("JSON không đúng khung phuong_tien")
            return parsed
    except Exception as exc:  # noqa: BLE001 — lỗi lượt phụ không được làm hỏng luồng chính
        logger.warning("Qwen đọc Giấy đề nghị liên vận lỗi, giữ kết quả OCR + LLM: %s", exc)
        return None


def _plate_key(car: dict) -> str:
    return re.sub(r"[^0-9A-Z]", "", str(car.get("bienSo") or "").upper())


def _as_list(value) -> list[dict]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []
    if isinstance(value, dict):
        value = [value]
    return [dict(v) for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _match(items: list[dict], car: dict, index: int, total: int) -> list[dict]:
    """Khớp theo biển số; biển OCR lệch thì ghép theo thứ tự khi số xe bằng nhau / chỉ có 1 xe."""
    key = _plate_key(car)
    same = [i for i in items if key and _plate_key(i) == key]
    if same:
        return same
    if total == 1:
        return items
    return [items[index]] if len(items) == total else []


def _first(items: list[dict], key: str) -> str:
    return next((i[key] for i in items if i.get(key)), "")


# Bảng ảnh THẮNG ở các cột người dân khai mà OCR văn bản hay lệch: màu sơn (giấy xe hay cắt góc đúng ô này), số
# khung/số máy cột tờ khai. Cột chọn theo option cổng (hình thức hoạt động) giữ LLM đã chuẩn hoá; ô khác bảng ảnh
# chỉ bù khi LLM bỏ trống.
_ROW_WINS = ("mauSon", "soKhung", "soMay")
_ROW_NEVER = ("hinhThucHoatDong", "tuNgay", "denNgay")
_DATE_KEYS = ("tuNgay", "denNgay")
_DATE_LABEL = {"tuNgay": "từ ngày", "denNgay": "đến ngày"}


def _norm_date(value) -> str:
    m = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", str(value or ""))
    return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}" if m else ""


def merge_vehicles(llm_value, parsed: dict | None) -> tuple[list[dict], list[str]]:
    cars = _as_list(llm_value)
    warnings: list[str] = []
    if not parsed:
        return cars, warnings
    rows, certs = parsed.get("rows") or [], parsed.get("certs") or []
    if not cars:
        cars = [{k: v for k, v in r.items() if k not in _ROW_NEVER} for r in rows]
    total = len(cars)
    out = []
    for index, car in enumerate(cars):
        merged = dict(car)
        row = (_match(rows, car, index, total) or [None])[0]
        if row:
            for key, value in row.items():
                if key in _ROW_NEVER:
                    continue
                if key in _ROW_WINS or not merged.get(key):
                    merged[key] = value
            # Ngày viết tay: cả OCR + LLM lẫn đọc ảnh đều có lúc ra ngày không có trên giấy → chỉ giữ khi hai lượt
            # đọc khớp nhau, lệch thì bỏ trống + cảnh báo.
            for key in _DATE_KEYS:
                llm_date, row_date = _norm_date(merged.get(key)), _norm_date(row.get(key))
                if llm_date and llm_date == row_date:
                    merged[key] = llm_date
                    continue
                if llm_date or row_date:
                    warnings.append(f"Không chắc {_DATE_LABEL[key]} cấp phép của xe {car.get('bienSo') or index + 1} — "
                                    "đã để trống, đối chiếu Giấy đề nghị.")
                merged.pop(key, None)
        # Số khung/số máy IN trên cà vẹt/giấy kiểm định: Qwen đọc ảnh > LLM đọc OCR (mapper ưu tiên khoá *DangKy).
        matched_certs = _match(certs, car, index, total)
        for key in ("soKhung", "soMay"):
            printed = _first(matched_certs, key)
            if printed:
                merged[f"{key}DangKy"] = printed
        out.append(merged)
    return out, warnings
