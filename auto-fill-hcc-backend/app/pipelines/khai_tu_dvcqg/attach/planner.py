"""Đính kèm "Thành phần hồ sơ" cho khai tử trên Cổng DVC quốc gia bản mới.

Bảng trên cổng có 4 dòng cố định, tên dòng giống hệt cổng cũ nhưng THỨ TỰ khác:
  1. Giấy báo tử hoặc giấy tờ thay Giấy báo tử
  2. Văn bản ủy quyền
  3. Giấy tờ chứng minh sự kiện chết (người chết đã lâu)
  4. Giấy tờ chứng minh nơi chết hoặc nơi phát hiện thi thể
Mỗi dòng có nút icon "Tải lên file"; trang KHÔNG có nút "Thêm thành phần hồ sơ".

Phân loại, tách trang, gộp CCCD dùng nguyên planner "khai-tu" (khớp dòng theo tên). Khác biệt:
- extension chưa gửi `attachmentContext` thì cấp sẵn 4 dòng trên, index = STT trên cổng;
- ô "Tài liệu đính kèm" của một dòng nhận NHIỀU tệp (cổng cũ mỗi dòng một tệp, tệp sau phải "thêm thành
  phần"): tài liệu cùng loại thứ hai trở đi (vd biên bản xác minh + bản cam đoan) vào chung dòng của loại đó;
- tài liệu không thuộc dòng nào (CCCD, tờ khai thứ hai...) không có chỗ "thêm thành phần" nên bỏ,
  ghi vào `extracted.skipped`.
"""

from app.pipelines.khai_tu.attach import planner as khai_tu_planner
from app.process.schemas import FileItem

PORTAL_ROWS = [
    {
        "index": 1,
        "componentName": (
            "- Giấy báo tử hoặc giấy tờ thay Giấy báo tử do cơ quan có thẩm quyền cấp."
        ),
    },
    {
        "index": 2,
        "componentName": (
            "- Văn bản ủy quyền (được chứng thực) theo quy định của pháp luật trong trường hợp ủy quyền "
            "thực hiện việc đăng ký khai tử."
        ),
    },
    {
        "index": 3,
        "componentName": (
            "- Giấy tờ, tài liệu, chứng cứ do cơ quan, tổ chức có thẩm quyền cấp hoặc xác nhận hợp lệ "
            "chứng minh sự kiện chết đối với trường hợp đăng ký khai tử cho người chết đã lâu"
        ),
    },
    {
        "index": 4,
        "componentName": (
            "- Trường hợp không xác định được nơi cư trú cuối cùng của người chết thì xuất trình giấy tờ "
            "chứng minh nơi người đó chết hoặc nơi phát hiện thi thể của người chết."
        ),
    },
]


def _with_portal_rows(options: dict | None) -> dict:
    options = dict(options or {})
    context = dict(options.get("attachmentContext") or {})
    if not context.get("components"):
        context["components"] = [dict(row) for row in PORTAL_ROWS]
        options["attachmentContext"] = context
    return options


async def plan_khai_tu_dvcqg_attachments(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    options = _with_portal_rows(options)
    result = await khai_tu_planner.plan(files, options, session)
    # Loại tài liệu của từng mục (planner "khai-tu" ghi trong extracted.classified, khớp theo tệp + tên).
    doc_types = {
        (row.get("fileIndex"), row.get("documentName")): row.get("type")
        for row in (result.get("extracted") or {}).get("classified") or []
    }
    kept, dropped = [], []
    for item in result.get("attachments") or []:
        if item.get("target") != "existing":
            slot = khai_tu_planner._slot_for_type(
                options, doc_types.get((item.get("fileIndex"), item.get("documentName")), "")
            )
            if not slot:
                dropped.append(item)
                continue
            item.update({
                "target": "existing",
                "componentIndex": slot[0],
                "componentName": slot[1],
                "needsAddComponent": False,
            })
        kept.append(item)
    result["attachments"] = kept
    extracted = result.setdefault("extracted", {})
    extracted["skipped"] = [
        f"{item.get('fileName')} ({item.get('documentName')})" for item in dropped
    ]
    return result


# Entrypoint thống nhất cho registry app.pipelines.<procedure>.attach.
plan = plan_khai_tu_dvcqg_attachments
