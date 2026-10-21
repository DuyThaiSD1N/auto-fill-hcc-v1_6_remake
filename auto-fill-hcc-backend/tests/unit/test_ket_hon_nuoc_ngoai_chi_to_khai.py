"""Kết hôn có yếu tố nước ngoài: hồ sơ chỉ có tờ khai mà LLM chỉ trả cột tờ khai → vẫn điền nhân thân theo tờ khai."""
from app.pipelines.ket_hon_nuoc_ngoai.process import mapper


def _fields(**kw):
    return [{"name": k, "comp": "x-input", "value": v} for k, v in kw.items()]


def test_chi_co_cot_to_khai_van_dien_ho_ten_so_giay_to_ngay_sinh():
    out = {f["name"]: f["value"] for f in mapper.enrich(_fields(
        ToKhaiNam_HoTen="Li Wei", ToKhaiNam_SoGiayTo="E12345678", ToKhaiNam_NgaySinh="01/02/1985",
        ToKhaiNu_HoTen="Nguyễn Thị A", ToKhaiNu_SoGiayTo="001190000123", ToKhaiNu_NgaySinh="03/04/1990",
        Nam_SoLanKetHon=2, Nu_SoLanKetHon=1), {})}
    assert out["HoTenBenNam"] == "LI WEI" and out["SoGiayToDinhDanh_BenNam"] == "E12345678"
    assert out["NgaySinhBenNam"] == "01/02/1985" and out["SoLanKetHon_BenNam"] == "2"
    assert out["HoTenBenNu"] == "NGUYỄN THỊ A" and out["SoLanKetHon_BenNu"] == "1"
    # Không có căn cứ quốc tịch / loại giấy tờ → không đoán (người nước ngoài không bị gán "Việt Nam", "Căn cước").
    assert "QuocTichBenNam" not in out and "LoaiGiayToDinhDanh_BenNam" not in out


def test_khong_co_gi_cua_nguoi_do_thi_bo_trong():
    assert mapper.enrich(_fields(Nam_SoLanKetHon=1), {}) == []
