"""Compact-agent process pipeline cho đăng ký đất đai lần đầu (Tuyên Quang) — form "5 bước 20 ngày" + chọn form.

Trợ lý người dân: công dân chọn quy trình ở hộp thoại "Chọn trường hợp giải quyết" → registry trợ lý (caseOptions)
gửi ``options.quyTrinh`` = "ilis" / "vbdlis" → chạy form của quy trình đó. Auto Fill không gửi khóa này: extension tự
nhận diện form theo tiêu đề trang rồi gọi thẳng key ``-ilis`` / ``-vbdlis``.

Bộ hồ sơ hay có cả bản thường lẫn bản đã ký số của cùng một tệp ("DON.pdf" + "DON.signed.pdf", ảnh scan giống hệt):
chỉ đọc bản ký số (OCR gấp đôi dễ quá timeout 100s của extension). PDF lớn OCR song song theo phần như đăng ký biến
động Đà Nẵng.

Giới tính chỉ nằm ở giấy khai sinh / CCCD hay danh xưng "Bà …" trong hợp đồng giữa xấp giấy tờ nguồn gốc đất: chạy thử
bộ mẫu, LLM bỏ sót field này khoảng một nửa số lần dù OCR đọc rõ → apply_ocr_fallback đọc lại thẳng từ OCR.
"""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines._shared.naming import fold
from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.process.runner import (
    _ocr_split_large_pdfs,
)

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS

_EXTENSION = re.compile(r"\.[a-z0-9]{2,5}$", re.IGNORECASE)
_SIGNED = re.compile(r"[\s._-]*signed$", re.IGNORECASE)
_GENDER_WORD = {"nam": "Nam", "nu": "Nữ"}
_GENDER_TITLE = {"ong": "Nam", "ba": "Nữ"}


def _gender_from_text(name: str, text: str) -> str | None:
    """Giới tính của ĐÚNG người tên ``name`` trong OCR đã fold: dòng "Họ và tên: <tên> … Giới tính: Nữ" (giấy khai
    sinh, CCCD — không vượt sang "Họ và tên" của người khác) hoặc danh xưng "Bà <tên>" / "Ông <tên>". Vênh nhau → None."""
    who = re.escape(fold(name))
    found: set[str] = set()
    labeled = (rf"ho (?:va |, chu dem, )?ten(?: ?/ ?full name)?\W{{0,10}}{who}\b(?:(?!ho (?:va )?ten).){{0,160}}?"
               rf"gioi tinh(?: ?/ ?sex)?\W{{0,4}}(nam|nu)\b")
    for match in re.finditer(labeled, text):
        found.add(_GENDER_WORD[match.group(1)])
    for match in re.finditer(rf"\b(ong|ba)\W{{0,3}}{who}\b", text):
        found.add(_GENDER_TITLE[match.group(1)])
    return found.pop() if len(found) == 1 else None


def apply_ocr_fallback(raw_fields, documents: list[dict]):
    """Bù giới tính chủ hồ sơ / bên được ủy quyền mà LLM bỏ sót, đọc thẳng từ OCR theo đúng họ tên LLM đã chốt."""
    if not isinstance(raw_fields, (dict, list)):
        return raw_fields
    fields = dict(raw_fields) if isinstance(raw_fields, dict) else {
        item.get("name"): item.get("value") for item in raw_fields if isinstance(item, dict) and item.get("name")}
    text = fold("\n".join(str(document.get("text") or "") for document in documents))
    for role in ("ChuHoSo", "NguoiNop"):
        name = fields.get(f"{role}_HoTen")
        if isinstance(name, str) and name.strip() and not fields.get(f"{role}_GioiTinh"):
            gender = _gender_from_text(name, text)
            if gender:
                fields[f"{role}_GioiTinh"] = gender
    return fields


def _signed_key(file: dict) -> tuple[str, bool]:
    """("giay to", True) cho "GIAY TO.signed.pdf": tên gốc đã gộp khoảng trắng/gạch dưới + có phải bản ký số."""
    stem = _EXTENSION.sub("", str(file.get("name") or "").strip())
    signed = bool(_SIGNED.search(stem))
    key = re.sub(r"[\s_]+", " ", _SIGNED.sub("", stem)).strip().lower()
    return f"{file.get('type') or ''}|{key}", signed


def unsigned_copies(files: list[dict]) -> dict[int, int]:
    """{chỉ số bản chưa ký số: chỉ số bản ký số cùng tên, cùng loại tệp}."""
    signed: dict[str, int] = {}
    for index, file in enumerate(files):
        key, is_signed = _signed_key(file)
        if is_signed:
            signed.setdefault(key, index)
    out: dict[int, int] = {}
    for index, file in enumerate(files):
        key, is_signed = _signed_key(file)
        if not is_signed and key in signed:
            out[index] = signed[key]
    return out


def without_unsigned_copies(files_by_role: dict[str, list[dict]]) -> dict[str, list[dict]]:
    flat = [file for files in files_by_role.values() for file in files]
    dropped = {id(flat[index]) for index in unsigned_copies(flat)}
    return {role: [file for file in files if id(file) not in dropped] for role, files in files_by_role.items()}


async def extract(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    """OCR + LLM ra facts chung của ba form (process/schema.FIELDS), chưa xếp vào ô."""
    return await runner.run(
        without_unsigned_copies(files_by_role),
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=apply_ocr_fallback,
        options=options,
        ocr_fn=_ocr_split_large_pdfs,
    )


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    quy_trinh = str((options or {}).get("quyTrinh") or "")
    if quy_trinh == "ilis":
        from ..process_ilis.runner import run as run_ilis

        return await run_ilis(files_by_role, options)
    if quy_trinh == "vbdlis":
        from ..process_vbdlis.runner import run as run_vbdlis

        return await run_vbdlis(files_by_role, options)
    result = await extract(files_by_role, options)
    result["fields"], warnings = mapper.enrich(result["fields"], options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
