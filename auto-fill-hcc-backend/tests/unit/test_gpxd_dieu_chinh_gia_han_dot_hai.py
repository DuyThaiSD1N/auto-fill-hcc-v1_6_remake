"""Điều chỉnh / gia hạn / sửa chữa cải tạo giấy phép xây dựng: điền đợt 2 (thanh tra giấy phép đã cấp + định danh, thửa đất
dùng chung cấp mới) và mapper điều chỉnh (số, tên giả)."""

import asyncio

from app.pipelines._shared.thanh_tra.ho_so import Case, Finding, Result
from app.pipelines.cap_giay_phep_xay_dung.thanh_tra import chung, giay_phep
from app.pipelines.dieu_chinh_giay_phep_xay_dung import thanh_tra as dc_thanh_tra
from app.pipelines.dieu_chinh_giay_phep_xay_dung.process import mapper as dc_mapper
from app.pipelines.dieu_chinh_giay_phep_xay_dung.thanh_tra import dot_hai as dc_dot_hai
from app.pipelines.gia_han_giay_phep_xay_dung import thanh_tra as gh_thanh_tra
from app.procedures.registry import get_procedure


def test_registry_bat_dot_hai_formio_ca_nhom():
    for key in ("dieu-chinh-giay-phep-xay-dung", "gia-han-giay-phep-xay-dung", "sua-chua-cai-tao-gpxd-nha-o-rieng-le",
                "sua-chua-cai-tao-gpxd-cong-trinh"):
        assert get_procedure(key)["secondPass"] == "formio"
    assert [i.key for i in dc_thanh_tra.INSPECTORS] == ["dinh_danh", "dia_diem", "giay_phep"]
    assert [u.key for u in gh_thanh_tra.INSPECTORS[2].units] == ["so_gpxd", "cap_gpxd", "thoi_gian"]


def test_dieu_chinh_thoi_gian_chi_so_thang_va_mot_so_dinh_danh():
    fields, _ = dc_mapper.enrich([
        {"name": "ChuHo_HoTen", "value": "Nguyễn Văn A - Trần Thị B"},
        {"name": "ChuHo_SoDinhDanh", "value": "001000000001 - 001000000002"},
        {"name": "CongTrinh_ThoiGianDuKienHoanThanh", "value": "03 tháng"},
    ], {})
    ui = {f["name"]: f["value"] for f in fields}
    assert ui["data[thoiGianDuKienHoanThanh]"] == "3"
    assert ui["data[soDinhDanhChuHo]"] == "001000000001" and ui["data[identityNumber]"] == "001000000001"
    assert dc_mapper._first_identity("001000000001001000000002") == "001000000001"


def test_thoi_gian_chi_nhan_dong_cua_don_ghi_theo_thang(monkeypatch):
    unit = giay_phep.THOI_GIAN
    key = "CongTrinh_ThoiGianDuKienHoanThanh"

    async def fake(inspector, case, title):
        return [Finding(inspector, unit, {key: "9"}, "Dự kiến thời gian hoàn thành công trình: 09 tháng", 1,
                        owner=chung.GPXD),
                Finding(inspector, unit, {key: "12"}, "có hiệu lực trong thời hạn 12 năm", 1, owner=chung.DON),
                Finding(inspector, unit, {key: "3"}, "theo thiết kế điều chỉnh: 03 tháng", 1, owner=chung.DON)]

    monkeypatch.setattr(giay_phep.engine, "llm_findings", fake)
    inspector = giay_phep.inspector(giay_phep.SO, giay_phep.THOI_GIAN)
    found = asyncio.run(giay_phep.find(inspector, Case([{"text": ""}], "", {}, {}), "thử"))
    assert [f.values[key] for f in found] == ["3"]
    assert giay_phep.check(giay_phep.SO, {"GPXD_So": "GPXD"}, None)


def test_dot_hai_dieu_chinh_chi_va_o_phan_quyet_lam_doi(monkeypatch):
    async def fake_review(documents, values, options=None):
        return Result({**values, "GPXD_So": "306/GPXD", "Dat_DienTich": "84,1"}, [], {})

    monkeypatch.setattr(dc_dot_hai, "review", fake_review)
    raw = [{"name": "ChuHo_HoTen", "value": "Nguyễn Văn A"}, {"name": "GPXD_So", "value": "308/GPXD"},
           {"name": "Dat_DienTich", "value": "84,1"}]
    base, _ = dc_mapper.enrich(raw, {})
    out = asyncio.run(dc_dot_hai.patch([], raw, base, {}))
    assert [(f["name"], f["value"], f["by"]) for f in out["fields"]] == [
        ("data[tenHoSo]", "Điều chỉnh Giấy phép xây dựng số 306/GPXD", "giay_phep")]
