"""Điền đợt 2 cấp điều chỉnh giấy phép xây dựng: soát lại lượt trích rồi tính các ô UI cần ghi lại so với lượt điền đầu."""

from app.pipelines.cap_giay_phep_xay_dung.thanh_tra import dia_diem, dinh_danh
from app.pipelines.cap_giay_phep_xay_dung.thanh_tra.dot_hai import patch_with

from ..process import mapper
from . import INSPECTORS, review

# Ô tỉnh / xã KHÔNG vá: form có hai cặp tỉnh / xã cùng tên ô (người nộp, địa điểm) mà bản vá chỉ phân biệt ô theo tên.
_BLOCKS = (
    (dinh_danh.INSPECTOR.key, ("data[tenChuHo]", "data[soDinhDanhChuHo]", "data[soDinhDanhNguoiDaiDien]",
                               "data[fullname]", "data[identityNumber]", "data[identityDate]", "data[identityAgency]")),
    (dia_diem.INSPECTOR.key, ("data[loDatSo]", "data[dienTichLoDat]")),
    (INSPECTORS[2].key, ("data[thoiGianDuKienHoanThanh]", "data[tenHoSo]")),
)
# Ô quyết định bố cục form: phán quyết làm đổi ô nào trong số này thì form đang theo nhánh cũ → không vá gì.
_LAYOUT = ("data[chonDoiTuong]", "data[loaiHinhChuDauTu]")


async def patch(documents: list[dict], raw_fields: list[dict], base_fields: list[dict], options: dict) -> dict:
    return await patch_with(review, mapper.enrich, _BLOCKS, _LAYOUT, documents, raw_fields, base_fields, options)
