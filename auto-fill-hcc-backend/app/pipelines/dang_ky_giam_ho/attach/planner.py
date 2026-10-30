"""Điều phối hai chế độ đính kèm của thủ tục đăng ký giám hộ (và đăng ký chấm dứt giám hộ)."""

import re

from app.pipelines.dang_ky_giam_ho.attach.dinh_kem_khong_tach.planner import plan as plan_without_split
from app.pipelines.dang_ky_giam_ho.attach.dinh_kem_tach.planner import plan as plan_with_split
from app.pipelines._shared import fold
from app.process.schemas import FileItem


async def plan_dang_ky_giam_ho_attachments(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Chỉ boolean ``True`` mới tách; client cũ tiếp tục giữ nguyên từng file."""
    planner = plan_with_split if (options or {}).get("splitDocuments") is True else plan_without_split
    return await planner(files, options, session=session)


plan = plan_dang_ky_giam_ho_attachments


# Đăng ký chấm dứt giám hộ (1.004845) cùng bộ giấy tờ nhưng bảng thành phần chỉ có:
#   STT1 - Mẫu hộ tịch điện tử tương tác đăng ký chấm dứt giám hộ (eForm, không xử lý)
#   STT2 - Giấy tờ làm căn cứ chấm dứt giám hộ theo quy định của Bộ luật Dân sự
#   STT3 - Văn bản ủy quyền
# Không có dòng "văn bản cử" / "điều kiện giám hộ": giấy cử, giấy điều kiện, CCCD, giấy khai sinh và
# giấy liên quan khác (quyết định Tòa án, giấy chứng tử...) đều là căn cứ chấm dứt → STT2.
_CHAM_DUT_BASIS_ROW = (2, "- Giấy tờ làm căn cứ chấm dứt giám hộ theo quy định của Bộ luật Dân sự")
_CHAM_DUT_AUTH_ROW = (3, "- Văn bản ủy quyền theo quy định của pháp luật trong trường hợp ủy quyền")
_CHAM_DUT_RENAME = {
    "to khai dang ky giam ho ban giay": "Tờ khai đăng ký chấm dứt giám hộ bản giấy",
    "giay to chung minh dieu kien giam ho": "Giấy tờ làm căn cứ chấm dứt giám hộ",
    "tai lieu dang ky giam ho": "Tài liệu chấm dứt giám hộ",
    # Bản cam đoan ở thủ tục chấm dứt nêu lý do chấm dứt, không phải cam đoan đủ điều kiện giám hộ.
    "ban cam doan du dieu kien giam ho": "Bản cam đoan",
}


def _cham_dut_row(item: dict) -> tuple[int, str] | None:
    name = fold(item.get("componentName") or "")
    if item.get("target") == "existing":
        if "uy quyen" in name:
            return _CHAM_DUT_AUTH_ROW
        return _CHAM_DUT_BASIS_ROW
    document = fold(item.get("documentName") or "")
    if document.startswith(("to khai", "giay xac nhan tinh trang hon nhan")):
        return None
    return _CHAM_DUT_BASIS_ROW


def route_cham_dut_attachments(result: dict) -> dict:
    """Đổi tuyến kế hoạch đính kèm giám hộ sang bảng thành phần của thủ tục chấm dứt."""
    used_slots: set[int] = set()
    for item in result.get("attachments") or []:
        document = fold(item.get("documentName") or "")
        for old, new in _CHAM_DUT_RENAME.items():
            if document == old or re.fullmatch(re.escape(old) + r" \d+", document):
                # Giữ hậu tố " 2", " 3"... mà planner gốc gắn để tên không trùng.
                item["documentName"] = item["detectedType"] = new + document[len(old):]
                break
        row = _cham_dut_row(item)
        if row is None or row[0] in used_slots:
            item.update({
                "target": "new",
                "componentIndex": None,
                "componentName": item["documentName"],
                "needsAddComponent": True,
            })
            continue
        used_slots.add(row[0])
        item.update({
            "target": "existing",
            "componentIndex": row[0],
            "componentName": row[1],
            "needsAddComponent": False,
        })
    return result


async def plan_cham_dut_giam_ho_attachments(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    result = await plan_dang_ky_giam_ho_attachments(files, options, session=session)
    return route_cham_dut_attachments(result)


__all__ = [
    "plan",
    "plan_cham_dut_giam_ho_attachments",
    "plan_dang_ky_giam_ho_attachments",
    "route_cham_dut_attachments",
]
