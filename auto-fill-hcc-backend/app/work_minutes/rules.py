"""Quy tắc thuần của biên bản làm việc (văn bản mẫu, tên đơn vị trên biên bản, kỳ mặc định, trường trả về)."""
from datetime import date, timedelta
from typing import Annotated

from pydantic import BaseModel, Field

from app.daily_reports.rules import iso, parse_day, today_vn  # noqa: F401 - dùng chung lịch VN + kiểm ngày
from app.reports.integration import province_name

# Đơn vị triển khai in ở đầu và cuối biên bản; dùng chung mọi tỉnh.
COMPANY = {
    "l1": "CÔNG TY CỔ PHẦN ĐẦU TƯ",
    "l2": "KỶ NGUYÊN MỚI VIỆT NAM",
    "full": "Công ty Cổ phần Đầu tư Kỷ Nguyên Mới Việt Nam",
    "short": "Công ty CP Đầu tư Kỷ Nguyên Mới Việt Nam",
}
NO_ISSUE = "- Trong thời gian làm việc, hiện tại chưa phát sinh khó khăn, vướng mắc."
NEXT_DEFAULT = "Ghi nhận và hỗ trợ các vấn đề phát sinh trong quá trình triển khai (nếu có)."

MAX_LINE = 300
MAX_PARA = 2000
MAX_COUNT = 999_999
MAX_ITEMS = 50
MAX_ROWS = 500

_Line = Annotated[str, Field(max_length=MAX_LINE)]
_Para = Annotated[str, Field(max_length=MAX_PARA)]


class Person(BaseModel):
    x: str = Field("", max_length=10)  # Ông / Bà
    n: _Line = ""
    r: _Line = ""


class Row(BaseModel):
    code: str = Field("", max_length=40)
    name: _Para = ""
    n: int = Field(0, ge=0, le=MAX_COUNT)


class Doc(BaseModel):
    """Nội dung biên bản đúng như trên bản xem trước; ô trống in ra khoảng trắng, không tự điền thay."""
    place: _Line = ""
    prov: _Line = ""
    start: str = Field("", max_length=60)
    end: str = Field("", max_length=60)
    cty: list[Person] = Field(default_factory=list, max_length=MAX_ITEMS)
    tt: list[Person] = Field(default_factory=list, max_length=MAX_ITEMS)
    signTT: int = Field(-1, ge=-1, le=MAX_ITEMS)
    signCty: int = Field(-1, ge=-1, le=MAX_ITEMS)
    may: str = Field("", max_length=10)
    mayNote: _Line = ""
    thietBi: _Line = ""
    canBo: str = Field("", max_length=10)
    rows: list[Row] = Field(default_factory=list, max_length=MAX_ROWS)
    v: int = Field(0, ge=0, le=MAX_COUNT)
    nv: int = Field(0, ge=0, le=MAX_COUNT)
    issues: list[_Para] = Field(default_factory=list, max_length=MAX_ITEMS)
    evals: list[_Para] = Field(default_factory=list, max_length=MAX_ITEMS)
    next: list[_Para] = Field(default_factory=list, max_length=MAX_ITEMS)


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else ""


def place_of(unit: dict) -> str:
    """"Phường Bắc Giang" → "phường Bắc Giang" như câu văn trên biên bản."""
    return _lower_first((unit.get("xa") or unit.get("name") or "").strip())


def prov_of(unit: dict) -> str:
    return _lower_first(province_name(unit.get("tinh")) or "")


def eval_default(place: str) -> list[str]:
    return [
        "- Lãnh đạo, cán bộ Trung tâm rất phối hợp, tích cực trong quá trình triển khai Trợ lý Nhân dân hoàn thiện "
        "thủ tục hành chính; cán bộ chủ động hướng dẫn, đưa công dân vào trải nghiệm và sử dụng công cụ Trợ lý "
        "Nhân dân.",
        "- Công cụ hỗ trợ cán bộ và người dân điền hồ sơ nhanh, giảm thao tác thủ công, hạn chế sai sót, tối ưu "
        "thời gian tiếp nhận và xử lý; bước đầu được đánh giá thiết thực, dễ sử dụng.",
        f"- Sự phối hợp giữa nhân sự đội triển khai của {COMPANY['full']} và cán bộ Trung tâm Phục vụ hành chính "
        f"công {place} diễn ra chặt chẽ, hiệu quả; địa phương đã tạo mọi điều kiện thuận lợi cho đơn vị triển khai "
        "thực hiện nhiệm vụ.",
    ]


def default_from(last_to: str | None, today: str) -> str:
    """Kỳ mới nối tiếp biên bản gần nhất; chưa có biên bản thì từ đầu tháng."""
    start = (date.fromisoformat(last_to) + timedelta(days=1)).isoformat() if last_to else today[:8] + "01"
    return min(start, today)


def blank_people() -> list[dict]:
    return [{"x": "", "n": "", "r": ""}]


def build_doc(unit: dict, system: dict, last: dict | None) -> dict:
    """Bản nháp chỉ chứa thứ biết chắc: tên đơn vị theo tài khoản, số liệu hệ thống, người tham dự / máy /
    thiết bị / số cán bộ của biên bản trước (thường không đổi). Giờ bắt đầu, kết thúc để trống."""
    prev = (last or {}).get("doc") or {}
    place = place_of(unit)
    return {
        "place": place,
        "prov": prov_of(unit),
        "start": "",
        "end": "",
        "cty": prev.get("cty") or blank_people(),
        "tt": prev.get("tt") or blank_people(),
        "signTT": prev.get("signTT", -1) if prev.get("tt") else -1,
        "signCty": prev.get("signCty", -1) if prev.get("cty") else -1,
        "may": prev.get("may") or "",
        "mayNote": prev.get("mayNote") or "",
        "thietBi": prev.get("thietBi") or "",
        "canBo": prev.get("canBo") or "",
        "rows": system["rows"],
        "v": system["v"],
        "nv": system["nv"],
        "issues": [""],
        "evals": eval_default(place),
        "next": [NEXT_DEFAULT],
    }


def total_of(doc: dict) -> int:
    return sum(int(r.get("n") or 0) for r in doc.get("rows") or [])


def serialize_summary(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "unitId": doc.get("unit_id"),
        "unitName": doc.get("unit_name"),
        "province": doc.get("province"),
        "from": doc.get("period_from"),
        "to": doc.get("period_to"),
        "lap": doc.get("lap_date"),
        "total": total_of(doc.get("doc") or {}),
        "createdAt": iso(doc.get("created_at")),
        "createdBy": doc.get("created_by_name"),
        "updatedAt": iso(doc.get("updated_at")) if doc.get("updated_at") != doc.get("created_at") else None,
        "updatedBy": doc.get("updated_by_name"),
    }


def serialize_full(doc: dict) -> dict:
    return {**serialize_summary(doc), "doc": doc.get("doc") or {}, "base": doc.get("base") or doc.get("doc") or {}}


def serialize_draft(doc: dict) -> dict:
    return {
        "unitId": doc.get("_id"),
        "editingId": doc.get("editing_id"),
        "from": doc.get("period_from"),
        "to": doc.get("period_to"),
        "lap": doc.get("lap_date"),
        "doc": doc.get("doc") or {},
        "base": doc.get("base") or {},
        "saved": True,
        "updatedAt": iso(doc.get("updated_at")),
        "updatedBy": doc.get("updated_by_name"),
    }
