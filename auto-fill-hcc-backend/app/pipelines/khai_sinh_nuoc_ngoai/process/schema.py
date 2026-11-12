"""Schema trích xuất cho "Đăng ký khai sinh có yếu tố nước ngoài" (2.000528, Cổng DVC quốc gia mới).

Cổng dùng CHUNG tờ khai điện tử khai sinh với 1.001193 (cùng khối người nộp / người được khai sinh / mẹ / cha, cùng
tên câu hỏi SurveyJS) → lấy lại schema của khai_sinh_dvc_moi, chỉ thêm loại cư trú của cha mẹ: cha/mẹ người nước
ngoài hay khai "Nơi tạm trú" ở Việt Nam, còn 1.001193 luôn để "Thường trú".
"""

from app.pipelines.khai_sinh_dvc_moi.process.schema import COMPACT_COMP_BY_NAME as _BASE_COMP
from app.pipelines.khai_sinh_dvc_moi.process.schema import FIELDS as _BASE_FIELDS
from app.pipelines.khai_sinh_dvc_moi.process.schema import UI_COMP_BY_NAME as _BASE_UI


def _loai_cu_tru(prefix: str, label: str) -> dict:
    return {
        "name": f"{prefix}_LoaiCuTru",
        "desc": f'Nhãn dòng nơi cư trú của {label} trên tờ khai: "Nơi tạm trú" → "Tạm trú"; "Nơi thường trú" → '
                f'"Thường trú"; "Nơi ở hiện tại" / "nơi đang sinh sống" → "Nơi ở hiện tại". Nhãn chung "Nơi cư trú" '
                f"hoặc không có tờ khai → bỏ.",
    }


FIELDS: list[dict] = [*_BASE_FIELDS, _loai_cu_tru("Me", "MẸ"), _loai_cu_tru("Cha", "CHA")]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {**_BASE_COMP, "Me_LoaiCuTru": "x-input", "Cha_LoaiCuTru": "x-input"}

# Địa chỉ ở nước ngoài: chọn radio "Khác" thì cổng hiện ô Quốc gia + địa chỉ thay cho Tỉnh / Xã. Extension dò ô theo
# nhãn trong cùng khối với radio (setArea), nên tên ô gộp "_NuocNgoai" chỉ để báo cáo, không có trên trang.
FOREIGN_AREA_RADIOS = {
    "Con_NoiSinh": "citizenNoisinhnks",
    "Con_QueQuan": "citizenQuequannks",
    "Me_NoiCuTru": "citizenMeNoicutru",
    "Cha_NoiCuTru": "citizenChaNoicutru",
}

UI_COMP_BY_NAME = {
    **_BASE_UI,
    **{f"{radio}_NuocNgoai": "sjs-area" for radio in FOREIGN_AREA_RADIOS.values()},
}
