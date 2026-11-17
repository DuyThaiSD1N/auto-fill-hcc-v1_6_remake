"""Compact agent process pipeline for "Xác định mức độ khuyết tật"."""

import asyncio
import copy
import re
import unicodedata

from app.pipelines._shared.area_remap import province_for_ward
from app.pipelines._shared.compact_agent import runner
from app.pipelines.khuyet_tat.process import dang_khuyet_tat, mapper, muc_do, vision
from app.pipelines.khuyet_tat.process.prompt import EXTRA_RULES
from app.pipelines.khuyet_tat.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def _norm_text(value: str) -> str:
    text = str(value or "").replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^0-9a-zA-Z]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _identity_occurs(identity: str, text: str) -> bool:
    if not identity:
        return False
    candidates = re.findall(r"(?:\d[ \t./\-]*){9,13}", str(text or ""))
    return any(re.sub(r"\D+", "", candidate) == identity for candidate in candidates)


def _matches_anchor(text: str, name: str, identity: str) -> bool:
    """Có đủ hai mỏ neo UI thì cùng một tài liệu phải khớp cả hai."""
    name_matches = bool(name and name in _norm_text(text))
    identity_matches = bool(identity and _identity_occurs(identity, text))
    if name and identity:
        return name_matches and identity_matches
    return name_matches if name else identity_matches


async def _requester_context(documents: list[dict], options: dict) -> str:
    """Khoanh giấy tờ người nộp bằng UI; dữ liệu output vẫn phải có trong OCR."""
    form = (options or {}).get("formContext") or {}
    name = _norm_text(form.get("applicantFullname") or form.get("fullname") or "")
    identity = re.sub(
        r"\D+",
        "",
        str(form.get("applicantIdentityNumber") or form.get("identityNumber") or ""),
    )

    if not name and not identity:
        return (
            '\n\n<requester_context result="missing_ui_anchor">\n'
            "UI không có mỏ neo người nộp. Không trả NguoiNop_*.\n"
            "</requester_context>"
        )

    matched = [
        (index, str(document.get("text") or "")[:6000])
        for index, document in enumerate(documents, start=1)
        if _matches_anchor(str(document.get("text") or ""), name, identity)
    ]
    if not matched:
        return (
            '\n\n<requester_context result="no_document_match">\n'
            "Không tài liệu OCR nào khớp đủ mỏ neo người nộp từ UI. "
            "Không trả NguoiNop_*; vẫn trích ChuHoSo_* và các field nghiệp vụ.\n"
            "</requester_context>"
        )

    scopes = "\n".join(
        (
            f'<matched_requester_ocr document="{index}">\n'
            "Đây là tài liệu đã được Python xác nhận thuộc người nộp. "
            "BẮT BUỘC trích mọi NguoiNop_* đọc được từ chính OCR này.\n"
            f"{text}\n"
            "</matched_requester_ocr>"
        )
        for index, text in matched
    )
    return (
        '\n\n<requester_context result="document_match">\n'
        "Chỉ trích NguoiNop_* từ matched_requester_ocr; không dùng tài liệu người khác.\n"
        "</requester_context>\n"
        + scopes
    )


def _counter_context(options: dict) -> str:
    """Xã / phường của tài khoản quầy (nơi nhận hồ sơ) cho quy tắc địa chỉ "gần giống xã quầy thì lấy xã quầy"."""
    raw = re.sub(r"^\s*(hcc|tt\s*hcc|ubnd)\s+", "", str((options or {}).get("counterWard") or "").strip(), flags=re.I)
    hit = province_for_ward(re.split(r"\s*[-–,]\s*|\s+tỉnh\s+", raw)[0].strip()) if raw else None
    if not hit:
        return ""
    province, ward = hit
    return f"\n\n<xa_quay>\nXã / phường của tài khoản quầy đang nhận hồ sơ: {ward}, {province}.\n</xa_quay>"


async def _owner_only_context(documents: list[dict], options: dict) -> str:
    """Chế độ THEO TỜ KHAI: không đưa mỏ neo tài khoản vào prompt; mapper lấy người nộp từ mục II."""
    _ = documents, options
    return (
        '\n\n<requester_context result="missing_ui_anchor">\n'
        "Chế độ người nộp theo tờ khai: KHÔNG dùng mỏ neo UI. Không trả NguoiNop_*; vẫn trích ChuHoSo_*, "
        "Nkt_* và đủ Ndd_*.\n"
        "</requester_context>"
    )


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    owner_mode = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    levels_tasks: list = []
    # Điền đợt 2 cần OCR từng tài liệu và field TRƯỚC mapper — runner chung chỉ trả chuỗi OCR đã nối.
    second_pass = bool((options or {}).get("_secondPass"))
    read: dict = {}
    requester_context = _owner_only_context if owner_mode else _requester_context

    types_tasks: list = []

    async def build_context(documents: list[dict], opts: dict) -> str:
        read["documents"] = documents
        # Bảng dạng khuyết tật (mục III.1) đọc riêng song song lượt trích chính, như bảng mức độ.
        types_tasks.append(asyncio.create_task(dang_khuyet_tat.read_disability_types(documents)))
        return await requester_context(documents, opts) + _counter_context(opts)

    # Mục III đọc thẳng từ ảnh song song với OCR + LLM; luôn chờ cả hai xong.
    res, section_iii = await asyncio.gather(runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=muc_do.context_with_levels(build_context, levels_tasks),
        max_tokens=2200,
    ), vision.read_section_iii(runner.flatten(files_by_role)) if vision.ENABLED else asyncio.sleep(0))
    await muc_do.apply_levels(res, levels_tasks)
    if section_iii is not None:
        for task in types_tasks:
            task.cancel()
        # Bảng tích ✓ viết tay: kết quả đọc ảnh thay hẳn phần LLM bóc từ OCR văn bản (kể cả khi rỗng).
        res["fields"] = [f for f in res["fields"] if f.get("name") not in section_iii] + [
            {"name": name, "comp": "raw", "value": value} for name, value in section_iii.items()
        ]
    else:
        if vision.ENABLED:
            # Kết quả dự phòng từ OCR văn bản hay mất cột Có/Không của bảng tích.
            res.setdefault("errors", []).append(vision.SECTION_III_WARNING)
        dang_khuyet_tat.apply(res, await types_tasks[0] if types_tasks else None)
    # OCR để mapper dò lại tên phường/xã khi LLM cắt cụt ("Phường Bắc Nha Trang" → "Bắc").
    enrich_options = {**(options or {}), "_ocr_text": res.get("ocr_text") or ""}
    raw_fields = copy.deepcopy(res["fields"]) if second_pass else []
    res["fields"] = mapper.enrich(res["fields"], enrich_options)
    if raw_fields and read.get("documents"):
        from ..thanh_tra import dot_hai

        # Nơi gọi pipeline lấy khoá này ra khỏi kết quả rồi chạy ở nền sau khi đã trả lượt điền đầu.
        res["_second_pass"] = lambda base_fields: dot_hai.patch(read["documents"], raw_fields, base_fields,
                                                                enrich_options)
    return res
