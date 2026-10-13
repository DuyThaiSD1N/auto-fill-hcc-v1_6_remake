"""Khai sinh liên thông: thông tin giấy chứng nhận kết hôn chép trên dòng in sẵn của TỜ KHAI (hồ sơ không kèm giấy
kết hôn thật) vẫn phải điền; giấy kết hôn thật thì thắng tờ khai."""
from app.pipelines.khai_sinh_lien_thong.process.mapper import enrich


def _gcn(values: dict) -> dict:
    out = enrich([{"name": k, "value": v} for k, v in values.items()])
    return {f["name"]: f.get("value") for f in out if f["name"].startswith("GiayCNKH")}


def test_chi_co_dong_to_khai_van_dien_bo_dau_cham():
    out = _gcn({"Tk_GcnKetHon_So": "49...", "Tk_GcnKetHon_QuyenSo": "....", "Tk_GcnKetHon_NgayCap": "24/06/2023",
                "Tk_GcnKetHon_NoiCap": "UBND xã A"})
    assert out == {"GiayCNKHSo": "49", "GiayCNKHNgayCap": "24/06/2023", "GiayCNKHNoiCap": "UBND xã A"}


def test_giay_ket_hon_that_thang_to_khai_to_khai_bu_o_thieu():
    out = _gcn({"GcnKetHon_So": "12", "GcnKetHon_NgayCap": "01/02/2020", "Tk_GcnKetHon_So": "21",
                "Tk_GcnKetHon_NoiCap": "UBND xã B"})
    assert out == {"GiayCNKHSo": "12", "GiayCNKHNgayCap": "01/02/2020", "GiayCNKHNoiCap": "UBND xã B"}
