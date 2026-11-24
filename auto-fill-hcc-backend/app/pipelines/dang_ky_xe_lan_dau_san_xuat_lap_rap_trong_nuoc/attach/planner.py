"""Đính kèm "Đăng ký xe lần đầu trực tuyến toàn trình đối với xe sản xuất lắp ráp trong nước" (1.012575, Cổng DVC Bộ
Công an).

Như xe nhập khẩu 1.013066 (user 24/11/2026): trang kê khai KHÔNG có bảng Thành phần hồ sơ; phần "đính kèm" là ba ô tải
ảnh ĐẦU trang ("Ảnh phương tiện", "Ảnh chứng từ nguồn gốc mặt trước / mặt sau" = hai mặt Phiếu kiểm tra chất lượng xuất
xưởng). Kế hoạch không có mục bảng (``attachments`` rỗng, ``nothingToAttach``), chỉ có ``pageFields`` comp ``bca-photo``
(Auto Fill: popup.js ``fillAttachPageFields``; trợ lý: pipeline_runner đổi thành mục ``target: "bca-photo"``). Bật hay tắt
"Tách giấy tờ" ra cùng một kế hoạch.
"""

from app.process.schemas import FileItem


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.attach.planner import plan_page_photos
    from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process.runner import (
        ORIGIN_LABEL,
        phieu_xuat_xuong_page,
    )

    del options
    return await plan_page_photos(files, session, is_origin=phieu_xuat_xuong_page, origin=ORIGIN_LABEL)
