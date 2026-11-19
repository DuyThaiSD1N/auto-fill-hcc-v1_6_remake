"""Qwen đọc thẳng ẢNH Giấy đề nghị liên vận Việt Nam – Lào – Campuchia: bảng phương tiện mục 5, phường/xã mục 2, điện
thoại mục 3, ô đánh dấu mục 6, và số khung/số máy IN trên Giấy chứng nhận đăng ký xe.

Cùng lý do với bản Việt – Lào (`cap_giay_phep_lien_van_viet_lao.process.vision`): OCR văn bản làm rơi dấu ☑ trong ô kẻ và
lệch cột bảng viết tay. Dùng lại cắt ảnh / làm sạch hàng / ghép xe của bản đó, chỉ khác prompt (mục 5/6 của mẫu ba nước,
phương án c "Phục vụ hoạt động của tổ chức/cá nhân") và cách đọc mục đích. Lỗi → ``None`` (giữ kết quả OCR + LLM).
"""

import asyncio
import base64
import logging

from app.monitor import recorder as mon
from app.pipelines.cap_giay_phep_lien_van_viet_lao.process import vision as viet_lao
from app.pipelines.cap_giay_phep_lien_van_viet_lao_campuchia.process.mapper import muc_dich_key
from app.services import ocr_qwen
from app.services.llm.client import extract_json_block

logger = logging.getLogger(__name__)

_MAX_TOKENS = 1500
_TIMEOUT_S = 120
_PURPOSE_LABEL = {"mucdich_01": "Công vụ", "mucdich_02": "Cá nhân", "mucdich_03": "Hoạt động kinh doanh",
                  "mucdich_04": "Mục đích khác"}

PROMPT = """Bạn đọc ẢNH các trang hồ sơ xin "cấp, cấp lại giấy phép liên vận giữa Việt Nam, Lào và Campuchia". Chép đúng chữ
nhìn thấy, giữ dấu tiếng Việt. Ô trống hoặc không đọc được → "". Không suy đoán, không tính toán.

A. GIẤY ĐỀ NGHỊ (tiêu đề "GIẤY ĐỀ NGHỊ CẤP, CẤP LẠI GIẤY PHÉP LIÊN VẬN GIỮA VIỆT NAM, LÀO VÀ CAMPUCHIA…"):
1. "dia_chi" — CHỈ dòng "2. Địa chỉ": {"tinh": tỉnh/thành phố, "xa": phường/xã/thị trấn viết ĐẦY ĐỦ "Phường …"/"Xã …"/
   "Thị trấn …" (không viết tắt)}. Không ghi → "".
2. "dien_thoai" — dòng "3. Số điện thoại": chỉ chữ số.
3. "phuong_tien" — BẢNG mục 5, cột trái → phải: Số TT | Biển số xe | Trọng tải (ghế) | Năm sản xuất | Nhãn hiệu | Số khung |
   Số máy | Màu sơn | Thời gian đề nghị cấp phép | Cửa khẩu xuất - nhập cảnh. Dòng đánh số cột (A, B, 1, 2, …) dưới tiêu
   đề không phải dữ liệu.
   - Xác định cột theo vị trí ngang của chữ so với đường kẻ dọc, KHÔNG theo thứ tự xuất hiện.
   - Chữ xuống nhiều dòng trong CÙNG một ô → ghép lại; biển số ghép thành một (vd "92A-" + "123.45" → "92A-123.45"); số
     khung/số máy bỏ khoảng trắng.
   - "tuNgay"/"denNgay": ô thời gian ghi "ngày-ngày" → ngày trước là "tuNgay", ngày sau là "denNgay" (dd/mm/yyyy). Ô chỉ
     ghi số tháng → "".
   - Chỉ trả hàng có dữ liệu.
4. "muc_dich" — mục "6. Mục đích chuyến đi": a) Công vụ, b) Cá nhân, c) Phục vụ hoạt động của tổ chức/cá nhân, d) Mục đích
   khác; mỗi phương án có MỘT ô vuông NGAY SAU nhãn (hai phương án chung một hàng). Ô có dấu (☑, X, ✓, tô đen) là được
   chọn; ô rỗng (□) là không. Trả đúng MỘT chữ cái của phương án được chọn: "a" / "b" / "c" / "d". Không ô nào → "".
B. "giay_xe" — mỗi GIẤY CHỨNG NHẬN ĐĂNG KÝ XE là 1 phần tử: biển số, "Số khung (Chassis N°)", "Số máy (Engine N°)" — chữ
   IN trên giấy, bỏ khoảng trắng.

Trả DUY NHẤT một JSON, không giải thích:
{"dia_chi": {"tinh": "", "xa": ""}, "dien_thoai": "", "muc_dich": "",
 "phuong_tien": [{"bienSo": "", "trongTai": "", "namSanXuat": "", "nhanHieu": "", "soKhung": "", "soMay": "",
   "mauSon": "", "cuaKhau": "", "tuNgay": "", "denNgay": ""}],
 "giay_xe": [{"bienSo": "", "soKhung": "", "soMay": ""}]}
Không thấy Giấy đề nghị → "dia_chi" rỗng, "dien_thoai": "", "muc_dich": "", "phuong_tien": []. Không thấy giấy xe →
"giay_xe": []."""

_LETTER = {"a": "Công vụ", "b": "Cá nhân", "c": "Hoạt động kinh doanh", "d": "Mục đích khác"}


def purpose(value) -> str:
    """Chữ cái a–d (hoặc nhãn) → nhãn checkbox của form. Nhãn c) trên đơn có chữ "cá nhân" nên không dùng bản Việt – Lào."""
    text = str(value or "").strip().lower().strip(").")
    if text in _LETTER:
        return _LETTER[text]
    key = muc_dich_key(value)
    return _PURPOSE_LABEL[key] if key else ""


def parse(data: dict) -> dict | None:
    parsed = viet_lao.parse(data)
    if parsed is not None:
        parsed["purpose"] = purpose(data.get("muc_dich"))
    return parsed


async def read_application(files: list[dict]) -> dict | None:
    try:
        async with mon.span("llm.vision_lien_van_campuchia") as span:
            images = await asyncio.to_thread(viet_lao._page_images, files)
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
            mon.output("vision_lien_van_campuchia", data)
            parsed = parse(data or {})
            if parsed is None:
                raise ValueError("JSON không đúng khung phuong_tien")
            return parsed
    except Exception as exc:  # noqa: BLE001 — lỗi lượt phụ không được làm hỏng luồng chính
        logger.warning("Qwen đọc Giấy đề nghị liên vận Việt Nam – Lào – Campuchia lỗi, giữ kết quả OCR + LLM: %s", exc)
        return None
