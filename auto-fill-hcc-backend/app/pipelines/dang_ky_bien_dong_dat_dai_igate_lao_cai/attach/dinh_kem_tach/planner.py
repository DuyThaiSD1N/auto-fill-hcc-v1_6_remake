"""Đính kèm 1.115668 Lào Cai cổng iGate mới — chế độ TÁCH giấy tờ (cài đặt "Tách giấy tờ" bật, ``splitDocuments is True``).

Dùng lại bộ chia trang của cổng Lào Cai (``_shared/lao_cai_tach_giay_to.plan_with_split``): OCR tệp gốc một lần, LLM chia
mọi tệp thành từng giấy theo trang trong MỘT lượt (không sót trang, hai mặt CCCD cùng người là một giấy), cắt PDF con rồi
chạy planner đính nguyên tệp (dinh_kem_khong_tach) trên các PDF con → mỗi giấy vào đúng dòng, kế hoạch trả về tệp gốc
bằng ``sourceSegments``. LLM chia giấy lỗi → planner chạy trên tệp gốc (đính nguyên tệp) + cảnh báo.
"""

from app.pipelines._shared.lao_cai_tach_giay_to import always_split
from app.pipelines._shared.lao_cai_tach_giay_to import plan_with_split as _chia_trang
from app.process.schemas import FileItem

from ..dinh_kem_khong_tach.planner import plan as plan_without_split


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    opts = options or {}
    # Router đã chia trang (tài khoản luôn tách) hoặc extension không cắt được trang → đính nguyên tệp, không chia lần hai.
    if always_split(opts) or opts.get("supportsSourceSegments") is False:
        return await plan_without_split(files, options, session)
    return await _chia_trang(plan_without_split, files, options, session)
