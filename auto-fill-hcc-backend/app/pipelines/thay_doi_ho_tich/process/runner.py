"""Compact agent pipeline cho "Thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc"."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.thay_doi_ho_tich.process import declaration, mapper
from app.pipelines.thay_doi_ho_tich.process.prompt import EXTRA_RULES
from app.pipelines.thay_doi_ho_tich.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def _fold(value: str) -> str:
    text = str(value or "").replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-zA-Z]+", " ", text)).strip().lower()


def _digits(value: str) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _is_identity_document(text: str) -> bool:
    folded = _fold(text)
    return any(
        marker in folded
        for marker in (
            "can cuoc cong dan",
            "citizen identity card",
            "chung minh nhan dan",
            "identity card",
        )
    )


def _matches_requester(text: str, name: str, identity: str) -> bool:
    text_name = _fold(text)
    text_digits = _digits(text)
    name_matches = bool(name and name in text_name)
    identity_matches = bool(identity and identity in text_digits)
    if name and identity:
        return name_matches and identity_matches
    return name_matches if name else identity_matches


async def _identity_context(documents: list[dict], options: dict) -> str:
    """Định vị CCCD người yêu cầu; mọi CCCD còn lại vẫn phải ghép đúng chủ thể."""
    context = (options or {}).get("formContext") or {}
    requester_name = _fold(
        context.get("applicantFullname")
        or context.get("fullname")
        or ""
    )
    requester_identity = _digits(
        context.get("applicantIdentityNumber")
        or context.get("identityNumber")
        or ""
    )

    identity_indexes: list[int] = []
    requester_indexes: list[int] = []
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        if not _is_identity_document(text):
            continue
        identity_indexes.append(index)
        if _matches_requester(
            text,
            requester_name,
            requester_identity,
        ):
            requester_indexes.append(index)

    if not identity_indexes:
        return ""

    requester_label = (
        ", ".join(str(index) for index in requester_indexes)
        if requester_indexes
        else "không xác định"
    )
    other_indexes = [
        index
        for index in identity_indexes
        if index not in requester_indexes
    ]
    other_label = (
        ", ".join(str(index) for index in other_indexes)
        if other_indexes
        else "không có"
    )
    return (
        "\n\n<identity_document_context>\n"
        f"- Tài liệu CCCD/CMND đã upload: {', '.join(map(str, identity_indexes))}.\n"
        "- BẮT BUỘC đưa từng tài liệu trên thành một object riêng trong DanhSachCccd.\n"
        f"- CCCD khớp người yêu cầu trên UI: {requester_label}. "
        "Chỉ tài liệu này được đưa vào Cccd_*.\n"
        f"- CCCD khác người yêu cầu: {other_label}. Không được bỏ qua. "
        "Phải đối chiếu họ tên/số định danh/ngày sinh với ChuThe, Chong, Vo "
        "và hợp nhất toàn bộ thông tin CCCD vào đúng nhóm người khớp.\n"
        "- Nếu một người vừa là người yêu cầu vừa là chủ thể thì được trả cả "
        "Cccd_* và nhóm chủ thể tương ứng; không làm mất thông tin CCCD.\n"
        "</identity_document_context>"
    )


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=_identity_context,
    )
    # Agent hay dồn dữ kiện người yêu cầu của tờ khai vào Cccd_* rồi bỏ trống NguoiYeuCau_*,
    # khiến mapper rơi xuống dữ liệu VNeID của tài khoản đăng nhập. Tờ khai là biểu mẫu chuẩn
    # nên đọc lại khối đó tất định và bù các ô còn thiếu.
    res["fields"] = declaration.fill_missing(
        res["fields"],
        res.get("ocr_text") or "",
        COMPACT_COMP_BY_NAME,
    )
    # _ocrText: mapper cần chính văn bản OCR để chốt chồng/vợ là người được cải chính khi hồ sơ
    # không có tờ khai và cả hai bên đều nộp CCCD (xem mapper._subject_from_evidence).
    res["fields"] = mapper.enrich(
        res["fields"],
        {**(options or {}), "_ocrText": res.get("ocr_text") or ""},
    )

    # Rà soát bbox (Kiểu A): chỉ chạy khi router bật cờ _review (thủ tục có "review": True).
    if (options or {}).get("_review"):
        from app.review import capture
        from app.pipelines.thay_doi_ho_tich.process.schema import REVIEW_FIELDS
        try:
            cap = await capture.capture(files_by_role, res["fields"], review_names=REVIEW_FIELDS)
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res
