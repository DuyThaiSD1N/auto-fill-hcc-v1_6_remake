"""API tờ khai đăng ký hộ kinh doanh cho cán bộ Auto Fill (tab riêng của extension).

Chỉ dựng file rồi trả về: không lưu dữ liệu đã điền, không tạo hồ sơ, không vào thống kê.
"""
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Response

from app.core.deps import require_auth
from app.pipelines.dang_ky_kinh_doanh.giay_de_nghi.fill import GiayDeNghi, to_docx
from app.pipelines.dang_ky_kinh_doanh.giay_de_nghi.pdf import to_pdf

router = APIRouter(prefix="/api/v1/ho-kinh-doanh/giay-de-nghi", tags=["giay-de-nghi-ho-kinh-doanh"])

_VN = timezone(timedelta(hours=7))
_NGANH_FILE = Path(__file__).parents[1] / "data" / "nganh_kinh_te_cap4.json"
_DON_VI = re.compile(r"^(Phường|Xã|Thị trấn|Đặc khu)\s+", re.IGNORECASE)
_MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


@lru_cache(maxsize=1)
def _nganh() -> list[dict]:
    """Ngành cấp 4 (Quyết định 36/2025/QĐ-TTg) để gợi ý mã. Bỏ phần nội dung: dài và trang không dùng."""
    data = json.loads(_NGANH_FILE.read_text(encoding="utf-8"))
    return [{"ma": item["ma"], "ten": item["ten"]} for item in data["nganh"]]


def _kinh_gui(user: dict) -> str:
    ward = (user.get("xa") or "").strip()
    if not ward:
        return ""
    return f"UBND {_DON_VI.sub(lambda m: m.group(1).lower() + ' ', ward)}"


def _dia_danh(user: dict) -> str:
    return _DON_VI.sub("", (user.get("xa") or "").strip())


@router.get("/config")
async def config(user: dict = Depends(require_auth)):
    return {
        "kinhGui": _kinh_gui(user),
        "diaDanh": _dia_danh(user),
        "today": datetime.now(_VN).strftime("%d/%m/%Y"),
        "nganh": _nganh(),
    }


class RenderReq(GiayDeNghi):
    format: Literal["docx", "pdf"]


def _slug(name: str) -> str:
    text = unicodedata.normalize("NFD", name or "").replace("Đ", "D").replace("đ", "d")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:40]


@router.post("/render")
async def render(body: RenderReq, _: dict = Depends(require_auth)):
    # `async def` có chủ đích: chạy trên event loop thay vì threadpool vì MuPDF không an toàn đa luồng.
    data = to_docx(body) if body.format == "docx" else to_pdf(body)
    name = _slug(body.tenViet) or _slug(body.hoTen)
    filename = f"Giay_de_nghi_dang_ky_ho_kinh_doanh{f'_{name}' if name else ''}.{body.format}"
    return Response(
        content=data, media_type=_MIME[body.format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )
