"""Đính kèm "Đăng ký xe lần đầu trực tuyến toàn trình đối với xe nhập khẩu" (1.013066, Cổng DVC Bộ Công an).

Trang kê khai KHÔNG có bảng Thành phần hồ sơ; bấm "Đồng ý và tiếp tục" là sang thẳng trang Xác nhận (user 24/11/2026).
Phần "đính kèm" là ba ô tải ảnh ĐẦU trang kê khai: "Ảnh phương tiện", "Ảnh chứng từ nguồn gốc mặt trước / mặt sau" (tờ
khai hàng hóa nhập khẩu) — chọn ảnh bằng đúng luật của lượt điền (process/runner.py ``photo_slots``). Kế hoạch vì thế
không có mục bảng (``attachments`` rỗng, ``nothingToAttach``), chỉ có ``pageFields`` comp ``bca-photo``:
- Auto Fill: popup.js ``fillAttachPageFields`` gắn thẳng các ô này;
- trợ lý: pipeline_runner lưu ảnh vào phiên rồi đổi thành mục kế hoạch ``target: "bca-photo"`` (sidebar gắn).
Cài đặt "Tách giấy tờ" không đổi kết quả: ảnh lấy theo loại giấy / trang tờ khai, không có tệp nào phải chia vào dòng
bảng, nên bật hay tắt tách đều ra cùng một kế hoạch (registry vẫn khai supportsSplitDocuments như mọi thủ tục có đính
kèm để option tới được planner).
"""

from app.process.schemas import FileItem


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process.runner import missing_photo_note, photo_slots
    from app.services import ocr

    del options
    raw = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    errors: list[str] = []
    results = await ocr.ocr_per_file(raw) if raw else []
    for item in results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")
    texts = {i: str((results[i] if i < len(results) else {}).get("text") or "") for i in range(len(raw))}
    photos, done, missing = photo_slots(raw, texts)
    if missing:
        errors.append(missing_photo_note(missing, retry="đính kèm lại"))
    return {
        "attachments": [],
        "nothingToAttach": True,
        "pageFields": photos,
        "extracted": {
            "documents": [f["name"] for f in raw],
            "pagePhotos": done,
            "missingPagePhotos": missing,
            "sessionId": (session or {}).get("request_id"),
        },
        "errors": errors,
    }
