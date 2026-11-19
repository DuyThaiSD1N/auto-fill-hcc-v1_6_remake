"""Phần chung của các thanh tra cấp giấy phép xây dựng mới: loại giấy trong hồ sơ (lựa chọn "thuộc về") và khóa so sánh
các giá trị mà mapper chuẩn hoá lại (số đo, chi tiết "Trong đó", cấp công trình)."""

import re

from app.pipelines._shared.thanh_tra.ho_so import Case, fold

from ..process import mapper

# Lựa chọn "dòng chứng cứ thuộc giấy nào" — dùng chung cho cả bốn thanh tra.
DON = "đơn đề nghị cấp giấy phép xây dựng"
GCN = "giấy chứng nhận quyền sử dụng đất"
BAN_VE = "bản vẽ / thuyết minh thiết kế"
CCCD = "căn cước / CMND"
CHUNG_CHI = "chứng chỉ năng lực / chứng chỉ hành nghề / giấy đăng ký doanh nghiệp"
UY_QUYEN = "giấy ủy quyền"
KHAC = "giấy khác"
OWNERS = (DON, GCN, BAN_VE, CCCD, CHUNG_CHI, UY_QUYEN, KHAC)


def number_key(value) -> str:
    """Số đo so theo giá trị ("39,0" = "39" = "39.0")."""
    return mapper._number(value) or ""


def detail_key(value) -> str:
    """Chi tiết "Trong đó" so sau khi mapper đã bỏ chấm điền / chữ hướng dẫn / mục bằng 0, không tính dấu câu."""
    return re.sub(r"[\W_]+", "", fold(mapper._clean_detail(value) or ""))


def cap_key(value) -> str:
    return mapper._cap(value) or ""


def text_key(value) -> str:
    return re.sub(r"[\W_]+", "", fold(value or ""))


_PAGE_BREAK_RE = re.compile(r"(─────\s*Trang\s*\d+\s*/\s*\d+\s*─────)")


def narrowed(case, markers: tuple[str, ...]):
    """Case chỉ giữ những TRANG có một trong các dấu hiệu (so bỏ dấu) — mỗi thanh tra đọc đúng loại giấy của mình, khỏi
    đọc cả tập bản vẽ dài. Tài liệu không còn trang nào để trống chứ không bỏ: số thứ tự tài liệu giữ nguyên."""
    documents = []
    for document in case.documents:
        parts = _PAGE_BREAK_RE.split(str(document.get("text") or ""))
        # parts = [trước trang 1, nhãn, nội dung, nhãn, nội dung, ...]
        pages = [(parts[i], parts[i + 1]) for i in range(1, len(parts) - 1, 2)] or [("", parts[0])]
        kept = [f"{label}\n{body}".strip() for label, body in pages if any(marker in fold(body) for marker in markers)]
        documents.append({**document, "text": "\n".join(kept)})
    return Case(documents, case.context, case.values, case.options)
