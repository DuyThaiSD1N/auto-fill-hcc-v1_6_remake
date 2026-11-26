"""Prompt liệt kê giấy tờ trong từng tệp — "Cấp giấy phép thi công công trình trên đường bộ đang khai thác" (1.013061),
chế độ KHÔNG tách. Định nghĩa loại giấy lấy NGUYÊN VĂN từ prompt chế độ tách để hai chế độ hiểu loại giấy như nhau."""

from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach.dinh_kem_khong_tach.prompt import (
    build_system_prompt,
    build_user_prompt,
    split_prompt_blocks,
)

from ..dinh_kem_tach import prompt as _tach

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]

DOC_TYPES = split_prompt_blocks(_tach.SYSTEM_PROMPT, "allowed_types", "disambiguation")

SYSTEM_PROMPT = build_system_prompt(
    "Cấp giấy phép thi công công trình trên đường bộ đang khai thác",
    DOC_TYPES,
    '{"documents":[{"index":0,"docTypes":["don_de_nghi"]},{"index":1,"docTypes":["khoang_cach_dpc"]},'
    '{"index":2,"docTypes":["bptc_bdgt_hoan_tra"]},{"index":3,"docTypes":["thiet_ke_thi_cong"]}]}',
    extra_rules=(
        "Một thành phần hồ sơ gồm cả trang bìa, thuyết minh và các tờ bản vẽ của nó — chỉ liệt kê loại của thành phần "
        "đó, không liệt kê thêm loại vì các cụm được nhắc tới trong thân văn bản.",
    ),
)
