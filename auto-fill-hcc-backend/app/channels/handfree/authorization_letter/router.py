"""API tạo giấy ủy quyền tại quầy (tab riêng của extension Handfree).

Ảnh đi qua phiên tải ảnh dùng chung (`/api/v1/upload-sessions`): chọn tệp, QR điện thoại và
máy quét tại quầy cùng đổ vào một phiên. Ở đây chỉ: đọc ảnh → danh sách người, dựng file, xoá phiên.
Không lưu dữ liệu đã điền, không tạo hồ sơ, không vào thống kê.
"""
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from app.channels.handfree.authorization_letter import render
from app.channels.handfree.authorization_letter.extract import extract_people
from app.core.deps import require_auth
from app.core.errors import AppError
from app.upload_session import store as up_store

router = APIRouter(prefix="/api/v1/assistant/authorization-letter", tags=["authorization-letter"])

# Chip gợi ý nội dung — BE giữ để sửa danh sách không phải phát hành extension. Extension dựng câu
# "Thay mặt tôi <chip> tại <nơi lập>." rồi cán bộ sửa lại cho đúng việc.
SUGGESTIONS = (
    "Nộp hồ sơ và nhận kết quả thủ tục hành chính",
    "Nhận bản sao trích lục hộ tịch",
    "Chứng thực bản sao từ bản chính",
    "Nhận lương hưu, trợ cấp bảo hiểm xã hội",
)
_VN = timezone(timedelta(hours=7))
_UNIT_PREFIX = re.compile(r"^(Phường|Xã|Thị trấn|Đặc khu|Tỉnh|Thành phố)\b")


def _lower_unit(name: str) -> str:
    """"Phường Vũ Ninh" → "phường Vũ Ninh" — trong câu văn tiền tố đơn vị viết thường."""
    name = (name or "").strip()
    return _UNIT_PREFIX.sub(lambda m: m.group(1).lower(), name)


def default_place(user: dict) -> str:
    ward, province = _lower_unit(user.get("xa") or ""), _lower_unit(user.get("tinh") or "")
    if not ward:
        return ""
    return f"UBND {ward}" + (f", {province}" if province else "")


@router.get("/config")
async def config(user: dict = Depends(require_auth)):
    return {
        "suggestions": list(SUGGESTIONS),
        "place": default_place(user),
        "today": datetime.now(_VN).strftime("%d/%m/%Y"),
    }


async def _owned_session(sid: str, user: dict) -> dict:
    """Chỉ tài khoản tạo phiên — capability của điện thoại được tải ảnh lên, không được đọc/xoá."""
    sess = await up_store.get(sid)
    if not sess:
        raise AppError("UPLOAD_SESSION_NOT_FOUND", "Phiên tải ảnh không tồn tại hoặc đã hết hạn", 404)
    if str(sess.get("owner_user_id") or "") != str(user.get("id") or ""):
        raise AppError("UPLOAD_SESSION_FORBIDDEN", "Tài khoản không có quyền với phiên này", 403)
    return sess


class ExtractReq(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)


@router.post("/extract")
async def extract(body: ExtractReq, user: dict = Depends(require_auth)):
    sess = await _owned_session(body.session_id, user)
    metas, files = [], []
    for f in sess.get("files") or []:
        data_url = up_store.file_to_data_url(body.session_id, f)
        if data_url:
            metas.append(f)
            files.append({"name": f.get("name"), "type": f.get("type"), "dataUrl": data_url})
    if not files:
        raise AppError("NO_FILES", "Chưa có ảnh giấy tờ nào trong phiên", 400)
    out = await extract_people(files)
    fids = [m["fid"] for m in metas]
    # tepNguon là chỉ số tệp → đổi ra fid để trang hiện ảnh chân dung đúng người ở câu hỏi "Ai nhờ?".
    for person in out["people"]:
        person["fids"] = [fids[i] for i in person.pop("tepNguon")]
    out["unusedFiles"] = [fids[i] for i in out["unusedFiles"]]
    out["ocrFailed"] = [fids[i] for i in out["ocrFailed"]]
    return out


@router.delete("/sessions/{sid}")
async def delete_session(sid: str, user: dict = Depends(require_auth)):
    """Đóng tab / "Xóa hết, làm lại" → xoá NGAY ảnh căn cước, không chờ phiên hết hạn."""
    await _owned_session(sid, user)
    await up_store.delete_session(sid)
    return {"ok": True}


class PartyIn(BaseModel):
    hoTen: str = Field(default="", max_length=200)
    ngaySinh: str = Field(default="", max_length=20)
    diaChi: str = Field(default="", max_length=500)
    soDinhDanh: str = Field(default="", max_length=30)
    ngayCap: str = Field(default="", max_length=20)
    noiCap: str = Field(default="", max_length=200)


# Đồng ủy quyền / ủy quyền cho nhiều người: mỗi bên là DANH SÁCH. Nhận cả object đơn (dạng đầu
# tiên của trang) để file cache cũ của tab đang mở không vỡ.
_MAX_PEOPLE_PER_SIDE = 10


def _as_people(value) -> list[PartyIn]:
    items = value if isinstance(value, list) else [value]
    people = [p if isinstance(p, PartyIn) else PartyIn(**(p or {})) for p in items][:_MAX_PEOPLE_PER_SIDE]
    return people or [PartyIn()]


class RenderReq(BaseModel):
    format: Literal["docx", "pdf"]
    benUyQuyen: list[PartyIn] | PartyIn = Field(default_factory=lambda: [PartyIn()])
    benDuocUyQuyen: list[PartyIn] | PartyIn = Field(default_factory=lambda: [PartyIn()])
    ghiNgaySinhDuocUyQuyen: bool = False
    noiDung: str = Field(default="", max_length=4000)
    lapTai: str = Field(default="", max_length=300)
    ngayLap: str = Field(default="", max_length=20)
    soBan: str = Field(default="2", max_length=4)
    moiBenGiu: str = Field(default="1", max_length=4)


def _slug(name: str) -> str:
    text = unicodedata.normalize("NFD", name or "").replace("Đ", "D").replace("đ", "d")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:40] or "ban_moi"


_MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


@router.post("/render")
async def render_letter(body: RenderReq, _: dict = Depends(require_auth)):
    uy_quyen, duoc_uy_quyen = _as_people(body.benUyQuyen), _as_people(body.benDuocUyQuyen)
    letter = render.Letter(
        benUyQuyen=[render.Party(**p.model_dump()) for p in uy_quyen],
        benDuocUyQuyen=[render.Party(**p.model_dump()) for p in duoc_uy_quyen],
        ghiNgaySinhDuocUyQuyen=body.ghiNgaySinhDuocUyQuyen,
        noiDung=body.noiDung, lapTai=body.lapTai, ngayLap=body.ngayLap,
        soBan=body.soBan, moiBenGiu=body.moiBenGiu,
    )
    data = render.to_docx(letter) if body.format == "docx" else render.to_pdf(letter)
    filename = f"Giay_uy_quyen_{_slug(uy_quyen[0].hoTen)}.{body.format}"
    return Response(
        content=data, media_type=_MIME[body.format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )
