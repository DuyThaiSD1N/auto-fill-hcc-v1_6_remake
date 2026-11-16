"""Dựng ô form Cấp lại thẻ căn cước (Cổng DVC Bộ Công an) từ dữ kiện compact.

Cùng trang, cùng bộ ô với cấp đổi căn cước → dùng lại enrich của cap_doi_the_can_cuoc, chỉ thay nhãn radio người kê
khai và bảng lý do cấp của trang cấp lại.
"""

from app.pipelines.cap_doi_the_can_cuoc.process import mapper as cap_doi
from app.pipelines.cap_lai_the_can_cuoc.process.schema import DECLARANT_OTHER, DECLARANT_SELF, REASONS

PROCEDURE_KEY = "cap-lai-the-can-cuoc"


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Bản sao options kèm xã/tỉnh tài khoản: dự phòng ô Cơ quan thực hiện (bắt buộc) khi giấy không ghi."""
    result = dict(options or {})
    if procedure != PROCEDURE_KEY:
        return result
    result.pop(cap_doi.ACCOUNT_AGENCY_OPTION, None)
    if isinstance(user, dict) and user.get("tinh") and user.get("xa"):
        result[cap_doi.ACCOUNT_AGENCY_OPTION] = {"tinh": str(user["tinh"]), "xa": str(user["xa"])}
    return result


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    return cap_doi.enrich(fields, options, reasons=REASONS, declarant_self=DECLARANT_SELF,
                          declarant_other=DECLARANT_OTHER)
