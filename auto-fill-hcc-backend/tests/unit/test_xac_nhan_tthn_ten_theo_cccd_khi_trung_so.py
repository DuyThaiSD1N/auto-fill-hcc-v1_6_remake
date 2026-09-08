"""XNTTHN: số định danh trên tờ khai TRÙNG số trên thẻ căn cước → lấy HỌ TÊN in trên thẻ.

Tờ khai là bản VIẾT TAY nên OCR tên rất hay sai: rơi dấu hoặc đọc nhầm chữ ("Hoà" → "Hoa",
"Thiết" → "Thiệt"). Thẻ căn cước là bản IN, và đó mới là tên phải khớp với CSDLQG về dân cư khi
cổng đối chiếu. Trùng 12 chữ số định danh là bằng chứng CHẮC CHẮN cùng một người (khác hẳn phép
so tên vốn dễ đụng hàng), nên lúc đó tên trên thẻ luôn thắng — giống cách số CCCD/ngày cấp vẫn
lấy theo thẻ.

Ranh giới phải giữ: KHÁC số là hai người khác nhau, mượn tên sang là ghép nhân thân lai.
"""
from app.pipelines.xac_nhan_tthn.process.mapper import enrich


def _run(**kv):
    return {f["name"]: f["value"] for f in enrich([{"name": k, "value": v} for k, v in kv.items()])}


# --------------------------------------------------------------------------------------
# MỤC II — người được xác nhận
# --------------------------------------------------------------------------------------

def test_trung_so_thi_lay_ten_tren_the():
    out = _run(
        ToKhai_HoTen="NGUYEN THI HOA",          # OCR chữ viết tay, mất dấu
        ToKhai_SoDinhDanh="036301012326",
        Cccd_HoTen="NGUYỄN THỊ HOÀ",            # bản in trên thẻ
        Cccd_SoDinhDanh="036301012326",
        Cccd_NgayCap="12/02/2026",
    )
    assert out["HoVaTenC1"] == "NGUYỄN THỊ HOÀ"
    # Số/ngày cấp vẫn như cũ — thay đổi này chỉ đụng đến HỌ TÊN.
    assert out["SoDinhDanhC1"] == "036301012326"
    assert out["NgayCapDDC1"] == "12/02/2026"


def test_khac_so_thi_giu_ten_to_khai():
    """Khác số = hai người khác nhau. Đây là ranh giới quan trọng nhất của cả thay đổi."""
    out = _run(
        ToKhai_HoTen="TRẦN VĂN NAM",
        ToKhai_SoDinhDanh="001099000111",
        Cccd_HoTen="NGUYỄN THỊ HOÀ",
        Cccd_SoDinhDanh="036301012326",
    )
    assert out["HoVaTenC1"] == "TRẦN VĂN NAM"


def test_to_khai_khong_ghi_so_thi_giu_thu_tu_cu():
    """Thiếu số một bên → không kết luận được cùng người → không mượn tên."""
    out = _run(
        ToKhai_HoTen="LE VAN BINH",
        Cccd_HoTen="NGUYỄN THỊ HOÀ",
        Cccd_SoDinhDanh="036301012326",
    )
    assert out["HoVaTenC1"] == "LE VAN BINH"


def test_the_trung_so_nhung_khong_doc_duoc_ten_thi_lui_ve_to_khai():
    out = _run(
        ToKhai_HoTen="NGUYEN THI HOA",
        ToKhai_SoDinhDanh="036301012326",
        Cccd_SoDinhDanh="036301012326",
    )
    assert out["HoVaTenC1"] == "NGUYEN THI HOA"


def test_so_co_dinh_dang_khac_nhau_van_coi_la_trung():
    """So theo CHỮ SỐ: tờ khai hay ghi cách nhóm ("036 301 012 326")."""
    out = _run(
        ToKhai_HoTen="NGUYEN THI HOA",
        ToKhai_SoDinhDanh="036 301 012 326",
        Cccd_HoTen="NGUYỄN THỊ HOÀ",
        Cccd_SoDinhDanh="036301012326",
    )
    assert out["HoVaTenC1"] == "NGUYỄN THỊ HOÀ"


# --------------------------------------------------------------------------------------
# MỤC I — khối "người yêu cầu" khai riêng ở đầu tờ khai (cũng là chữ viết tay)
# --------------------------------------------------------------------------------------

def test_muc_i_trung_so_the_thi_lay_ten_tren_the():
    out = _run(
        ToKhaiYeuCau_HoTen="PHAM TRUONG GIANG",
        ToKhaiYeuCau_SoDinhDanh="036200002580",
        Cccd_HoTen="PHẠM TRƯỜNG GIANG",
        Cccd_SoDinhDanh="036200002580",
        ToKhai_HoTen="LÊ THỊ NGỌC BÍCH",        # người ĐƯỢC cấp, người khác
        ToKhai_SoDinhDanh="036301012326",
    )
    assert out["HoVaTenC"] == "PHẠM TRƯỜNG GIANG"
    assert out["HoVaTenC1"] == "LÊ THỊ NGỌC BÍCH"
    assert out["quanhevoinguoiduocxacminh"] == "2"   # hai người khác nhau


def test_muc_i_the_la_cua_nguoi_khac_thi_khong_muon_ten():
    """Thẻ trong hồ sơ thường là của NGƯỜI ĐƯỢC CẤP, không phải người đứng khai hộ."""
    out = _run(
        ToKhaiYeuCau_HoTen="PHAM TRUONG GIANG",
        ToKhaiYeuCau_SoDinhDanh="036200002580",
        Cccd_HoTen="LÊ THỊ NGỌC BÍCH",
        Cccd_SoDinhDanh="036301012326",
    )
    assert out["HoVaTenC"] == "PHAM TRUONG GIANG"
