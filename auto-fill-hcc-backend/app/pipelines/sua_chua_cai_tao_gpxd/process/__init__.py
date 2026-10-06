"""Process cho "Cấp giấy phép xây dựng SỬA CHỮA, CẢI TẠO" (cổng Bộ Xây dựng dvc.moc.gov.vn).

Form/contact-block + bộ field thông tin công trình GIỐNG ~95% thủ tục cấp mới (cap_giay_phep_xay_dung),
nên TÁI SỬ DỤNG nguyên schema/prompt/mapper của thủ tục cấp mới. KHÁC: thủ tục sửa chữa có HAI FORM riêng
theo quy trình (process= khác nhau), dùng bộ element khác nhau:
  - Quy trình 15 ngày (nhà ở riêng lẻ) → element data[...]NhaO         → constructionVariant="nha_o_rieng_le"
  - Quy trình 10 ngày (công trình)     → element data[...]KhongTheoTuyen → constructionVariant="khong_theo_tuyen"
Nhánh phải khớp FORM đang mở (không chỉ suy từ giấy tờ) → mỗi registry key ÉP một biến thể qua option.
"""

from app.pipelines.cap_giay_phep_xay_dung.process.runner import run as _cap_moi_run


async def _run(files_by_role: dict[str, list[dict]], options: dict, variant: str) -> dict:
    opts = dict(options or {})
    opts["constructionVariant"] = variant
    return await _cap_moi_run(files_by_role, opts)


async def run_nha_o(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    """Quy trình 15 ngày — nhà ở riêng lẻ (element ...NhaO)."""
    return await _run(files_by_role, options, "nha_o_rieng_le")


async def run_cong_trinh(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    """Quy trình 10 ngày — công trình không theo tuyến/… (element ...KhongTheoTuyen)."""
    return await _run(files_by_role, options, "khong_theo_tuyen")
