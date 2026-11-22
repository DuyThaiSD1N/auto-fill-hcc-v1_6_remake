"""Lớp soát thứ hai của thủ tục cấp Giấy xác nhận tình trạng hôn nhân: các thanh tra + toà án (khung ở
_shared/thanh_tra). Chạy ở nền sau lượt điền đầu, kết quả thành các ô điền đợt 2 (dot_hai.py, app/second_pass)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra import sdt_nguoi_nop
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from ..process import mapper
from . import dia_chi, dinh_danh, giay_ho_tich

TITLE = "cấp Giấy xác nhận tình trạng hôn nhân"
# Giấy khai tử / bản án ly hôn không có trong tài khoản nên soát ở mọi hồ sơ.
INSPECTORS_ALWAYS = (giay_ho_tich.INSPECTOR, sdt_nguoi_nop.INSPECTOR)
# Chỉ soát khi người nộp KHÔNG phải người được cấp: chọn "Bản thân" thì khối người được cấp lấy theo tài khoản.
INSPECTORS_FOR_OTHERS = (dinh_danh.INSPECTOR, dia_chi.INSPECTOR)


async def review(documents: list[dict], context: str, values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản."""
    options = options or {}
    relation = mapper._relation(values, context or "", options)[0]
    inspectors = INSPECTORS_ALWAYS + (() if relation == "1" else INSPECTORS_FOR_OTHERS)
    # Cụm ly hôn: mapper dùng BanAn_* (văn bản), field nào trống thì lấy DivorceDecision_* (tờ khai). Thanh tra soát
    # trên chính giá trị sẽ được điền đó, và bộ thanh tra đề xuất ghi vào BanAn_* nên vẫn thắng ở mapper.
    effective = dict(values)
    for banan, to_khai in zip(giay_ho_tich.DIVORCE_FIELDS, ("DivorceDecision_Number", "DivorceDecision_Date",
                                                           "DivorceDecision_Agency")):
        if not effective.get(banan) and effective.get(to_khai):
            effective[banan] = effective[to_khai]
    result = await engine.run(Case(documents, context or "", effective, options), inspectors, title=TITLE)
    # Số giấy tờ tùy thân chính là số định danh: số định danh được sửa thì số giấy tờ đi theo.
    old, new = values.get(dinh_danh.NUMBER), result.values.get(dinh_danh.NUMBER)
    if new and new != old and values.get("NguoiDuocCap_SoGiayTo") == old:
        result.values["NguoiDuocCap_SoGiayTo"] = new
    return result
