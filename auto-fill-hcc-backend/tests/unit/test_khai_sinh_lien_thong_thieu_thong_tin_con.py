"""Khai sinh liên thông: hồ sơ CHƯA có thông tin con thì không được làm sập pipeline.

Lỗi thật gặp tại quầy: cán bộ gửi mỗi giấy chứng nhận kết hôn + một giấy tờ khác (chưa có
giấy chứng sinh, chưa có tờ khai) → `has_child` = False → nhánh quê quán đọc `is_lam_dong` vốn
chỉ được gán BÊN TRONG khối `if has_child:` → UnboundLocalError. Công dân chỉ thấy
"Xử lý giấy tờ chưa xong được — cannot access local variable 'is_lam_dong'".

Đây là ca RẤT dễ gặp: công dân đưa giấy tờ theo từng đợt, đợt đầu thường chưa có chứng sinh.
"""
from app.pipelines.khai_sinh_lien_thong.process.mapper import enrich


def _run(values: dict):
    """enrich nhận LIST field (không phải dict) — dựng đúng hình dạng thật."""
    return enrich([{"name": k, "value": v} for k, v in values.items()])


def _fields(rows):
    return {f["name"]: f.get("value") for f in rows}


def test_thieu_hoan_toan_thong_tin_con_van_chay_duoc():
    # Đúng bộ giấy tờ của ca lỗi: chỉ có cha/mẹ, không một trường nào của con.
    result = _run({
        "ThongTinBo_HoTen": "NGUYỄN VĂN A",
        "ThongTinBo_SoDinhDanh": "001234567890",
        "ThongTinMe_HoTen": "TRẦN THỊ B",
        "ThongTinMe_SoDinhDanh": "001234567891",
    })
    assert isinstance(result, list), "không được ném UnboundLocalError"


def test_khong_co_noi_sinh_thi_khong_ap_ngoai_le_lam_dong():
    # is_lam_dong phải là False chứ không phải "chưa gán": quê quán con vẫn lấy theo CHA.
    result = _run({
        "ThongTinBo_HoTen": "NGUYỄN VĂN A",
        "ThongTinBo_QueQuan": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Tân Phong"},
        "ThongTinMe_HoTen": "TRẦN THỊ B",
        "ThongTinMe_QueQuan": {"tinh": "Tỉnh Lâm Đồng", "xa": "Xã Khác"},
    })
    qq = _fields(result).get("QqDiaChi") or {}
    if qq:
        assert "Lâm Đồng" not in str(qq), "không có nơi sinh thì không được lấy quê mẹ theo lệ Lâm Đồng"


def test_sinh_o_lam_dong_van_lay_que_quan_me():
    # Hành vi CŨ phải giữ nguyên sau khi dời phép tính ra ngoài khối.
    result = _run({
        "Gcs_NoiSinh": {"tinh": "Tỉnh Lâm Đồng", "xa": "Phường Xuân Hương"},
        "Tk_HoTenCon": "NGUYỄN VĂN C",
        "ThongTinBo_HoTen": "NGUYỄN VĂN A",
        "ThongTinBo_QueQuan": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Tân Phong"},
        "ThongTinMe_HoTen": "TRẦN THỊ B",
        "ThongTinMe_SoDinhDanh": "001234567891",
        "ThongTinMe_QueQuan": {"tinh": "Tỉnh Lâm Đồng", "xa": "Phường Xuân Hương"},
    })
    qq = _fields(result).get("QqDiaChi") or {}
    assert "Lâm Đồng" in str(qq), "sinh ở Lâm Đồng thì quê quán con theo MẸ"
